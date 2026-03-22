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
                return {"pm10": float(items[0].get("pm10Value", 0) or 0),
                        "pm25": float(items[0].get("pm25Value", 0) or 0)}
        return {"pm10": 0.0, "pm25": 0.0}


async def fetch_weather(nx: int, ny: int) -> dict:
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    now = datetime.now()

    # 기상청 단기예보 기준시간 알고리즘 (02, 05, 08, 11, 14, 17, 20, 23시)
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    target_hour = -1
    for bt in reversed(base_times):
        # 발표 후 15분 뒤부터 조회 안전권
        if now.hour > bt or (now.hour == bt and now.minute >= 15):
            target_hour = bt
            break

    if target_hour == -1:  # 자정~02시 사이면 전날 23시 데이터 사용
        now = now - timedelta(days=1)
        target_hour = 23

    base_date = now.strftime("%Y%m%d")
    base_time = f"{target_hour:02d}00"

    params = {"serviceKey": SERVICE_KEY, "dataType": "JSON", "numOfRows": 100, "pageNo": 1, "base_date": base_date,
              "base_time": base_time, "nx": nx, "ny": ny}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        data = response.json()
        result = {"temperature": 0.0, "rain_prob": 0.0}

        if data.get("response", {}).get("header", {}).get("resultCode") == "00":
            items = data["response"]["body"]["items"]["item"]
            for item in items:
                if item["category"] == "TMP": result["temperature"] = float(item["fcstValue"])
                if item["category"] == "POP": result["rain_prob"] = float(item["fcstValue"])
        return result


async def fetch_uv_index(code: str) -> float:
    url = "http://apis.data.go.kr/1360000/LivingWthrIdxServiceV4/getUVIdxV4"
    now = datetime.now()
    area_no = str(code)[:10]  # 행정구역코드
    params = {"ServiceKey": SERVICE_KEY, "dataType": "JSON", "areaNo": area_no, "time": now.strftime("%Y%m%d%H")}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()
            if data.get("response", {}).get("header", {}).get("resultCode") == "00":
                return float(data["response"]["body"]["items"]["item"][0]["h0"])
        except:
            pass
    return 3.0