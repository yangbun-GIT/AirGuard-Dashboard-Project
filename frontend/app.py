import os
import requests
import pandas as pd
import streamlit as st
from components.ui import apply_glassmorphism, render_metric_card, render_score_card
from components.map import render_map, render_national_overview_map

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AirGuard Dashboard", page_icon="🍃", layout="wide")
apply_glassmorphism()

st.title("🍃 스마트 환기 및 야외 운동 알리미")

with st.expander("🗺️ 전국 주요 지역 기상/대기 요약 보기", expanded=False):
    st.markdown("**전반적인 전국 상태를 간략하게 파악합니다.** (🟢좋음 🟡보통 🔴나쁨)")
    render_national_overview_map()

st.markdown("---")

st.sidebar.header("🗺️ 내 지역 선택")
selected_code = None

try:
    res = requests.get(f"{BACKEND_URL}/api/regions")
    if res.status_code == 200:
        regions_data = res.json()
        if regions_data:
            df = pd.DataFrame(regions_data)

            # 단계 1: 시/도
            sido_list = df['sido'].unique().tolist()
            selected_sido = st.sidebar.selectbox("1. 시/도를 선택하세요", sido_list)

            # 단계 2: 시/군/구 (선택한 시/도 기준 필터링)
            sigungu_df = df[df['sido'] == selected_sido]
            sigungu_list = sigungu_df['sigungu'].unique().tolist()
            selected_sigungu = st.sidebar.selectbox("2. 시/군/구를 선택하세요", sigungu_list)

            selected_code = sigungu_df[sigungu_df['sigungu'] == selected_sigungu]['code'].values[0]
        else:
            st.sidebar.warning("등록된 지역 데이터가 없습니다.")
except Exception as e:
    st.sidebar.error("백엔드 서버와 연결할 수 없습니다.")

if st.sidebar.button("🔄 현재 지역 날씨 새로고침"):
    st.rerun()

if selected_code:
    with st.spinner(f"[{selected_sigungu}] 공공데이터를 분석 중입니다..."):
        try:
            res = requests.get(f"{BACKEND_URL}/api/dashboard/{selected_code}")
            if res.status_code == 200:
                data = res.json()

                if data.get("is_fallback"):
                    st.warning("⚠️ 현재 공공데이터 API 응답 지연으로, 최근 저장된 이전 데이터를 표시합니다.")

                col1, col2 = st.columns(2)
                with col1:
                    render_score_card("환기 적합도", data['ventilation_score'], "fas fa-wind", "미세먼지, 강수량 기준 산출")
                with col2:
                    render_score_card("야외 활동 적합도", data['outdoor_score'], "fas fa-running", "기온, 자외선, 미세먼지 기준 산출")

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
                st.subheader(f"📍 {selected_sigungu} 기반 지역 적합도 지도")
                render_map(lat=data['lat'], lon=data['lon'], score=data['outdoor_score'])

            else:
                st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            st.error(f"대시보드 로딩 중 오류가 발생했습니다.")
else:
    st.info("👈 좌측 사이드바에서 지역을 선택하여 분석을 시작하세요.")