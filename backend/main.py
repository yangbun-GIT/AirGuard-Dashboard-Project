import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from .database import get_db, init_db, RegionCode, WeatherDataCache
from .api_client import fetch_nearby_station, fetch_air_quality, fetch_weather, fetch_uv_index
from .service import calculate_scores

app = FastAPI(title="AirGuard Dashboard API")


@app.on_event("startup")
async def on_startup():
    await init_db()
    async for db in get_db():
        result = await db.execute(select(RegionCode).limit(1))
        # DB가 비어있다면 CSV에서 전국 데이터(시/군/구) 추출 및 저장
        if not result.scalars().first():
            import pandas as pd
            import os

            csv_path = "region_data.csv"
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path, encoding="cp949")
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_path, encoding="utf-8")

                df = df.fillna("")
                # 3단계(동)가 비어있고 1단계(시도)가 존재하는 '시/군/구' 단위 데이터 추출
                target_df = df[(df["3단계"] == "") & (df["1단계"] != "")]

                regions = []
                for _, row in target_df.iterrows():
                    code = str(row["행정구역코드"])
                    sido = row["1단계"]
                    sigungu = row["2단계"]
                    if not sigungu: sigungu = sido  # 세종시 등 단일 구조 대응

                    try:
                        regions.append(RegionCode(
                            code=code, sido=sido, sigungu=sigungu, eupmyeondong="",
                            lat=float(row["위도(초/100)"]), lon=float(row["경도(초/100)"]),
                            nx=int(row["격자 X"]), ny=int(row["격자 Y"])
                        ))
                    except ValueError:
                        continue

                if regions:
                    db.add_all(regions)
                    await db.commit()


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
        weather_task = fetch_weather(region.nx, region.ny)  # 👈 위경도 대신 nx, ny 전달
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