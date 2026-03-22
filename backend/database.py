import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint

# 로컬(내 컴퓨터)과 도커 모두에서 동일하게 작동하는 직관적인 경로 설정
DB_DIR = "backend/data"

# data 폴더가 없으면 자동으로 짠! 하고 생성합니다.
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/airguard.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class RegionCode(Base):
    __tablename__ = "region_codes"
    code = Column(String(10), primary_key=True, index=True)
    sido = Column(String(20), nullable=False)
    sigungu = Column(String(20), nullable=True)
    eupmyeondong = Column(String(20), nullable=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    nx = Column(Integer, nullable=False)
    ny = Column(Integer, nullable=False)

class StationCache(Base):
    __tablename__ = "station_cache"
    region_code = Column(String(10), ForeignKey("region_codes.code", ondelete="CASCADE"), primary_key=True)
    station_name = Column(String(50), nullable=False)
    tm_x = Column(Float, nullable=False)
    tm_y = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class WeatherDataCache(Base):
    __tablename__ = "weather_data_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    region_code = Column(String(10), ForeignKey("region_codes.code", ondelete="CASCADE"), index=True, nullable=False)
    pm10 = Column(Float, nullable=False, default=0.0)
    pm25 = Column(Float, nullable=False, default=0.0)
    temperature = Column(Float, nullable=False)
    rain_prob = Column(Float, nullable=False)
    uv_index = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('pm10 >= 0', name='check_pm10_positive'),
        CheckConstraint('pm25 >= 0', name='check_pm25_positive'),
        CheckConstraint('rain_prob >= 0 AND rain_prob <= 100', name='check_rain_prob_range'),
    )

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session