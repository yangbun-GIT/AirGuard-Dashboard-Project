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
        # 지역 선택 테스트를 위한 전국 8도 기반 더미 데이터 삽입
        if not result.scalars().first():
            dummy_regions = [
                RegionCode(code="1168064000", sido="서울특별시", sigungu="강남구", eupmyeondong="역삼1동", lat=37.495, lon=127.033,
                           nx=61, ny=125),
                RegionCode(code="1168065000", sido="서울특별시", sigungu="강남구", eupmyeondong="역삼2동", lat=37.495, lon=127.035,
                           nx=61, ny=125),
                RegionCode(code="2635051000", sido="부산광역시", sigungu="해운대구", eupmyeondong="우제1동", lat=35.163,
                           lon=129.163, nx=98, ny=76),
                RegionCode(code="4113552000", sido="경기도", sigungu="성남시 분당구", eupmyeondong="서현1동", lat=37.382,
                           lon=127.118, nx=62, ny=123),
                RegionCode(code="5011025300", sido="제주특별자치도", sigungu="제주시", eupmyeondong="애월읍", lat=33.462,
                           lon=126.336, nx=51, ny=38)
            ]
            db.add_all(dummy_regions)
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
    # 계층형 구성을 위해 속성별로 분리해서 반환
    return [{"code": r.code, "sido": r.sido, "sigungu": r.sigungu, "eupmyeondong": r.eupmyeondong} for r in regions]


@app.get("/api/dashboard/{region_code}", response_model=DashboardResponse)
async def get_dashboard(region_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RegionCode).where(RegionCode.code == region_code))
    region = result.scalars().first()
    if not region: raise HTTPException(status_code=404, detail="지역을 찾을 수 없습니다.")

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