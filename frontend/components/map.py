import folium
from streamlit_folium import st_folium


def render_map(lat, lon, score=100):
    color = "green" if score >= 70 else "orange" if score >= 40 else "red"
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB positron")

    # 🚨 팝업 글씨 가로 고정 (white-space: nowrap)
    popup_html = folium.Popup('<div style="white-space: nowrap; font-weight: bold; font-size: 14px;">선택 지역</div>',
                              max_width=200)

    folium.Marker(
        [lat, lon],
        popup=popup_html,
        icon=folium.Icon(color=color, icon="info-sign")
    ).add_to(m)
    st_folium(m, use_container_width=True, height=400)


def render_national_overview_map():
    # 대한민국 중심 좌표
    m = folium.Map(location=[36.0, 127.5], zoom_start=7, tiles="CartoDB positron")

    # 전국 17개 주요 시/도 대표 좌표 (시각적 파악용)
    points = [
        {"name": "서울특별시", "lat": 37.5665, "lon": 126.9780, "color": "green"},
        {"name": "인천광역시", "lat": 37.4563, "lon": 126.7052, "color": "orange"},
        {"name": "경기도", "lat": 37.2747, "lon": 127.0096, "color": "green"},
        {"name": "강원특별자치도", "lat": 37.8228, "lon": 128.1555, "color": "green"},
        {"name": "충청남도", "lat": 36.6588, "lon": 126.6728, "color": "orange"},
        {"name": "충청북도", "lat": 36.6353, "lon": 127.4913, "color": "orange"},
        {"name": "세종특별자치시", "lat": 36.4800, "lon": 127.2890, "color": "green"},
        {"name": "대전광역시", "lat": 36.3504, "lon": 127.3845, "color": "orange"},
        {"name": "전북특별자치도", "lat": 35.8202, "lon": 127.1086, "color": "orange"},
        {"name": "전라남도", "lat": 34.8159, "lon": 126.4629, "color": "green"},
        {"name": "광주광역시", "lat": 35.1595, "lon": 126.8526, "color": "green"},
        {"name": "경상북도", "lat": 36.5760, "lon": 128.5058, "color": "orange"},
        {"name": "경상남도", "lat": 35.2377, "lon": 128.6923, "color": "green"},
        {"name": "대구광역시", "lat": 35.8714, "lon": 128.6014, "color": "orange"},
        {"name": "울산광역시", "lat": 35.5384, "lon": 129.3114, "color": "green"},
        {"name": "부산광역시", "lat": 35.1796, "lon": 129.0756, "color": "red"},
        {"name": "제주특별자치도", "lat": 33.4996, "lon": 126.5312, "color": "green"}
    ]

    for p in points:
        # 🚨 팝업 글씨 가로 고정 적용
        popup_html = folium.Popup(
            f'<div style="white-space: nowrap; font-weight: bold; font-size: 13px;">{p["name"]}</div>', max_width=200)

        folium.CircleMarker(
            location=[p['lat'], p['lon']], radius=10, popup=popup_html, color=p['color'],
            fill=True, fill_color=p['color'], fill_opacity=0.7
        ).add_to(m)

    st_folium(m, use_container_width=True, height=650)