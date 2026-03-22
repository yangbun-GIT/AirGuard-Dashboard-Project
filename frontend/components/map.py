import folium
from streamlit_folium import st_folium


def render_map(lat, lon, score=100):
    color = "green" if score >= 70 else "orange" if score >= 40 else "red"
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB positron")
    folium.Marker([lat, lon], popup="선택 지역", icon=folium.Icon(color=color, icon="info-sign")).add_to(m)
    st_folium(m, use_container_width=True, height=400)


def render_national_overview_map():
    m = folium.Map(location=[36.3, 127.5], zoom_start=7, tiles="CartoDB positron")
    points = [
        {"name": "서울", "lat": 37.5665, "lon": 126.9780, "color": "green"},
        {"name": "강원", "lat": 37.8228, "lon": 128.1555, "color": "green"},
        {"name": "대전", "lat": 36.3504, "lon": 127.3845, "color": "orange"},
        {"name": "대구", "lat": 35.8714, "lon": 128.6014, "color": "orange"},
        {"name": "부산", "lat": 35.1796, "lon": 129.0756, "color": "red"},
        {"name": "제주", "lat": 33.4996, "lon": 126.5312, "color": "green"}
    ]
    for p in points:
        folium.CircleMarker(
            location=[p['lat'], p['lon']], radius=12, popup=p['name'], color=p['color'],
            fill=True, fill_color=p['color'], fill_opacity=0.7
        ).add_to(m)

    # 🚨 height를 650으로 대폭 확대하여 세로로 길게 표시
    st_folium(m, use_container_width=True, height=650)