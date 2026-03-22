import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint

# DB 저장 경로 설정 (Docker 환경과 로컬 환경 구분)
DB_DIR = "/app/data"
if not os.path.exists(DB_DIR) and not os.environ.get('DOCKER_ENV'):
    DB_DIR = "."  # 로컬 테스트용

DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR}/airguard.db"

# 비동기 엔진 및 세션 설정
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class RegionCode(Base):
    __tablename__ = "region_codes"

    # 법정동 코드는 10자리 문자열로 고정
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

    # 외래 키 설정: RegionCode 삭제 시 함께 삭제(CASCADE)
    region_code = Column(String(10), ForeignKey("region_codes.code", ondelete="CASCADE"), primary_key=True)
    station_name = Column(String(50), nullable=False)
    tm_x = Column(Float, nullable=False)
    tm_y = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class WeatherDataCache(Base):
    __tablename__ = "weather_data_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 외래 키 설정 (단순 인덱스를 넘어 관계성 명시)
    region_code = Column(String(10), ForeignKey("region_codes.code", ondelete="CASCADE"), index=True, nullable=False)
    pm10 = Column(Float, nullable=False, default=0.0)
    pm25 = Column(Float, nullable=False, default=0.0)
    temperature = Column(Float, nullable=False)
    rain_prob = Column(Float, nullable=False)
    uv_index = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 데이터 무결성을 위한 CHECK 제약 조건
    __table_args__ = (
        CheckConstraint('pm10 >= 0', name='check_pm10_positive'),
        CheckConstraint('pm25 >= 0', name='check_pm25_positive'),
        CheckConstraint('rain_prob >= 0 AND rain_prob <= 100', name='check_rain_prob_range'),
    )


async def init_db():
    """데이터베이스 테이블 생성 (앱 시작 시 호출)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """비동기 DB 세션 제너레이터 (FastAPI Depends 용도)"""
    async with AsyncSessionLocal() as session:
        yield session