import folium
from streamlit_folium import st_folium


def render_map(lat, lon, station_lat=None, station_lon=None, score=100):
    # 점수에 따른 마커 색상 결정
    color = "blue" if score >= 70 else "orange" if score >= 40 else "red"

    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB positron")

    # 사용자 위치 핀
    folium.Marker(
        [lat, lon],
        popup="선택 지역",
        icon=folium.Icon(color=color, icon="info-sign")
    ).add_to(m)

    # 범례 HTML 오버레이
    legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 120px; height: 110px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:rgba(255, 255, 255, 0.8);
     border-radius: 10px; padding: 10px;">
     <b>적합도 상태</b><br>
     <i class="fa fa-map-marker" style="color:blue"></i> 좋음 (70+)<br>
     <i class="fa fa-map-marker" style="color:orange"></i> 보통 (40+)<br>
     <i class="fa fa-map-marker" style="color:red"></i> 나쁨 (<40)
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width=700, height=400)