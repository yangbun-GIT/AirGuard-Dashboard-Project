# backend/main.py

import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from .database import get_db, init_db, RegionCode, WeatherDataCache
from .api_client import fetch_nearby_station, fetch_air_quality, fetch_weather, fetch_uv_index
from .service import calculate_scores  # ✨ 분리한 서비스 모듈 임포트

app = FastAPI(title="AirGuard Dashboard API")


@app.on_event("startup")
async def on_startup():
    await init_db()
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


@app.get("/api/regions")
async def get_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode))
    regions = result.scalars().all()
    return [{"code": r.code, "name": f"{r.sido} {r.sigungu} {r.eupmyeondong}"} for r in regions]


@app.get("/api/dashboard/{region_code}", response_model=DashboardResponse)
async def get_dashboard(region_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode).where(RegionCode.code == region_code))
    region = result.scalars().first()
    if not region:
        raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다.")

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

    try:
        station_name = await fetch_nearby_station(region.lat, region.lon)
        air_task = fetch_air_quality(station_name)
        weather_task = fetch_weather(region.lat, region.lon)
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
        raise HTTPException(status_code=500, detail="API 연동 오류 및 표시할 과거 데이터가 없습니다.")