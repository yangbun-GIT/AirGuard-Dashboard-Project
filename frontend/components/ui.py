import streamlit as st

def apply_glassmorphism():
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
        .stApp {
            background: linear-gradient(135deg, #e0eafc, #cfdef3);
            color: #1a202c;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.4);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 15px;
            padding: 20px;
            margin: 10px 0px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
            color: #1a202c !important;
        }
        .glass-card h3 { color: #2c3e50 !important; font-weight: bold; }
        .glass-card h1 { color: #2980b9 !important; font-weight: 900; margin-top: -10px;}
        </style>
    """, unsafe_allow_html=True)

def render_metric_card(title, value, icon_class, desc=""):
    html = f"""
    <div class="glass-card">
        <h3><i class="{icon_class}"></i> {title}</h3>
        <h1>{value}</h1>
        <p style="margin:0; font-size:14px; color:#34495e;">{desc}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)