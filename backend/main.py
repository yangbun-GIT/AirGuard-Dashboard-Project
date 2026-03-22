import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from .database import get_db, init_db, RegionCode, WeatherDataCache
from .api_client import fetch_nearby_station, fetch_air_quality, fetch_weather, fetch_uv_index

app = FastAPI(title="AirGuard Dashboard API")


@app.on_event("startup")
async def on_startup():
    await init_db()
    # 개발/테스트용 초기 더미 지역 데이터 적재
    async for db in get_db():
        result = await db.execute(select(RegionCode).limit(1))
        if not result.scalars().first():
            dummy_region = RegionCode(code="1168064000", sido="서울특별시", sigungu="강남구", eupmyeondong="역삼1동", lat=37.495,
                                      lon=127.033, nx=61, ny=125)
            db.add(dummy_region)
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


def calculate_scores(pm10, pm25, temp, rain, uv):
    # 환기 지수 계산 (미세먼지, 강수 확률 기반)
    vent_score = 100
    if rain > 50: vent_score -= 50
    if pm10 > 80 or pm25 > 35:
        vent_score -= 40
    elif pm10 > 30 or pm25 > 15:
        vent_score -= 15

    # 야외 운동 지수 계산 (기온, 자외선, 미세먼지 기반)
    out_score = 100
    if temp < 5 or temp > 33:
        out_score -= 40
    elif temp < 15 or temp > 28:
        out_score -= 15
    if uv > 7:
        out_score -= 30
    elif uv > 5:
        out_score -= 15
    if pm10 > 80 or pm25 > 35: out_score -= 40
    if rain > 40: out_score -= 50

    return max(0, vent_score), max(0, out_score)


@app.get("/api/regions")
async def get_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode))
    regions = result.scalars().all()
    return [{"code": r.code, "name": f"{r.sido} {r.sigungu} {r.eupmyeondong}"} for r in regions]


@app.get("/api/dashboard/{region_code}", response_model=DashboardResponse)
async def get_dashboard(region_code: str, db: AsyncSession = Depends(get_db)):
    # 1. 지역 확인
    result = await db.execute(select(RegionCode).where(RegionCode.code == region_code))
    region = result.scalars().first()
    if not region: raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다.")

    # 2. 캐시 확인 (1시간 이내)
    time_threshold = datetime.utcnow() - timedelta(hours=1)
    cache_result = await db.execute(
        select(WeatherDataCache).where(
            WeatherDataCache.region_code == region_code,
            WeatherDataCache.timestamp >= time_threshold
        ).order_by(WeatherDataCache.timestamp.desc())
    )
    cache = cache_result.scalars().first()

    if cache:
        vent, out = calculate_scores(cache.pm10, cache.pm25, cache.temperature, cache.rain_prob, cache.uv_index)
        return DashboardResponse(is_fallback=False, temperature=cache.temperature, rain_prob=cache.rain_prob,
                                 pm10=cache.pm10, pm25=cache.pm25, uv_index=cache.uv_index, ventilation_score=vent,
                                 outdoor_score=out, lat=region.lat, lon=region.lon)

    # 3. 비동기 API 호출
    try:
        station_name = await fetch_nearby_station(region.lat, region.lon)
        air_task = fetch_air_quality(station_name)
        weather_task = fetch_weather(region.lat, region.lon)
        uv_task = fetch_uv_index(region_code)

        air_data, weather_data, uv_data = await asyncio.gather(air_task, weather_task, uv_task)

        # 캐시 저장
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
        # 4. Fallback: API 에러시 가장 최근 캐시 반환
        fallback_result = await db.execute(
            select(WeatherDataCache).where(WeatherDataCache.region_code == region_code).order_by(
                WeatherDataCache.timestamp.desc()))
        fb = fallback_result.scalars().first()
        if fb:
            vent, out = calculate_scores(fb.pm10, fb.pm25, fb.temperature, fb.rain_prob, fb.uv_index)
            return DashboardResponse(is_fallback=True, temperature=fb.temperature, rain_prob=fb.rain_prob, pm10=fb.pm10,
                                     pm25=fb.pm25, uv_index=fb.uv_index, ventilation_score=vent, outdoor_score=out,
                                     lat=region.lat, lon=region.lon)
        raise HTTPException(status_code=500, detail="API 연동 오류 및 표시할 과거 데이터가 없습니다.")