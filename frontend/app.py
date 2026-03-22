import os
import requests
import streamlit as st
from components.ui import apply_glassmorphism, render_metric_card
from components.map import render_map

# BE 연결 URL (도커 환경 대응)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AirGuard Dashboard", page_icon="🍃", layout="wide")
apply_glassmorphism()

st.title("🍃 스마트 환기 및 야외 운동 알리미")

# 사이드바: 지역 선택 UI
st.sidebar.header("🗺️ 지역 선택")
try:
    res = requests.get(f"{BACKEND_URL}/api/regions")
    regions_data = res.json()
    if regions_data:
        region_options = {r["name"]: r["code"] for r in regions_data}
        selected_name = st.sidebar.selectbox("행정구역을 선택하세요", list(region_options.keys()))
        selected_code = region_options[selected_name]
    else:
        st.sidebar.warning("등록된 지역 데이터가 없습니다.")
        selected_code = None
except Exception as e:
    st.sidebar.error("백엔드 서버와 연결할 수 없습니다.")
    selected_code = None

# 새로고침 버튼
if st.sidebar.button("🔄 데이터 새로고침"):
    st.rerun()

# 메인 대시보드
if selected_code:
    with st.spinner("공공데이터를 분석 중입니다..."):
        try:
            res = requests.get(f"{BACKEND_URL}/api/dashboard/{selected_code}")
            if res.status_code == 200:
                data = res.json()

                if data.get("is_fallback"):
                    st.warning("⚠️ 현재 공공데이터 API 응답 지연으로, 최근 저장된 이전 데이터를 표시합니다.")

                col1, col2 = st.columns(2)
                with col1:
                    render_metric_card("환기 적합도", f"{data['ventilation_score']}점", "fas fa-wind", "미세먼지, 강수량 기준 산출")
                with col2:
                    render_metric_card("야외 활동 적합도", f"{data['outdoor_score']}점", "fas fa-running",
                                       "기온, 자외선, 미세먼지 기준 산출")

                st.markdown("---")
                st.subheader("📊 상세 관측 데이터")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    render_metric_card("기온", f"{data['temperature']}°C", "fas fa-temperature-half")
                with c2:
                    render_metric_card("미세먼지(PM10)", f"{data['pm10']} µg/m³", "fas fa-smog")
                with c3:
                    render_metric_card("자외선 지수", f"{data['uv_index']}", "fas fa-sun")
                with c4:
                    render_metric_card("강수 확률", f"{data['rain_prob']}%", "fas fa-cloud-rain")

                st.markdown("---")
                st.subheader("📍 지역 기반 적합도 지도")
                render_map(lat=data['lat'], lon=data['lon'], score=data['outdoor_score'])

            else:
                st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            st.error(f"대시보드 로딩 중 오류가 발생했습니다: {str(e)}")
else:
    st.info("👈 좌측 사이드바에서 지역을 선택하여 분석을 시작하세요.")