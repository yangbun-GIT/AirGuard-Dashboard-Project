import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from .database import get_db, init_db, AsyncSessionLocal, RegionCode, WeatherDataCache
from .api_client import fetch_nearby_station, fetch_air_quality, fetch_weather, fetch_uv_index
from .service import calculate_scores

app = FastAPI(title="AirGuard Dashboard API")


@app.on_event("startup")
async def on_startup():
    await init_db()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RegionCode).limit(1))
        if not result.scalars().first():
            print("\n[DB 초기화] 등록된 지역 데이터가 없습니다. 엑셀(Excel) 로딩을 시작합니다...")
            import pandas as pd
            import os

            # 🚨 경로 및 확장자 수정 (.xlsx)
            excel_path = "backend/region_data.xlsx"

            if not os.path.exists(excel_path):
                print(f"[오류] ❌ 엑셀 파일을 찾을 수 없습니다: {excel_path}")
                print("⚠️ region_data.xlsx 파일이 backend 폴더 안에 있는지 꼭 확인해주세요!")
                return

            try:
                print(f"[진행] ✅ 엑셀 파일 발견! 데이터를 읽어옵니다. (시간이 조금 걸릴 수 있습니다...)")
                # 🚨 CSV가 아닌 Excel 파싱 (openpyxl 엔진 사용)
                df = pd.read_excel(excel_path, engine='openpyxl')

                df = df.fillna("")

                df['1단계'] = df['1단계'].astype(str)
                df['3단계'] = df['3단계'].astype(str)

                target_df = df[(df["1단계"] != "") & (df["3단계"] == "")]
                print(f"[진행] ✅ 필터링 완료! 총 {len(target_df)}개의 시/도 및 시/군/구 데이터가 발견되었습니다.")

                regions = []
                for _, row in target_df.iterrows():
                    code = str(row["행정구역코드"]).strip()
                    sido = str(row["1단계"]).strip()
                    sigungu = str(row["2단계"]).strip()

                    # 🚨 수정 포인트:
                    # 2단계(시군구)가 비어있는 행은 해당 '도' 전체의 대표 좌표입니다.
                    # 이를 위해 sigungu가 비어있으면 '전체' 또는 시도명과 동일하게 처리하되,
                    # 프론트엔드에서 필터링하기 쉽도록 구조를 잡습니다.
                    display_sigungu = sigungu if sigungu else sido

                    try:
                        regions.append(RegionCode(
                            code=code, sido=sido, sigungu=display_sigungu, eupmyeondong="",
                            lat=float(row["위도(초/100)"]), lon=float(row["경도(초/100)"]),
                            nx=int(row["격자 X"]), ny=int(row["격자 Y"])
                        ))
                    except Exception as e:
                        continue

                if regions:
                    db.add_all(regions)
                    await db.commit()
                    print(f"[완료] 🎉 총 {len(regions)}개의 지역 데이터가 DB(backend/data/airguard.db)에 성공적으로 저장되었습니다!\n")
                else:
                    print("[오류] ❌ 추출된 지역 데이터가 0건입니다. 엑셀 파일 형식을 확인하세요.")

            except Exception as e:
                print(f"[오류] ❌ 알 수 없는 에러 발생: {str(e)}")


class DashboardResponse(BaseModel):
    is_fallback: bool
    temperature: float
    rain_prob: float
    pm10: float
    pm25: float
    uv_index: float
    ventilation_score: int
    outdoor_score: int
    lat: float
    lon: float


@app.get("/api/regions")
async def get_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode))
    regions = result.scalars().all()
    return [{"code": r.code, "sido": r.sido, "sigungu": r.sigungu} for r in regions]


@app.get("/api/dashboard/{region_code}", response_model=DashboardResponse)
async def get_dashboard(region_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode).where(RegionCode.code == region_code))
    region = result.scalars().first()
    if not region: raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다.")

    time_threshold = datetime.utcnow() - timedelta(hours=1)
    cache_result = await db.execute(
        select(WeatherDataCache).where(WeatherDataCache.region_code == region_code,
                                       WeatherDataCache.timestamp >= time_threshold).order_by(
            WeatherDataCache.timestamp.desc())
    )
    cache = cache_result.scalars().first()

    if cache:
        vent, out = calculate_scores(cache.pm10, cache.pm25, cache.temperature, cache.rain_prob, cache.uv_index)
        return DashboardResponse(is_fallback=False, temperature=cache.temperature, rain_prob=cache.rain_prob,
                                 pm10=cache.pm10, pm25=cache.pm25, uv_index=cache.uv_index, ventilation_score=vent,
                                 outdoor_score=out, lat=region.lat, lon=region.lon)

    try:
        station_name = await fetch_nearby_station(region.lat, region.lon)
        air_task = fetch_air_quality(station_name)
        weather_task = fetch_weather(region.nx, region.ny)
        uv_task = fetch_uv_index(region_code)

        air_data, weather_data, uv_data = await asyncio.gather(air_task, weather_task, uv_task)

        new_cache = WeatherDataCache(
            region_code=region_code, pm10=air_data["pm10"], pm25=air_data["pm25"],
            temperature=weather_data["temperature"], rain_prob=weather_data["rain_prob"], uv_index=uv_data
        )
        db.add(new_cache)
        await db.commit()

        vent, out = calculate_scores(air_data["pm10"], air_data["pm25"], weather_data["temperature"],
                                     weather_data["rain_prob"], uv_data)
        return DashboardResponse(is_fallback=False, temperature=weather_data["temperature"],
                                 rain_prob=weather_data["rain_prob"], pm10=air_data["pm10"], pm25=air_data["pm25"],
                                 uv_index=uv_data, ventilation_score=vent, outdoor_score=out, lat=region.lat,
                                 lon=region.lon)

    except Exception as e:
        fallback_result = await db.execute(
            select(WeatherDataCache).where(WeatherDataCache.region_code == region_code).order_by(
                WeatherDataCache.timestamp.desc()))
        fb = fallback_result.scalars().first()
        if fb:
            vent, out = calculate_scores(fb.pm10, fb.pm25, fb.temperature, fb.rain_prob, fb.uv_index)
            return DashboardResponse(is_fallback=True, temperature=fb.temperature, rain_prob=fb.rain_prob, pm10=fb.pm10,
                                     pm25=fb.pm25, uv_index=fb.uv_index, ventilation_score=vent, outdoor_score=out,
                                     lat=region.lat, lon=region.lon)
        raise HTTPException(status_code=500, detail="API 연동 오류 및 과거 데이터 없음.")