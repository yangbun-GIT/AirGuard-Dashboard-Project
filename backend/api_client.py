import os
import math
import httpx
from pyproj import Transformer
from datetime import datetime, timedelta

SERVICE_KEY = os.getenv("SERVICE_KEY", "YOUR_SERVICE_KEY")


def lat_lon_to_tm(lat, lon):
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5181", always_xy=True)
    tm_x, tm_y = transformer.transform(lon, lat)
    return tm_x, tm_y


async def fetch_nearby_station(lat: float, lon: float) -> str:
    tm_x, tm_y = lat_lon_to_tm(lat, lon)
    url = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getNearbyMsrstnList"
    params = {"serviceKey": SERVICE_KEY, "returnType": "json", "tmX": tm_x, "tmY": tm_y}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        data = response.json()
        if data.get("response", {}).get("header", {}).get("resultCode") == "00":
            items = data["response"]["body"]["items"]
            if items: return items[0]["stationName"]
        raise Exception("측정소 정보를 불러오지 못했습니다.")


async def fetch_air_quality(station_name: str) -> dict:
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
    params = {"serviceKey": SERVICE_KEY, "returnType": "json", "numOfRows": 1, "pageNo": 1, "stationName": station_name,
              "dataTerm": "DAILY", "ver": "1.0"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        data = response.json()
        if data.get("response", {}).get("header", {}).get("resultCode") == "00":
            items = data["response"]["body"]["items"]
            if items:
                # 관측소 점검 등으로 데이터가 "-"로 올 때의 에러를 방지합니다.
                pm10_val = items[0].get("pm10Value")
                pm25_val = items[0].get("pm25Value")
                pm10 = float(pm10_val) if pm10_val and pm10_val != "-" else 0.0
                pm25 = float(pm25_val) if pm25_val and pm25_val != "-" else 0.0
                return {"pm10": pm10, "pm25": pm25}
        return {"pm10": 0.0, "pm25": 0.0}


async def fetch_weather(nx: int, ny: int) -> dict:
    # 🚨 단기예보(getVilageFcst) -> 초단기실황(getUltraSrtNcst)으로 변경!
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    now = datetime.now()

    # 초단기실황은 매시간 40분에 발표됩니다. (예: 10시 40분에 10시 실황 발표)
    if now.minute < 40:
        now = now - timedelta(hours=1)

    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")

    params = {"serviceKey": SERVICE_KEY, "dataType": "JSON", "numOfRows": 20, "pageNo": 1, "base_date": base_date,
              "base_time": base_time, "nx": nx, "ny": ny}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        data = response.json()

        result = {"temperature": 0.0, "rain_prob": 0.0}

        if data.get("response", {}).get("header", {}).get("resultCode") == "00":
            items = data["response"]["body"]["items"]["item"]
            for item in items:
                # T1H: 현재 실황 기온
                if item["category"] == "T1H":
                    result["temperature"] = float(item["obsrValue"])
                # PTY: 현재 강수 형태 (0:없음, 1:비, 2:비/눈, 3:눈, 4:소나기)
                if item["category"] == "PTY":
                    pty_val = int(item["obsrValue"])
                    # 현재 비나 눈이 오고 있다면 강수확률을 100%로 취급하여 환기/야외활동 점수 대폭 차감
                    result["rain_prob"] = 100.0 if pty_val > 0 else 0.0
        return result


async def fetch_uv_index(code: str) -> float:
    url = "http://apis.data.go.kr/1360000/LivingWthrIdxServiceV4/getUVIdxV4"
    now = datetime.now()
    area_no = str(code)[:10]
    params = {"ServiceKey": SERVICE_KEY, "dataType": "JSON", "areaNo": area_no, "time": now.strftime("%Y%m%d%H")}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()
            if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                return float(data["response"]["body"]["items"]["item"][0]["h0"])
        except:
            pass
    return 3.0  # 에러 시 기본값