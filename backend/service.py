# backend/service.py

def calculate_scores(pm10: float, pm25: float, temp: float, rain: float, uv: float):
    """
    수집된 기상 및 대기 데이터를 바탕으로 환기 및 야외활동 적합도(0~100점)를 계산합니다.
    """
    # 환기 지수 계산 (미세먼지, 강수 확률 기반)
    vent_score = 100
    if rain > 50:
        vent_score -= 50
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

    if pm10 > 80 or pm25 > 35:
        out_score -= 40
    if rain > 40:
        out_score -= 50

    return max(0, vent_score), max(0, out_score)