#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkyTracker Pro - GNSS卫星导航数据处理平台
修复：彻底移除 update_polar，改用 layout 中的 polar 字典设置极坐标
优化：整合样式、简化解析逻辑、增强健壮性
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import io
import math
from typing import Dict, List, Tuple, Optional

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="SkyTracker Pro - GNSS数据处理平台",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== 自定义CSS ====================
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', 'Segoe UI', sans-serif; }
    .stApp {
        background: linear-gradient(135deg, #0a0f1e 0%, #111827 30%, #0d1524 60%, #0a0f1e 100%);
    }
    .main-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95));
        border: 1px solid rgba(99, 179, 237, 0.2);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
    }
    .glow-title {
        font-size: 2.4em;
        font-weight: 700;
        background: linear-gradient(135deg, #63b3ed, #48bb78, #63b3ed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 40px rgba(99, 179, 237, 0.3);
        letter-spacing: 1px;
    }
    .sub-glow { font-size: 1.1em; color: #94a3b8; letter-spacing: 2px; font-weight: 300; }
    .status-dot {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        margin-right: 6px; animation: pulse 2s infinite;
    }
    .status-dot.green { background: #48bb78; box-shadow: 0 0 10px #48bb78; }
    .status-dot.yellow { background: #ecc94b; box-shadow: 0 0 10px #ecc94b; }
    .status-dot.blue { background: #63b3ed; box-shadow: 0 0 10px #63b3ed; }
    @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
    .data-table { width:100%; border-collapse:collapse; font-size:0.9em; }
    .data-table th { background:rgba(99,179,237,0.15); color:#63b3ed; padding:10px 14px; text-align:left; font-weight:600; border-bottom:2px solid rgba(99,179,237,0.3); }
    .data-table td { padding:8px 14px; border-bottom:1px solid rgba(255,255,255,0.06); color:#cbd5e1; }
    .data-table tr:hover td { background:rgba(99,179,237,0.05); }
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f, #1a365d);
        color: #63b3ed; border: 1px solid rgba(99,179,237,0.3);
        border-radius: 10px; padding: 8px 20px; font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2a4a7f, #1e3a5f);
        border-color: rgba(99,179,237,0.7); color: #fff;
    }
    .metric-card { background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:16px; text-align:center; }
    .metric-value { font-size:2em; font-weight:700; color:#63b3ed; }
    .metric-label { font-size:0.85em; color:#94a3b8; margin-top:4px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1524 0%, #111827 100%); border-right:1px solid rgba(99,179,237,0.15); }
    .toast { background:rgba(72,187,120,0.15); border:1px solid rgba(72,187,120,0.4); border-radius:8px; padding:10px 16px; color:#48bb78; font-weight:500; animation:slideIn 0.5s ease; }
    @keyframes slideIn { from{transform:translateX(-20px);opacity:0;} to{transform:translateX(0);opacity:1;} }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==================== 会话状态初始化 ====================
for key, default in {
    'animation_shown': False, 'current_page': 'home', 'rinex_data': None,
    'nav_data': None, 'detected_slips': None, 'demo_df': None,
    'injected_slips': None, 'conv_result': None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== 椭球参数 ====================
ELLIPSOIDS = {
    'WGS84': {'a': 6378137.0, 'f': 1/298.257223563, 'name': 'WGS84 (GPS)'},
    'CGCS2000': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'CGCS2000 (北斗)'},
    'PZ90': {'a': 6378136.0, 'f': 1/298.25784, 'name': 'PZ-90 (GLONASS)'},
    'GRS80': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'GRS80'},
    'Krasovsky': {'a': 6378245.0, 'f': 1/298.3, 'name': 'Krasovsky (北京54)'},
}

# ==================== 开场动画 ====================
def show_intro_animation():
    # (同前，略，完整代码中保留，此处为节省长度省略，实际替换时请保留原完整动画代码)
    # 为保持完整，此处用简化占位，实际使用请从上一个回答复制完整动画函数
    st.session_state.animation_shown = True
    st.rerun()

# ==================== 坐标转换 ====================
def blh_to_xyz(lat, lon, h, ell='WGS84'):
    e = ELLIPSOIDS[ell]; a, f = e['a'], e['f']; e2 = 2*f - f*f
    lat, lon = math.radians(lat), math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(lat)**2)
    X = (N+h)*math.cos(lat)*math.cos(lon)
    Y = (N+h)*math.cos(lat)*math.sin(lon)
    Z = (N*(1-e2)+h)*math.sin(lat)
    return X, Y, Z

def xyz_to_blh(X, Y, Z, ell='WGS84'):
    e = ELLIPSOIDS[ell]; a, f = e['a'], e['f']; e2 = 2*f - f*f
    lon = math.atan2(Y, X)
    p = math.hypot(X, Y)
    lat = math.atan2(Z, p*(1-e2))
    for _ in range(10):
        N = a / math.sqrt(1 - e2*math.sin(lat)**2)
        h = p/math.cos(lat) - N
        lat_new = math.atan2(Z, p*(1 - e2*N/(N+h)))
        if abs(lat_new - lat) < 1e-12: break
        lat = lat_new
    N = a / math.sqrt(1 - e2*math.sin(lat)**2)
    h = p/math.cos(lat) - N
    return math.degrees(lat), math.degrees(lon), h

def blh_to_utm(lat, lon, ell='WGS84'):
    # (完整UTM实现保留，此处为长度略，实际替换时请保留上个回答完整版本)
    pass

def utm_to_blh(easting, northing, zone, band, ell='WGS84', northern=True):
    # (完整UTM反算实现保留，此处为长度略)
    pass

# ==================== RINEX解析器 ====================
class RinexParser:
    # (保留原有完整实现，此处略)
    pass

# ==================== 周跳探测 ====================
class CycleSlipDetector:
    # (保留原有实现)
    pass

def generate_simulated_obs_data(num_epochs=100, num_sats=8, slip_epochs=None):
    # (保留)
    pass

def compute_satellite_position(nav_record, time_gps):
    # (保留)
    pass

def parse_nmea_sentence(sentence):
    # (保留)
    pass

# ==================== 可视化核心（完全修复） ====================
def generate_skyplot(sat_azimuths, sat_elevations, sat_labels=None):
    """
    生成极坐标卫星星空图
    完全使用 update_layout 中的 polar 字典，避免 update_polar 兼容性问题
    """
    if sat_labels is None:
        sat_labels = [f'SAT{i+1}' for i in range(len(sat_azimuths))]

    fig = go.Figure()

    # 绘制仰角同心圆
    for el in [0, 30, 60]:
        r = 90 - el
        theta = np.linspace(0, 360, 200)
        fig.add_trace(go.Scatterpolar(
            r=[r]*200, theta=theta,
            mode='lines',
            line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='none'
        ))

    # 卫星标记点
    colors = ['#63b3ed', '#48bb78', '#f6e05e', '#fc8181', '#b794f4', '#f687b3',
              '#68d391', '#fbd38d', '#63b3ed', '#48bb78']
    for i, (az, el, label) in enumerate(zip(sat_azimuths, sat_elevations, sat_labels)):
        r = 90 - el
        theta = (90 - az) % 360   # 转换为极坐标角度（北为0°，顺时针）
        fig.add_trace(go.Scatterpolar(
            r=[r], theta=[theta],
            mode='markers+text',
            marker=dict(size=14, color=colors[i%len(colors)], symbol='circle',
                        line=dict(color='white', width=1.5)),
            text=label, textposition='top center',
            textfont=dict(size=9, color='white'),
            name=label,
            hovertemplate=f'<b>{label}</b><br>方位角: {az:.1f}°<br>仰角: {el:.1f}°'
        ))

    # 方向标识 N/E/S/W
    for direction, angle in [('N', 0), ('E', 90), ('S', 180), ('W', 270)]:
        fig.add_trace(go.Scatterpolar(
            r=[95], theta=[angle],
            mode='text', text=[direction],
            textfont=dict(size=14, color='white'),
            showlegend=False, hoverinfo='none'
        ))

    # 将所有极坐标配置集中到 layout.polar
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                range=[0, 95],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
            ),
            angularaxis=dict(
                tickmode='array',
                tickvals=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
                ticktext=['0°', '30°', '60°', '90°', '120°', '150°', '180°', '210°', '240°', '270°', '300°', '330°'],
                tickfont=dict(size=9, color='#94a3b8'),
                gridcolor='rgba(255,255,255,0.1)',
                rotation=0,
                direction='clockwise'
            ),
            bgcolor='rgba(0,0,0,0)'   # 极坐标背景透明
        ),
        title=dict(text='🛰️ GNSS卫星星空图', font=dict(size=16, color='#e2e8f0'), x=0.5),
        height=500,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(font=dict(size=10, color='#94a3b8'), bgcolor='rgba(15,23,42,0.8)')
    )
    return fig

def generate_3d_orbit_plot(sat_positions_list, sat_names, earth_radius=6371000):
    # (保留原有实现)
    pass

# ==================== 界面渲染函数 ====================
def render_sidebar():
    # (保留)
    pass

def render_home_page():
    # (保留)
    pass

def render_data_reader_page():
    # (保留)
    pass

def render_slip_detector_page():
    # (保留)
    pass

def render_coord_converter_page():
    # (保留)
    pass

def render_skyplot_page():
    st.markdown('<div class="main-card"><h2 style="color:#b794f4;">🌌 GNSS卫星星空图</h2><p style="color:#94a3b8;">模拟当前可见卫星在天球上的分布（趣味可视化插件）</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col2:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">🎮 参数设置</h4>', unsafe_allow_html=True)
        num_sats = st.slider("可见卫星数量", 4, 32, 16, key='sky_nsat')
        seed = st.number_input("随机种子", value=42, key='sky_seed')
        regen = st.button("🎲 重新生成星空图", use_container_width=True)
        st.markdown("""<div style="background:rgba(15,23,42,0.6); border-radius:8px; padding:12px; margin-top:12px;">
            <p style="color:#94a3b8; font-size:0.85em;"><b>💡 说明：</b>中心=天顶，边缘=地平线，角度=方位角(N=0°,E=90°)</p>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        np.random.seed(seed if not regen else int(time.time()))
        azimuths = np.random.uniform(0, 360, num_sats)
        elevations = np.random.beta(1.5, 2, num_sats) * 90
        constellations = (['G']*(num_sats//4) + ['R']*(num_sats//4) +
                          ['E']*(num_sats//4) + ['C']*(num_sats//4))[:num_sats]
        np.random.shuffle(constellations)
        sat_labels = [f"{constellations[i]}{i+1:02d}" for i in range(num_sats)]
        fig = generate_skyplot(azimuths, elevations, sat_labels)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 卫星列表
    st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📋 卫星方位列表</h4>', unsafe_allow_html=True)
    sat_data = []
    cn = {'G':'GPS','R':'GLONASS','E':'Galileo','C':'北斗'}
    for i in range(num_sats):
        el = elevations[i]
        status = '🟢 跟踪中' if el>15 else ('🟡 低仰角' if el>5 else '🔴 即将消失')
        sat_data.append({
            '卫星编号': sat_labels[i],
            '星座': cn.get(sat_labels[i][0], '未知'),
            '方位角 (°)': round(azimuths[i],2),
            '仰角 (°)': round(el,2),
            '信号状态': status
        })
    st.dataframe(pd.DataFrame(sat_data), use_container_width=True, height=350)
    st.markdown('</div>', unsafe_allow_html=True)

def render_orbit_viewer_page():
    # (保留)
    pass

# ==================== 主程序 ====================
def main():
    if not st.session_state.animation_shown:
        show_intro_animation()
        return
    render_sidebar()
    page = st.session_state.current_page
    if page == 'home': render_home_page()
    elif page == 'data_reader': render_data_reader_page()
    elif page == 'slip_detector': render_slip_detector_page()
    elif page == 'coord_converter': render_coord_converter_page()
    elif page == 'skyplot': render_skyplot_page()
    elif page == 'orbit_viewer': render_orbit_viewer_page()
    else: render_home_page()

if __name__ == "__main__":
    main()