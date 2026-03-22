import streamlit as st


def apply_glassmorphism():
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
        /* 다크모드/라이트모드 자동 감지 반응형 카드 */
        .glass-card {
            background-color: var(--secondary-background-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin: 10px 0px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .glass-card h3 { font-size: 1.1rem; color: var(--text-color); font-weight: bold; opacity: 0.9;}
        .glass-card h1 { color: var(--text-color); font-weight: 900; margin-top: -10px;}

        /* 게이지바(Progress Bar) 디자인 */
        .score-bar-container {
            width: 100%;
            background-color: var(--background-color);
            border-radius: 10px;
            margin-top: 15px;
            height: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }
        .score-bar {
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease-in-out;
        }
        .score-labels {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin-top: 5px;
            color: var(--text-color);
            opacity: 0.7;
        }
        </style>
    """, unsafe_allow_html=True)


def render_metric_card(title, value, icon_class, desc=""):
    html = f"""
    <div class="glass-card">
        <h3><i class="{icon_class}" style="color: #3498db;"></i> {title}</h3>
        <h1>{value}</h1>
        <p style="margin:0; font-size:13px; opacity:0.8;">{desc}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_score_card(title, score, icon_class, desc=""):
    # 점수 가이드라인 판단
    if score >= 70:
        color = "#2ecc71"  # 초록 (좋음)
        status = "🟢 좋음"
    elif score >= 40:
        color = "#f1c40f"  # 노랑 (보통)
        status = "🟡 보통"
    else:
        color = "#e74c3c"  # 빨강 (나쁨)
        status = "🔴 나쁨"

    html = f"""
    <div class="glass-card" style="border-top: 4px solid {color};">
        <h3><i class="{icon_class}"></i> {title} : {status}</h3>
        <h1>{score}점</h1>
        <p style="margin:0 0 10px 0; font-size:13px; opacity:0.8;">{desc}</p>

        <div class="score-bar-container">
            <div class="score-bar" style="width: {score}%; background-color: {color};"></div>
        </div>
        <div class="score-labels">
            <span>나쁨(0)</span>
            <span>보통(40)</span>
            <span>좋음(70~100)</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)