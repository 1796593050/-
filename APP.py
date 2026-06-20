#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkyTracker Pro - GNSS卫星导航数据处理平台
功能：RINEX数据读取、周跳探测、坐标转换、卫星星空图、3D轨道可视化
支持格式：RINEX 2.x/3.x 观测文件、导航文件、NMEA-0183、CSV
修复：修复星空图update_polar参数错误，优化整体代码结构
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
from typing import List, Dict, Optional, Tuple

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
        transition: all 0.3s ease;
    }
    .main-card:hover {
        border-color: rgba(99, 179, 237, 0.5);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(99, 179, 237, 0.1);
        transform: translateY(-2px);
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
    .sub-glow {
        font-size: 1.1em;
        color: #94a3b8;
        letter-spacing: 2px;
        font-weight: 300;
    }
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .status-dot.green { background: #48bb78; box-shadow: 0 0 10px #48bb78; }
    .status-dot.yellow { background: #ecc94b; box-shadow: 0 0 10px #ecc94b; }
    .status-dot.blue { background: #63b3ed; box-shadow: 0 0 10px #63b3ed; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9em;
    }
    .data-table th {
        background: rgba(99, 179, 237, 0.15);
        color: #63b3ed;
        padding: 10px 14px;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid rgba(99, 179, 237, 0.3);
    }
    .data-table td {
        padding: 8px 14px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        color: #cbd5e1;
    }
    .data-table tr:hover td {
        background: rgba(99, 179, 237, 0.05);
    }
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f, #1a365d);
        color: #63b3ed;
        border: 1px solid rgba(99, 179, 237, 0.3);
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2a4a7f, #1e3a5f);
        border-color: rgba(99, 179, 237, 0.7);
        box-shadow: 0 4px 16px rgba(99, 179, 237, 0.2);
        color: #fff;
    }
    .metric-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 2em;
        font-weight: 700;
        color: #63b3ed;
    }
    .metric-label {
        font-size: 0.85em;
        color: #94a3b8;
        margin-top: 4px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1524 0%, #111827 100%);
        border-right: 1px solid rgba(99, 179, 237, 0.15);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #cbd5e1;
    }
    .orbit-container {
        position: relative;
        width: 300px;
        height: 300px;
        margin: 0 auto;
    }
    .toast {
        background: rgba(72, 187, 120, 0.15);
        border: 1px solid rgba(72, 187, 120, 0.4);
        border-radius: 8px;
        padding: 10px 16px;
        color: #48bb78;
        font-weight: 500;
        animation: slideIn 0.5s ease;
    }
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==================== 会话状态初始化 ====================
session_defaults = {
    'animation_shown': False,
    'current_page': 'home',
    'rinex_data': None,
    'nav_data': None,
    'detected_slips': None,
    'demo_df': None,
    'injected_slips': None,
    'conv_result': None,
}
for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== 地球椭球参数 ====================
ELLIPSOIDS = {
    'WGS84': {'a': 6378137.0, 'f': 1 / 298.257223563, 'name': 'WGS84 (GPS)'},
    'CGCS2000': {'a': 6378137.0, 'f': 1 / 298.257222101, 'name': 'CGCS2000 (北斗)'},
    'PZ90': {'a': 6378136.0, 'f': 1 / 298.25784, 'name': 'PZ-90 (GLONASS)'},
    'GRS80': {'a': 6378137.0, 'f': 1 / 298.257222101, 'name': 'GRS80'},
    'Krasovsky': {'a': 6378245.0, 'f': 1 / 298.3, 'name': 'Krasovsky (北京54)'},
}

# ==================== 开场动画 ====================
def show_intro_animation():
    """卫星环绕地球开场动画，5秒后自动进入主界面"""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div style="height:60px;"></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center;">
                <div style="position:relative; width:300px; height:300px; margin:0 auto;">
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
                         width:90px; height:90px; border-radius:50%;
                         background: radial-gradient(circle at 38% 32%, #7ec8f8 0%, #2980b9 35%, #0d3b66 70%, #061a2e 100%);
                         box-shadow: 0 0 60px rgba(41,128,185,0.7), 0 0 120px rgba(41,128,185,0.35), 0 0 200px rgba(41,128,185,0.15);
                         z-index:5; animation: earthPulse 3s ease-in-out infinite;">
                    </div>
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(-30deg);
                         width:220px; height:220px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.2); z-index:2;
                         animation: orbitSpin 10s linear infinite;"></div>
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(45deg);
                         width:260px; height:260px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.13); z-index:1;
                         animation: orbitSpin 14s linear infinite reverse;"></div>
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(80deg);
                         width:180px; height:180px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.17); z-index:3;
                         animation: orbitSpin 8s linear infinite;"></div>
                    <div style="position:absolute; top:50%; left:50%; z-index:6;
                         animation: satelliteFly1 5s linear infinite;">
                        <div style="width:10px; height:10px; background:#fff; border-radius:50%;
                             box-shadow: 0 0 15px #63b3ed, 0 0 30px rgba(99,179,237,0.7);
                             position:relative; left:110px; top:-5px;"></div>
                    </div>
                    <div style="position:absolute; top:50%; left:50%; z-index:6;
                         animation: satelliteFly2 7s linear infinite;">
                        <div style="width:8px; height:8px; background:#ffd700; border-radius:50%;
                             box-shadow: 0 0 12px #ffd700, 0 0 24px rgba(255,215,0,0.6);
                             position:relative; left:130px; top:-4px;"></div>
                    </div>
                    <div style="position:absolute; top:50%; left:50%; z-index:6;
                         animation: satelliteFly3 6.5s linear infinite;">
                        <div style="width:7px; height:7px; background:#48bb78; border-radius:50%;
                             box-shadow: 0 0 10px #48bb78, 0 0 20px rgba(72,187,120,0.5);
                             position:relative; left:90px; top:-3px;"></div>
                    </div>
                </div>
                <style>
                @keyframes earthPulse {
                    0%,100% { box-shadow: 0 0 60px rgba(41,128,185,0.7), 0 0 120px rgba(41,128,185,0.35); }
                    50% { box-shadow: 0 0 80px rgba(41,128,185,0.9), 0 0 150px rgba(41,128,185,0.5); }
                }
                @keyframes orbitSpin {
                    from { transform: translate(-50%,-50%) rotate(0deg); }
                    to { transform: translate(-50%,-50%) rotate(360deg); }
                }
                @keyframes satelliteFly1 {
                    0% { transform: rotate(0deg) translateX(110px); }
                    100% { transform: rotate(360deg) translateX(110px); }
                }
                @keyframes satelliteFly2 {
                    0% { transform: rotate(60deg) translateX(130px); }
                    100% { transform: rotate(420deg) translateX(130px); }
                }
                @keyframes satelliteFly3 {
                    0% { transform: rotate(180deg) translateX(90px); }
                    100% { transform: rotate(540deg) translateX(90px); }
                }
                </style>
                <h1 class="glow-title" style="margin-top:30px;">SkyTracker Pro</h1>
                <p class="sub-glow">GNSS 卫星导航数据处理平台</p>
                <p style="color:#94a3b8; font-size:0.9em; margin-top:10px;">
                    <span class="status-dot blue"></span> RINEX解析 
                    <span style="margin:0 12px;">|</span>
                    <span class="status-dot green"></span> 周跳探测 
                    <span style="margin:0 12px;">|</span>
                    <span class="status-dot yellow"></span> 坐标转换
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1.2, 1])
            with btn_col2:
                if st.button("🚀 进入平台", use_container_width=True, key="enter_btn"):
                    st.session_state.animation_shown = True
                    st.rerun()
            st.markdown("""
            <p style="text-align:center; color:#64748b; font-size:0.8em; margin-top:12px;">
                动画将在 5 秒后自动进入...
            </p>
            """, unsafe_allow_html=True)
            time.sleep(5)
            st.session_state.animation_shown = True
            st.rerun()

# ==================== 坐标转换工具 ====================
def blh_to_xyz(lat_deg: float, lon_deg: float, height: float, ellipsoid: str = 'WGS84') -> Tuple[float, float, float]:
    """大地坐标(BLH) 转 地心地固坐标(ECEF-XYZ)"""
    ell = ELLIPSOIDS[ellipsoid]
    a, f = ell['a'], ell['f']
    e2 = 2 * f - f ** 2
    lat_rad, lon_rad = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat_rad), math.cos(lat_rad)
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    X = (N + height) * cos_lat * math.cos(lon_rad)
    Y = (N + height) * cos_lat * math.sin(lon_rad)
    Z = (N * (1 - e2) + height) * sin_lat
    return X, Y, Z

def xyz_to_blh(X: float, Y: float, Z: float, ellipsoid: str = 'WGS84', max_iter: int = 10, tol: float = 1e-12) -> Tuple[float, float, float]:
    """ECEF-XYZ 转 大地坐标BLH (迭代法)"""
    ell = ELLIPSOIDS[ellipsoid]
    a, f = ell['a'], ell['f']
    e2 = 2 * f - f ** 2
    lon_rad = math.atan2(Y, X)
    p = math.sqrt(X**2 + Y**2)
    lat_rad = math.atan2(Z, p * (1 - e2))
    for _ in range(max_iter):
        sin_lat = math.sin(lat_rad)
        N = a / math.sqrt(1 - e2 * sin_lat ** 2)
        h = p / math.cos(lat_rad) - N
        lat_new = math.atan2(Z, p * (1 - e2 * N / (N + h)))
        if abs(lat_new - lat_rad) < tol:
            lat_rad = lat_new
            break
        lat_rad = lat_new
    sin_lat = math.sin(lat_rad)
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    height = p / math.cos(lat_rad) - N
    return math.degrees(lat_rad), math.degrees(lon_rad), height

def blh_to_utm(lat_deg: float, lon_deg: float, ellipsoid: str = 'WGS84') -> Tuple[float, float, int, str, str]:
    """大地坐标 转 UTM投影坐标，返回(东向, 北向, 带号, 纬度带, 完整带号)"""
    ell = ELLIPSOIDS[ellipsoid]
    a, f = ell['a'], ell['f']
    e2 = 2 * f - f ** 2
    e2_prime = e2 / (1 - e2)
    lat_rad, lon_rad = math.radians(lat_deg), math.radians(lon_deg)
    # 计算UTM带号
    zone = int((lon_deg + 180) / 6) + 1
    if lat_deg >= 56 and lat_deg < 64 and 3 <= lon_deg < 12:
        zone = 32
    if lat_deg >= 72 and lat_deg < 84:
        if 0 <= lon_deg < 9: zone = 31
        elif 9 <= lon_deg < 21: zone = 33
        elif 21 <= lon_deg < 33: zone = 35
        elif 33 <= lon_deg < 42: zone = 37
    lon0_deg = (zone - 1) * 6 - 180 + 3
    lon0_rad = math.radians(lon0_deg)
    sin_lat, cos_lat, tan_lat = math.sin(lat_rad), math.cos(lat_rad), math.tan(lat_rad)
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    T, C = tan_lat ** 2, e2_prime * cos_lat ** 2
    A = (lon_rad - lon0_rad) * cos_lat
    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat_rad
             - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat_rad)
             + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat_rad)
             - (35*e2**3/3072) * math.sin(6*lat_rad))
    k0 = 0.9996
    easting = k0 * N * (A + (1 - T + C) * A**3 / 6 
                        + (5 - 18*T + T**2 + 72*C - 58*e2_prime) * A**5 / 120) + 500000
    if lat_deg >= 0:
        northing = k0 * (M + N * tan_lat * (A**2/2 
                         + (5 - T + 9*C + 4*C**2) * A**4/24 
                         + (61 - 58*T + T**2 + 600*C - 330*e2_prime) * A**6/720))
    else:
        northing = k0 * (M + N * tan_lat * (A**2/2 
                         + (5 - T + 9*C + 4*C**2) * A**4/24 
                         + (61 - 58*T + T**2 + 600*C - 330*e2_prime) * A**6/720)) + 10000000
    # 纬度带
    bands = [('C', -80, -72), ('D', -72, -64), ('E', -64, -56), ('F', -56, -48),
             ('G', -48, -40), ('H', -40, -32), ('J', -32, -24), ('K', -24, -16),
             ('L', -16, -8), ('M', -8, 0), ('N', 0, 8), ('P', 8, 16),
             ('Q', 16, 24), ('R', 24, 32), ('S', 32, 40), ('T', 40, 48),
             ('U', 48, 56), ('V', 56, 64), ('W', 64, 72), ('X', 72, 84)]
    band = 'Z'
    for b, low, high in bands:
        if low <= lat_deg < high:
            band = b
            break
    return easting, northing, zone, band, f"{zone}{band}"

def utm_to_blh(easting: float, northing: float, zone: int, band: str, ellipsoid: str = 'WGS84', northern_hemisphere: bool = True) -> Tuple[float, float, float]:
    """UTM投影 转 大地坐标BLH (高度返回0)"""
    ell = ELLIPSOIDS[ellipsoid]
    a, f = ell['a'], ell['f']
    e2 = 2 * f - f ** 2
    e2_prime = e2 / (1 - e2)
    k0 = 0.9996
    x = easting - 500000
    y = northing if northern_hemisphere else northing - 10000000
    M = y / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    lat_rad = mu + (3*e1/2 - 27*e1**3/32) * math.sin(2*mu) \
              + (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu) \
              + (151*e1**3/96) * math.sin(6*mu) \
              + (1097*e1**4/512) * math.sin(8*mu)
    sin_lat, cos_lat, tan_lat = math.sin(lat_rad), math.cos(lat_rad), math.tan(lat_rad)
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    T, C = tan_lat**2, e2_prime * cos_lat**2
    D = x / (N * k0)
    lat_rad = lat_rad - (N * tan_lat / (a * (1 - e2))) * (
        D**2/2 - (5 + 3*T + 10*C - 4*C**2 - 9*e2_prime) * D**4/24
        + (61 + 90*T + 298*C + 45*T**2 - 252*e2_prime - 3*C**2) * D**6/720
    )
    lon0_deg = (zone - 1) * 6 - 180 + 3
    lon_rad = math.radians(lon0_deg) + (
        D - (1 + 2*T + C) * D**3/6
        + (5 - 2*C + 28*T - 3*C**2 + 8*e2_prime + 24*T**2) * D**5/120
    ) / cos_lat
    return math.degrees(lat_rad), math.degrees(lon_rad), 0.0

# ==================== RINEX解析器 ====================
class RinexParser:
    """RINEX观测文件和导航文件解析器（支持2.x和3.x）"""
    
    @staticmethod
    def parse_observation_header(lines: List[str]) -> Dict:
        header = {
            'version': '2.11', 'rinex_type': 'O', 'system': 'G',
            'marker_name': '', 'observer': '', 'receiver': '', 'antenna': '',
            'approx_position': [0.0, 0.0, 0.0], 'antenna_delta': [0.0, 0.0, 0.0],
            'observation_types': [], 'num_obs_types': 0,
            'time_of_first_obs': '', 'interval': 0.0, 'num_satellites': 0, 'prn_list': [],
        }
        for line in lines:
            label = line[60:].strip()
            if 'RINEX VERSION' in label:
                header['version'] = line[0:20].strip()
                if float(header['version']) >= 3.0:
                    header['system'] = line[20:21] if len(line) > 20 else 'G'
            elif 'MARKER NAME' in label:
                header['marker_name'] = line[0:60].strip()
            elif 'OBSERVER / AGENCY' in label:
                header['observer'] = line[0:60].strip()
            elif 'REC # / TYPE / VERS' in label:
                header['receiver'] = line[0:60].strip()
            elif 'ANT # / TYPE' in label:
                header['antenna'] = line[0:60].strip()
            elif 'APPROX POSITION XYZ' in label:
                parts = line[0:60].strip().split()
                if len(parts) >= 3:
                    header['approx_position'] = [float(p) for p in parts[:3]]
            elif 'ANTENNA: DELTA H/E/N' in label:
                parts = line[0:60].strip().split()
                if len(parts) >= 3:
                    header['antenna_delta'] = [float(p) for p in parts[:3]]
            elif '# / TYPES OF OBSERV' in label or 'SYS / # / OBS TYPES' in label:
                if float(header['version']) >= 3.0:
                    sys_char = line[0:1]
                    if sys_char == header.get('system', 'G'):
                        ntypes = int(line[3:6]) if len(line) > 5 else 0
                        header['num_obs_types'] = ntypes
                        header['observation_types'].extend(line[7:60].strip().split())
                else:
                    ntypes = int(line[0:6]) if len(line) > 5 else 0
                    header['num_obs_types'] = ntypes
                    header['observation_types'].extend(line[6:60].strip().split())
            elif 'TIME OF FIRST OBS' in label:
                header['time_of_first_obs'] = line[0:60].strip()
            elif 'INTERVAL' in label:
                try:
                    header['interval'] = float(line[0:10])
                except:
                    pass
            elif 'END OF HEADER' in label:
                break
        return header

    @staticmethod
    def parse_observation_data(lines: List[str], header: Dict) -> pd.DataFrame:
        records = []
        version = float(header.get('version', '2.11'))
        nobs = header.get('num_obs_types', 0)
        obs_types = header.get('observation_types', [])
        # 定位数据起始行
        data_start = next((j + 1 for j, line in enumerate(lines) if 'END OF HEADER' in line), 0)
        data_lines = lines[data_start:]
        line_idx = 0
        while line_idx < len(data_lines):
            line = data_lines[line_idx]
            if not line.strip() or len(line) < 30:
                line_idx += 1
                continue
            try:
                if version < 3.0:
                    # 解析历元行
                    yr = int(line[0:3])
                    yr += 1900 if yr >= 80 else 2000
                    month = int(line[3:6])
                    day = int(line[6:9])
                    hour = int(line[9:12])
                    minute = int(line[12:15])
                    second = float(line[15:26])
                    epoch_flag = int(line[28:29]) if len(line) > 28 else 0
                    num_sats = int(line[29:32]) if len(line) > 29 else 0
                    epoch_time = datetime(yr, month, day, hour, minute, int(second),
                                          int((second - int(second)) * 1e6))
                    # 收集卫星ID
                    sat_ids = [line[i:i+3].strip() for i in range(32, len(line), 3) if line[i:i+3].strip()]
                    while len(sat_ids) < num_sats:
                        line_idx += 1
                        if line_idx >= len(data_lines): break
                        extra = data_lines[line_idx]
                        sat_ids += [extra[i:i+3].strip() for i in range(0, len(extra), 3) if extra[i:i+3].strip()]
                    line_idx += 1
                    # 读取每颗卫星的观测值
                    for sat_id in sat_ids[:num_sats]:
                        if line_idx >= len(data_lines): break
                        record = {'epoch': epoch_time, 'satellite': sat_id, 'epoch_flag': epoch_flag}
                        remaining = nobs
                        while remaining > 0 and line_idx < len(data_lines):
                            cur_line = data_lines[line_idx]
                            vals_in_line = min(remaining, 5)
                            for k in range(vals_in_line):
                                start, end = k * 14, k * 14 + 14
                                val_str = cur_line[start:end].strip() if len(cur_line) > start else ''
                                try:
                                    val = float(val_str) if val_str else np.nan
                                except:
                                    val = np.nan
                                record[obs_types[nobs - remaining + k]] = val
                            remaining -= vals_in_line
                            if remaining > 0:
                                line_idx += 1
                        records.append(record)
                        line_idx += 1
                else:
                    # RINEX 3.x 简要实现
                    parts = line[1:].strip().split()
                    if len(parts) >= 6:
                        yr, month, day, hour, minute = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                        second = float(parts[5])
                        epoch_flag = int(parts[6]) if len(parts) > 6 else 0
                        num_sats = int(parts[7]) if len(parts) > 7 else 0
                        epoch_time = datetime(yr, month, day, hour, minute, int(second),
                                              int((second - int(second)) * 1e6))
                        line_idx += 1
                        for _ in range(num_sats):
                            if line_idx >= len(data_lines): break
                            sat_line = data_lines[line_idx]
                            sat_id = sat_line[0:3].strip()
                            record = {'epoch': epoch_time, 'satellite': sat_id, 'epoch_flag': epoch_flag}
                            obs_parts = sat_line[3:].strip().split()
                            for k, obs_type in enumerate(obs_types[:nobs]):
                                record[obs_type] = float(obs_parts[k]) if k < len(obs_parts) else np.nan
                            records.append(record)
                            line_idx += 1
                    else:
                        line_idx += 1
            except Exception:
                line_idx += 1
                continue
        return pd.DataFrame(records)

    @staticmethod
    def parse_navigation_header(lines: List[str]) -> Dict:
        header = {'version': '2.11', 'rinex_type': 'N',
                  'ion_alpha': [0.0]*4, 'ion_beta': [0.0]*4, 'leap_seconds': 0}
        for line in lines:
            label = line[60:].strip()
            if 'RINEX VERSION' in label:
                header['version'] = line[0:20].strip()
            elif 'ION ALPHA' in label:
                parts = line[0:60].strip().split()
                if len(parts) >= 4:
                    header['ion_alpha'] = [float(p.replace('D', 'E')) for p in parts[:4]]
            elif 'ION BETA' in label:
                parts = line[0:60].strip().split()
                if len(parts) >= 4:
                    header['ion_beta'] = [float(p.replace('D', 'E')) for p in parts[:4]]
            elif 'LEAP SECONDS' in label:
                try:
                    header['leap_seconds'] = int(line[0:6])
                except:
                    pass
            elif 'END OF HEADER' in label:
                break
        return header

    @staticmethod
    def parse_navigation_data(lines: List[str], header: Dict) -> pd.DataFrame:
        records = []
        data_start = next((j + 1 for j, line in enumerate(lines) if 'END OF HEADER' in line), 0)
        data_lines = lines[data_start:]
        line_idx = 0
        while line_idx < len(data_lines) - 7:
            try:
                line = data_lines[line_idx]
                if not line.strip():
                    line_idx += 1
                    continue
                prn = line[0:3].strip()
                yr = int(line[3:6])
                yr += 1900 if yr >= 80 else 2000
                month, day, hour, minute = int(line[6:9]), int(line[9:12]), int(line[12:15]), int(line[15:18])
                second = float(line[18:22])
                toc = datetime(yr, month, day, hour, minute, int(second))
                record = {'satellite': prn, 'toc': toc,
                          'af0': float(line[22:41].replace('D', 'E')),
                          'af1': float(line[41:60].replace('D', 'E'))}
                line_idx += 1; l2 = data_lines[line_idx]
                record.update({'af2': float(l2[0:19].replace('D', 'E')),
                               'crs': float(l2[19:38].replace('D', 'E')),
                               'delta_n': float(l2[38:57].replace('D', 'E')),
                               'M0': float(l2[57:76].replace('D', 'E')) if len(l2) > 57 else 0.0})
                line_idx += 1; l3 = data_lines[line_idx]
                record.update({'cuc': float(l3[0:19].replace('D', 'E')),
                               'ecc': float(l3[19:38].replace('D', 'E')),
                               'cus': float(l3[38:57].replace('D', 'E')),
                               'sqrt_a': float(l3[57:76].replace('D', 'E')) if len(l3) > 57 else 0.0})
                line_idx += 1; l4 = data_lines[line_idx]
                record.update({'toe': float(l4[0:19].replace('D', 'E')),
                               'cic': float(l4[19:38].replace('D', 'E')),
                               'OMEGA0': float(l4[38:57].replace('D', 'E')),
                               'cis': float(l4[57:76].replace('D', 'E')) if len(l4) > 57 else 0.0})
                line_idx += 1; l5 = data_lines[line_idx]
                record.update({'i0': float(l5[0:19].replace('D', 'E')),
                               'crc': float(l5[19:38].replace('D', 'E')),
                               'omega': float(l5[38:57].replace('D', 'E')),
                               'OMEGA_DOT': float(l5[57:76].replace('D', 'E')) if len(l5) > 57 else 0.0})
                line_idx += 1; l6 = data_lines[line_idx]
                record['i_dot'] = float(l6[0:19].replace('D', 'E'))
                line_idx += 1; l7 = data_lines[line_idx]
                record['week_num'] = int(float(l7[0:19].replace('D', 'E'))) if l7[0:19].strip() else 0
                records.append(record)
                line_idx += 1
            except:
                line_idx += 1
        return pd.DataFrame(records)

# ==================== 周跳探测算法 ====================
class CycleSlipDetector:
    """周跳探测：GF组合 + MW组合"""
    
    @staticmethod
    def gf_combination(L1, L2, f1=1575.42e6, f2=1227.60e6, threshold=0.05):
        c = 299792458.0
        lambda1, lambda2 = c / f1, c / f2
        gf = L1 * lambda1 - L2 * lambda2
        gf_diff = np.diff(gf, prepend=gf[0])
        slips = np.where(np.abs(gf_diff) > threshold)[0]
        return gf, slips, gf_diff

    @staticmethod
    def mw_combination(L1, L2, P1, P2, f1=1575.42e6, f2=1227.60e6, threshold=2.0):
        c = 299792458.0
        lambda1, lambda2 = c / f1, c / f2
        lambda_w = c / (f1 - f2)
        L1_m, L2_m = L1 * lambda1, L2 * lambda2
        mw = (f1 * L1_m - f2 * L2_m) / (f1 - f2) / lambda_w - (f1 * P1 + f2 * P2) / (f1 + f2) / lambda_w
        window_size = min(10, len(mw))
        slips = []
        if len(mw) > window_size:
            for i in range(window_size, len(mw)):
                window = mw[i-window_size:i]
                mean_val = np.nanmean(window)
                std_val = np.nanstd(window)
                if std_val > 0 and abs(mw[i] - mean_val) > threshold * std_val:
                    slips.append(i)
        return mw, np.array(slips)

    @staticmethod
    def detect_all(df: pd.DataFrame, f1=1575.42e6, f2=1227.60e6) -> Dict:
        results = {'slips': [], 'gf_values': None, 'mw_values': None, 'summary': ''}
        l1_cols = [c for c in df.columns if 'L1' in c.upper() or 'C1' in c.upper()]
        l2_cols = [c for c in df.columns if 'L2' in c.upper() or 'C2' in c.upper()]
        p1_cols = [c for c in df.columns if 'P1' in c.upper() or 'C1' in c.upper()]
        p2_cols = [c for c in df.columns if 'P2' in c.upper()]
        if not l1_cols or not l2_cols:
            return results
        l1_col, l2_col = l1_cols[0], l2_cols[0]
        all_slips = []
        for sat in df['satellite'].unique():
            sat_data = df[df['satellite'] == sat].sort_values('epoch').reset_index(drop=True)
            l1_vals, l2_vals = sat_data[l1_col].values, sat_data[l2_col].values
            valid = ~(np.isnan(l1_vals) | np.isnan(l2_vals))
            if np.sum(valid) < 5: continue
            l1_clean, l2_clean = l1_vals[valid], l2_vals[valid]
            valid_idx = np.where(valid)[0]
            gf, gf_slips, _ = CycleSlipDetector.gf_combination(l1_clean, l2_clean, f1, f2)
            for slip_idx in gf_slips:
                if slip_idx < len(valid_idx):
                    orig = valid_idx[slip_idx]
                    all_slips.append({
                        'satellite': sat,
                        'epoch': sat_data.iloc[orig]['epoch'],
                        'index': orig,
                        'method': 'GF组合',
                        'gf_value': gf[slip_idx] if slip_idx < len(gf) else 0.0,
                    })
            if p1_cols and p2_cols:
                p1_vals = sat_data[p1_cols[0]].values[valid]
                p2_vals = sat_data[p2_cols[0]].values[valid]
                if len(p1_vals) == len(l1_clean):
                    mw, mw_slips = CycleSlipDetector.mw_combination(l1_clean, l2_clean, p1_vals, p2_vals, f1, f2)
                    for slip_idx in mw_slips:
                        if slip_idx < len(valid_idx):
                            orig = valid_idx[slip_idx]
                            all_slips.append({
                                'satellite': sat,
                                'epoch': sat_data.iloc[orig]['epoch'],
                                'index': orig,
                                'method': 'MW组合',
                                'mw_value': mw[slip_idx] if slip_idx < len(mw) else 0.0,
                            })
        results['slips'] = all_slips
        results['summary'] = f"检测到 {len(all_slips)} 处疑似周跳，涉及 {len(set(s['satellite'] for s in all_slips))} 颗卫星"
        return results

# ==================== 模拟数据生成 ====================
def generate_simulated_obs_data(num_epochs=100, num_sats=8, slip_epochs=None):
    if slip_epochs is None:
        slip_epochs = [25, 55, 78]
    np.random.seed(42)
    epochs = [datetime(2024, 6, 21, 10, 0, 0) + timedelta(seconds=30 * i) for i in range(num_epochs)]
    records = []
    for i, epoch in enumerate(epochs):
        for sat_idx in range(num_sats):
            sat_id = f"G{sat_idx+1:02d}"
            base_l1 = 1e7 + sat_idx * 1e5 + i * 5000
            base_l2 = 8e6 + sat_idx * 8e4 + i * 3900
            l1 = base_l1 + np.random.normal(0, 0.01)
            l2 = base_l2 + np.random.normal(0, 0.012)
            if i in slip_epochs and sat_idx in [1, 3, 5]:
                l1 += np.random.choice([-15, 12, -8, 20]) * np.random.choice([1, 2, 3])
                l2 += np.random.choice([-10, 8, -6, 15])
            p1 = 2.1e7 + sat_idx * 2e5 + i * 5000 + np.random.normal(0, 0.5)
            p2 = 2.1e7 + sat_idx * 2e5 + i * 5000 + np.random.normal(0, 0.6)
            records.append({'epoch': epoch, 'satellite': sat_id, 'L1': l1, 'L2': l2, 'P1': p1, 'P2': p2, 'epoch_flag': 0})
    return pd.DataFrame(records), slip_epochs

# ==================== 卫星位置计算（简化） ====================
def compute_satellite_position(nav_record: Dict, time_gps: datetime) -> Optional[np.ndarray]:
    try:
        mu = 3.986005e14
        omega_e = 7.2921151467e-5
        toc = nav_record.get('toc')
        if toc is None: return None
        dt = (time_gps - toc).total_seconds()
        sqrt_a = nav_record.get('sqrt_a', 5153.5)
        a = sqrt_a ** 2
        delta_n = nav_record.get('delta_n', 0.0)
        n = math.sqrt(mu / a**3) + delta_n
        M0 = nav_record.get('M0', 0.0)
        M = M0 + n * dt
        ecc = nav_record.get('ecc', 0.01)
        E = M
        for _ in range(10):
            E_new = M + ecc * math.sin(E)
            if abs(E_new - E) < 1e-12: break
            E = E_new
        v = math.atan2(math.sqrt(1 - ecc**2) * math.sin(E), math.cos(E) - ecc)
        omega = nav_record.get('omega', 0.0)
        phi = v + omega
        cus, cuc = nav_record.get('cus', 0.0), nav_record.get('cuc', 0.0)
        crs, crc = nav_record.get('crs', 0.0), nav_record.get('crc', 0.0)
        cis, cic = nav_record.get('cis', 0.0), nav_record.get('cic', 0.0)
        delta_u = cus * math.sin(2*phi) + cuc * math.cos(2*phi)
        delta_r = crs * math.sin(2*phi) + crc * math.cos(2*phi)
        delta_i = cis * math.sin(2*phi) + cic * math.cos(2*phi)
        u = phi + delta_u
        r = a * (1 - ecc * math.cos(E)) + delta_r
        i0 = nav_record.get('i0', 0.96)
        i_dot = nav_record.get('i_dot', 0.0)
        i = i0 + delta_i + i_dot * dt
        x_orb = r * math.cos(u)
        y_orb = r * math.sin(u)
        OMEGA0 = nav_record.get('OMEGA0', 0.0)
        OMEGA_DOT = nav_record.get('OMEGA_DOT', 0.0)
        OMEGA = OMEGA0 + (OMEGA_DOT - omega_e) * dt - omega_e * (toc - datetime(1980, 1, 6)).total_seconds()
        X = x_orb * math.cos(OMEGA) - y_orb * math.cos(i) * math.sin(OMEGA)
        Y = x_orb * math.sin(OMEGA) + y_orb * math.cos(i) * math.cos(OMEGA)
        Z = y_orb * math.sin(i)
        return np.array([X, Y, Z])
    except Exception:
        return None

# ==================== NMEA解析 ====================
def parse_nmea_sentence(sentence: str) -> Dict:
    result = {'type': 'unknown', 'valid': False}
    if not sentence.startswith('$'): return result
    if '*' in sentence:
        sentence, _ = sentence.split('*', 1)
    parts = sentence.split(',')
    talker = parts[0][1:]
    if talker in ['GPGGA', 'GNGGA']:
        result['type'] = 'GGA'
        try:
            lat_deg = float(parts[2][:2]) if parts[2] else 0
            lat_min = float(parts[2][2:]) if len(parts[2]) > 2 else 0
            lat = lat_deg + lat_min / 60
            if parts[3] == 'S': lat = -lat
            lon_deg = float(parts[4][:3]) if parts[4] else 0
            lon_min = float(parts[4][3:]) if len(parts[4]) > 3 else 0
            lon = lon_deg + lon_min / 60
            if parts[5] == 'W': lon = -lon
            result.update({'latitude': lat, 'longitude': lon, 'quality': int(parts[6]) if parts[6] else 0,
                           'num_sats': int(parts[7]) if parts[7] else 0,
                           'hdop': float(parts[8]) if parts[8] else 0.0,
                           'altitude': float(parts[9]) if parts[9] else 0.0, 'valid': True})
        except: pass
    elif talker in ['GPRMC', 'GNRMC']:
        result['type'] = 'RMC'
        try:
            lat_deg = float(parts[3][:2]) if parts[3] else 0
            lat_min = float(parts[3][2:]) if len(parts[3]) > 2 else 0
            lat = lat_deg + lat_min / 60
            if parts[4] == 'S': lat = -lat
            lon_deg = float(parts[5][:3]) if parts[5] else 0
            lon_min = float(parts[5][3:]) if len(parts[5]) > 3 else 0
            lon = lon_deg + lon_min / 60
            if parts[6] == 'W': lon = -lon
            result.update({'latitude': lat, 'longitude': lon,
                           'speed': float(parts[7]) if parts[7] else 0.0,
                           'valid': parts[2] == 'A'})
        except: pass
    return result

# ==================== 可视化图形生成 ====================
def generate_skyplot(sat_azimuths, sat_elevations, sat_labels=None):
    """生成极坐标卫星星空图"""
    if sat_labels is None:
        sat_labels = [f'SAT{i+1}' for i in range(len(sat_azimuths))]
    fig = go.Figure()
    # 同心圆（仰角线）
    for el in [0, 30, 60]:
        r = 90 - el
        theta_circle = np.linspace(0, 360, 200)
        fig.add_trace(go.Scatterpolar(
            r=[r] * 200, theta=theta_circle,
            mode='lines', line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='none'
        ))
    # 卫星标记点
    colors = ['#63b3ed', '#48bb78', '#f6e05e', '#fc8181', '#b794f4', '#f687b3',
              '#68d391', '#fbd38d', '#63b3ed', '#48bb78']
    for i, (az, el, label) in enumerate(zip(sat_azimuths, sat_elevations, sat_labels)):
        r = 90 - el
        theta = (90 - az) % 360
        fig.add_trace(go.Scatterpolar(
            r=[r], theta=[theta],
            mode='markers+text',
            marker=dict(size=14, color=colors[i % len(colors)], symbol='circle',
                       line=dict(color='white', width=1.5)),
            text=label, textposition='top center', textfont=dict(size=9, color='white'),
            name=label, hovertemplate=f'<b>{label}</b><br>方位角: {az:.1f}°<br>仰角: {el:.1f}°'
        ))
    # 方向标识
    for direction, angle in [('N', 0), ('E', 90), ('S', 180), ('W', 270)]:
        fig.add_trace(go.Scatterpolar(
            r=[95], theta=[angle], mode='text', text=[direction],
            textfont=dict(size=14, color='white'), showlegend=False, hoverinfo='none'
        ))
    fig.update_polar(
        radialaxis=dict(range=[0, 95], showticklabels=False, showgrid=False, zeroline=False),
        angularaxis=dict(
            tickmode='array',
            tickvals=[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
            ticktext=['0°', '30°', '60°', '90°', '120°', '150°', '180°', '210°', '240°', '270°', '300°', '330°'],
            tickfont=dict(size=9, color='#94a3b8'), gridcolor='rgba(255,255,255,0.1)',
            rotation=0, direction='clockwise'
        )
    )
    fig.update_layout(
        title=dict(text='🛰️ GNSS卫星星空图', font=dict(size=16, color='#e2e8f0'), x=0.5),
        height=500, margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        polar_bgcolor='rgba(0,0,0,0)',   # 修复点：通过layout设置极坐标背景
        showlegend=True,
        legend=dict(font=dict(size=10, color='#94a3b8'),
                    bgcolor='rgba(15,23,42,0.8)', bordercolor='rgba(255,255,255,0.1)')
    )
    return fig

def generate_3d_orbit_plot(sat_positions_list, sat_names, earth_radius=6371000):
    """3D卫星轨道可视化"""
    fig = go.Figure()
    # 地球曲面
    u = np.linspace(0, 2 * np.pi, 60)
    v = np.linspace(0, np.pi, 40)
    x_earth = earth_radius * np.outer(np.cos(u), np.sin(v))
    y_earth = earth_radius * np.outer(np.sin(u), np.sin(v))
    z_earth = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
    fig.add_trace(go.Surface(
        x=x_earth, y=y_earth, z=z_earth,
        colorscale=[[0, '#1a3a5c'], [0.5, '#2980b9'], [1, '#0d2137']],
        showscale=False, opacity=0.85, name='地球', hoverinfo='none',
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.3, roughness=0.5)
    ))
    colors = ['#63b3ed', '#48bb78', '#f6e05e', '#fc8181', '#b794f4', '#f687b3']
    for i, (positions, name) in enumerate(zip(sat_positions_list, sat_names)):
        if positions is None or len(positions) < 2: continue
        pos = np.array(positions)
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter3d(
            x=pos[:, 0], y=pos[:, 1], z=pos[:, 2],
            mode='lines+markers', line=dict(color=color, width=2.5),
            marker=dict(size=3, color=color), name=name,
            hovertemplate=f'<b>{name}</b><br>X: %{{x:.0f}}<br>Y: %{{y:.0f}}<br>Z: %{{z:.0f}}'
        ))
    max_range = earth_radius * 1.8
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-max_range, max_range], title='X (m)', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(range=[-max_range, max_range], title='Y (m)', gridcolor='rgba(255,255,255,0.1)'),
            zaxis=dict(range=[-max_range, max_range], title='Z (m)', gridcolor='rgba(255,255,255,0.1)'),
            aspectmode='cube', bgcolor='rgba(0,0,0,0)',
        ),
        title=dict(text='🌍 GNSS卫星3D轨道可视化', font=dict(size=16, color='#e2e8f0'), x=0.5),
        height=600, margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(size=10, color='#94a3b8'), bgcolor='rgba(15,23,42,0.8)')
    )
    return fig

# ==================== 主界面组件 ====================
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:16px 0;">
            <span style="font-size:1.6em;">🛰️</span>
            <h3 style="color:#63b3ed; margin:4px 0; font-weight:600;">SkyTracker Pro</h3>
            <p style="color:#64748b; font-size:0.8em;">GNSS数据处理平台 v2.0</p>
        </div>
        <hr style="border-color:rgba(255,255,255,0.1);">
        """, unsafe_allow_html=True)
        menu = {
            'home': '🏠 首页总览', 'data_reader': '📡 数据读取', 'slip_detector': '🔍 周跳探测',
            'coord_converter': '🗺️ 坐标转换', 'skyplot': '🌌 卫星星空图', 'orbit_viewer': '🛰️ 3D轨道可视化'
        }
        for key, label in menu.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.current_page = key
                st.rerun()
        st.markdown('<hr style="border-color:rgba(255,255,255,0.1);">', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:0.8em; color:#64748b; padding:8px;">
            <p><span class="status-dot green"></span> 系统就绪</p>
            <p>📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>🛰️ GNSS星座: GPS+GLONASS+Galileo+北斗</p>
        </div>
        """, unsafe_allow_html=True)

def render_home_page():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<h1 class="glow-title">SkyTracker Pro</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-glow">专业GNSS卫星导航数据处理平台</p>', unsafe_allow_html=True)
        st.markdown("""
        <p style="color:#94a3b8; line-height:1.8;">
        支持 <b style="color:#63b3ed;">RINEX 2.x/3.x</b> 观测文件与导航文件解析，
        集成 <b style="color:#48bb78;">GF组合</b> 与 <b style="color:#48bb78;">MW组合</b> 周跳探测算法，
        提供 <b style="color:#f6e05e;">BLH↔XYZ↔UTM</b> 全链路坐标转换，
        以及卫星星空图与3D轨道可视化等趣味功能。
        </p>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:12px; padding:16px; text-align:center;">
            <p style="font-size:3em; margin:0;">🛰️</p>
            <p style="color:#63b3ed; font-weight:600;">多系统支持</p>
            <p style="color:#94a3b8; font-size:0.85em;">GPS | GLONASS | Galileo | 北斗</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ('📡', 'RINEX解析', '2.x / 3.x', '#63b3ed'),
        ('🔍', '周跳探测', 'GF + MW组合', '#48bb78'),
        ('🗺️', '坐标转换', 'BLH/XYZ/UTM', '#f6e05e'),
        ('🌌', '可视化', '星空图+3D轨道', '#fc8181'),
    ]
    for col, (icon, title, desc, color) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:2em;">{icon}</div>
                <div class="metric-value" style="font-size:1.1em; color:{color};">{title}</div>
                <div class="metric-label">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color:#e2e8f0;">⚡ 快速入口</h3>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📡 开始读取数据", use_container_width=True): st.session_state.current_page = 'data_reader'; st.rerun()
    with col2:
        if st.button("🔍 周跳探测演示", use_container_width=True): st.session_state.current_page = 'slip_detector'; st.rerun()
    with col3:
        if st.button("🗺️ 坐标转换工具", use_container_width=True): st.session_state.current_page = 'coord_converter'; st.rerun()

def render_data_reader_page():
    st.markdown('<div class="main-card"><h2 style="color:#63b3ed;">📡 数据读取模块</h2><p style="color:#94a3b8;">支持RINEX观测文件、导航文件、NMEA-0183及CSV格式</p></div>', unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📂 文件上传", "📊 数据预览", "ℹ️ 文件信息"])
    with tab1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            obs_file = st.file_uploader("上传RINEX观测文件", type=['obs', 'rnx', 'o', 'txt', 'dat'], key='obs_uploader')
            if obs_file:
                st.markdown('<div class="toast">✅ 观测文件已加载</div>', unsafe_allow_html=True)
        with col2:
            nav_file = st.file_uploader("上传RINEX导航文件", type=['nav', 'n', 'sp3', 'txt', 'dat'], key='nav_uploader')
            if nav_file:
                st.markdown('<div class="toast">✅ 导航文件已加载</div>', unsafe_allow_html=True)
        aux_file = st.file_uploader("上传NMEA日志或CSV数据（可选）", type=['nmea', 'log', 'csv', 'txt'], key='aux_uploader')
        st.markdown('</div>', unsafe_allow_html=True)
        if obs_file:
            content = obs_file.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            header = RinexParser.parse_observation_header(lines)
            df = RinexParser.parse_observation_data(lines, header)
            st.session_state.rinex_data = {'header': header, 'dataframe': df, 'filename': obs_file.name}
            st.markdown(f"""
            <div class="main-card"><h4 style="color:#48bb78;">✅ 解析成功</h4>
            <p>文件: <b>{obs_file.name}</b> | 版本: RINEX {header['version']} | 观测类型数: {header['num_obs_types']} | 数据行数: {len(df)}</p></div>
            """, unsafe_allow_html=True)
        if nav_file:
            content = nav_file.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            nav_header = RinexParser.parse_navigation_header(lines)
            nav_df = RinexParser.parse_navigation_data(lines, nav_header)
            st.session_state.nav_data = {'header': nav_header, 'dataframe': nav_df, 'filename': nav_file.name}
            st.markdown(f"""
            <div class="main-card"><h4 style="color:#48bb78;">✅ 导航文件解析成功</h4>
            <p>文件: <b>{nav_file.name}</b> | 卫星数: {len(nav_df['satellite'].unique()) if not nav_df.empty else 0} | 星历记录: {len(nav_df)}</p></div>
            """, unsafe_allow_html=True)
        if aux_file:
            content = aux_file.read().decode('utf-8', errors='replace')
            if aux_file.name.endswith('.csv'):
                try:
                    st.session_state.aux_data = pd.read_csv(io.StringIO(content))
                    st.markdown(f'<div class="toast">✅ CSV数据已加载 ({len(st.session_state.aux_data)} 行)</div>', unsafe_allow_html=True)
                except:
                    st.warning("CSV解析失败")
            else:
                nmea_results = [parse_nmea_sentence(line.strip()) for line in content.split('\n') if line.strip().startswith('$')]
                valid_results = [r for r in nmea_results if r['valid']]
                if valid_results:
                    st.session_state.nmea_data = valid_results
                    st.markdown(f'<div class="toast">✅ NMEA数据已解析 ({len(valid_results)} 条有效定位)</div>', unsafe_allow_html=True)
    with tab2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        if st.session_state.rinex_data:
            df = st.session_state.rinex_data['dataframe']
            st.markdown(f'<p style="color:#94a3b8;">共 {len(df)} 条观测记录</p>', unsafe_allow_html=True)
            display_df = df.head(50).copy()
            for col in display_df.select_dtypes(include=[np.float64, float]).columns:
                display_df[col] = display_df[col].round(4)
            st.dataframe(display_df, use_container_width=True, height=400)
            if len(df) > 50:
                st.info(f"仅显示前50行，共{len(df)}行数据")
        else:
            st.info("📂 请先在「文件上传」标签页中上传RINEX观测文件")
        st.markdown('</div>', unsafe_allow_html=True)
    with tab3:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        if st.session_state.rinex_data:
            header = st.session_state.rinex_data['header']
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <h4 style="color:#63b3ed;">📋 文件头信息</h4>
                <table class="data-table">
                    <tr><td>RINEX版本</td><td><b>{header['version']}</b></td></tr>
                    <tr><td>观测类型数</td><td><b>{header['num_obs_types']}</b></td></tr>
                    <tr><td>测站名称</td><td><b>{header['marker_name'] or 'N/A'}</b></td></tr>
                    <tr><td>观测者</td><td><b>{header['observer'] or 'N/A'}</b></td></tr>
                    <tr><td>接收机</td><td><b>{header['receiver'] or 'N/A'}</b></td></tr>
                    <tr><td>天线</td><td><b>{header['antenna'] or 'N/A'}</b></td></tr>
                </table>
                """, unsafe_allow_html=True)
            with col2:
                approx_pos = header.get('approx_position', [0, 0, 0])
                st.markdown(f"""
                <h4 style="color:#63b3ed;">📍 近似坐标</h4>
                <table class="data-table">
                    <tr><td>X</td><td><b>{approx_pos[0]:.3f} m</b></td></tr>
                    <tr><td>Y</td><td><b>{approx_pos[1]:.3f} m</b></td></tr>
                    <tr><td>Z</td><td><b>{approx_pos[2]:.3f} m</b></td></tr>
                    <tr><td>采样间隔</td><td><b>{header.get('interval', 'N/A')} 秒</b></td></tr>
                    <tr><td>首次观测</td><td><b>{header.get('time_of_first_obs', 'N/A')}</b></td></tr>
                </table>
                """, unsafe_allow_html=True)
            obs_types = header.get('observation_types', [])
            if obs_types:
                st.markdown(f"<h4 style='color:#63b3ed;'>📊 观测类型</h4><p style='color:#cbd5e1;'>{' | '.join([f'<code style=\"background:rgba(99,179,237,0.15);padding:2px 8px;border-radius:4px;\">{t}</code>' for t in obs_types])}</p>", unsafe_allow_html=True)
        else:
            st.info("📂 请先上传RINEX文件")
        st.markdown('</div>', unsafe_allow_html=True)

def render_slip_detector_page():
    st.markdown('<div class="main-card"><h2 style="color:#48bb78;">🔍 周跳探测模块</h2><p style="color:#94a3b8;">GF组合 + MW组合双算法联合探测</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">⚙️ 探测参数设置</h4>', unsafe_allow_html=True)
        use_demo = st.checkbox("使用演示数据（模拟含周跳的观测数据）", value=True, key='use_demo_slip')
        if not use_demo:
            st.info("请先在「数据读取」模块上传RINEX观测文件")
        col_a, col_b = st.columns(2)
        with col_a:
            gf_threshold = st.number_input("GF阈值 (米)", value=0.05, step=0.01, format="%.3f")
        with col_b:
            mw_threshold = st.number_input("MW阈值 (标准差倍数)", value=2.0, step=0.5)
        detect_btn = st.button("🔍 开始探测", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📊 探测结果统计</h4>', unsafe_allow_html=True)
        if detect_btn or st.session_state.detected_slips is not None:
            if use_demo:
                slip_epochs_injected = [25, 55, 78]
                demo_df, _ = generate_simulated_obs_data(120, 8, slip_epochs_injected)
                results = CycleSlipDetector.detect_all(demo_df)
                st.session_state.detected_slips = results
                st.session_state.demo_df = demo_df
                st.session_state.injected_slips = slip_epochs_injected
            elif st.session_state.rinex_data:
                results = CycleSlipDetector.detect_all(st.session_state.rinex_data['dataframe'])
                st.session_state.detected_slips = results
                st.session_state.demo_df = st.session_state.rinex_data['dataframe']
        if st.session_state.detected_slips:
            slips = st.session_state.detected_slips.get('slips', [])
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#fc8181;">{len(slips)}</div><div class="metric-label">疑似周跳总数</div></div>', unsafe_allow_html=True)
            with col_s2:
                unique = len(set(s['satellite'] for s in slips)) if slips else 0
                st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#f6e05e;">{unique}</div><div class="metric-label">受影响卫星数</div></div>', unsafe_allow_html=True)
            with col_s3:
                gf_cnt = len([s for s in slips if 'GF' in s.get('method','')])
                mw_cnt = len([s for s in slips if 'MW' in s.get('method','')])
                st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#63b3ed;">{gf_cnt}+{mw_cnt}</div><div class="metric-label">GF+MW检出</div></div>', unsafe_allow_html=True)
            if slips:
                st.dataframe(pd.DataFrame(slips), use_container_width=True, height=200)
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.detected_slips and 'demo_df' in st.session_state:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📈 GF组合时序图（含周跳标记）</h4>', unsafe_allow_html=True)
        demo_df = st.session_state.demo_df
        sats = sorted(demo_df['satellite'].unique())
        selected = st.multiselect("选择卫星查看", sats, default=sats[:4])
        if selected:
            fig = make_subplots(rows=len(selected), cols=1, shared_xaxes=True,
                                subplot_titles=[f"卫星 {s}" for s in selected])
            for idx, sat in enumerate(selected):
                sat_data = demo_df[demo_df['satellite'] == sat].sort_values('epoch')
                if 'L1' in sat_data.columns and 'L2' in sat_data.columns:
                    c = 299792458.0; f1, f2 = 1575.42e6, 1227.60e6
                    lambda1, lambda2 = c/f1, c/f2
                    gf_vals = sat_data['L1'].values * lambda1 - sat_data['L2'].values * lambda2
                    row = idx + 1
                    fig.add_trace(go.Scatter(y=gf_vals, mode='lines', name=f'{sat} GF',
                                            line=dict(color='#63b3ed', width=1.5)), row=row, col=1)
                    slips = [s for s in st.session_state.detected_slips.get('slips', []) if s['satellite'] == sat]
                    if slips:
                        slip_idx = [s['index'] for s in slips if s['index'] < len(gf_vals)]
                        slip_vals = [gf_vals[i] for i in slip_idx]
                        fig.add_trace(go.Scatter(x=slip_idx, y=slip_vals, mode='markers',
                                                 marker=dict(color='#fc8181', size=10, symbol='x'),
                                                 name=f'{sat} 周跳'), row=row, col=1)
            fig.update_layout(height=200*len(selected), showlegend=True,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color='#94a3b8'), legend=dict(font=dict(size=9, color='#94a3b8')))
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.08)')
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.08)')
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def render_coord_converter_page():
    st.markdown('<div class="main-card"><h2 style="color:#f6e05e;">🗺️ 坐标转换模块</h2><p style="color:#94a3b8;">支持BLH ↔ XYZ ↔ UTM全链路转换，多椭球参数</p></div>', unsafe_allow_html=True)
    conv_direction = st.radio("选择转换方向",
                              ["BLH → XYZ (大地坐标转地心地固)", "XYZ → BLH (地心地固转大地坐标)",
                               "BLH → UTM (大地坐标转UTM投影)", "UTM → BLH (UTM投影转大地坐标)"],
                              horizontal=True)
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    presets = {
        '自定义': None, '北京 (天安门)': (39.9087, 116.3975, 50), '上海 (外滩)': (31.2304, 121.4737, 10),
        '广州 (珠江新城)': (23.1291, 113.2644, 20), '成都 (天府广场)': (30.6598, 104.0633, 500),
        '拉萨 (布达拉宫)': (29.6573, 91.1172, 3650), '纽约 (时代广场)': (40.7580, -73.9855, 10),
        '伦敦 (大本钟)': (51.5007, -0.1246, 5),
    }
    with col1:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📝 输入参数</h4>', unsafe_allow_html=True)
        ellipsoid = st.selectbox("选择椭球参数", list(ELLIPSOIDS.keys()), index=0, format_func=lambda x: ELLIPSOIDS[x]['name'])
        preset_choice = st.selectbox("或选择预设坐标", list(presets.keys()))
        if 'BLH →' in conv_direction:
            if preset_choice != '自定义' and presets[preset_choice]:
                lat, lon, h = presets[preset_choice]
            else:
                lat = st.number_input("纬度 (°)", value=39.9087, format="%.6f")
                lon = st.number_input("经度 (°)", value=116.3975, format="%.6f")
                h = st.number_input("大地高 (m)", value=50.0, format="%.3f")
            if 'UTM' not in conv_direction:
                if st.button("🔄 转换 BLH → XYZ", use_container_width=True):
                    X, Y, Z = blh_to_xyz(lat, lon, h, ellipsoid)
                    st.session_state.conv_result = {'type': 'xyz', 'X': X, 'Y': Y, 'Z': Z, 'input': (lat, lon, h, ellipsoid)}
            else:
                if st.button("🔄 转换 BLH → UTM", use_container_width=True):
                    easting, northing, zone, band, zone_band = blh_to_utm(lat, lon, ellipsoid)
                    st.session_state.conv_result = {'type': 'utm', 'easting': easting, 'northing': northing,
                                                    'zone': zone, 'band': band, 'zone_band': zone_band,
                                                    'input': (lat, lon, h, ellipsoid)}
        elif 'XYZ →' in conv_direction:
            if preset_choice != '自定义' and presets[preset_choice]:
                lat, lon, h = presets[preset_choice]
                X_p, Y_p, Z_p = blh_to_xyz(lat, lon, h, ellipsoid)
                st.info(f"预设坐标转换得到的XYZ: X={X_p:.3f}, Y={Y_p:.3f}, Z={Z_p:.3f}")
            X = st.number_input("X (m)", value=-2176842.0, format="%.3f")
            Y = st.number_input("Y (m)", value=4389234.0, format="%.3f")
            Z = st.number_input("Z (m)", value=4070692.0, format="%.3f")
            if st.button("🔄 转换 XYZ → BLH", use_container_width=True):
                lat, lon, h = xyz_to_blh(X, Y, Z, ellipsoid)
                st.session_state.conv_result = {'type': 'blh', 'lat': lat, 'lon': lon, 'height': h, 'input': (X, Y, Z, ellipsoid)}
        elif 'UTM →' in conv_direction:
            easting = st.number_input("东向 (m)", value=450000.0, format="%.3f")
            northing = st.number_input("北向 (m)", value=4420000.0, format="%.3f")
            zone = st.number_input("UTM带号", value=50, min_value=1, max_value=60)
            band = st.selectbox("纬度带", list('CDEFGHJKLMNPQRSTUVWX'), index=10)
            northern = st.checkbox("北半球", value=True)
            if st.button("🔄 转换 UTM → BLH", use_container_width=True):
                lat, lon, h = utm_to_blh(easting, northing, zone, band, ellipsoid, northern)
                st.session_state.conv_result = {'type': 'blh_from_utm', 'lat': lat, 'lon': lon, 'height': h, 'input': (easting, northing, zone, band, ellipsoid)}
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="main-card"><h4 style="color:#48bb78;">✅ 转换结果</h4>', unsafe_allow_html=True)
        if st.session_state.conv_result:
            result = st.session_state.conv_result
            if result['type'] == 'xyz':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">ECEF坐标 (XYZ)</h5>
                    <table class="data-table">
                        <tr><td>X</td><td><b>{result['X']:.4f} m</b></td></tr>
                        <tr><td>Y</td><td><b>{result['Y']:.4f} m</b></td></tr>
                        <tr><td>Z</td><td><b>{result['Z']:.4f} m</b></td></tr>
                    </table>
                    <p style="color:#64748b; font-size:0.8em; margin-top:12px;">椭球: {ELLIPSOIDS[result['input'][3]]['name']} | 输入: ({result['input'][0]:.6f}°, {result['input'][1]:.6f}°, {result['input'][2]:.3f}m)</p>
                </div>""", unsafe_allow_html=True)
            elif result['type'] == 'blh':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">大地坐标 (BLH)</h5>
                    <table class="data-table">
                        <tr><td>纬度 (B)</td><td><b>{result['lat']:.8f}°</b></td></tr>
                        <tr><td>经度 (L)</td><td><b>{result['lon']:.8f}°</b></td></tr>
                        <tr><td>大地高 (H)</td><td><b>{result['height']:.4f} m</b></td></tr>
                    </table>
                </div>""", unsafe_allow_html=True)
            elif result['type'] == 'utm':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">UTM投影坐标</h5>
                    <table class="data-table">
                        <tr><td>东向 (Easting)</td><td><b>{result['easting']:.3f} m</b></td></tr>
                        <tr><td>北向 (Northing)</td><td><b>{result['northing']:.3f} m</b></td></tr>
                        <tr><td>带号</td><td><b>{result['zone_band']}</b> (Zone {result['zone']}{result['band']})</td></tr>
                    </table>
                </div>""", unsafe_allow_html=True)
            elif result['type'] == 'blh_from_utm':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">大地坐标 (从UTM反算)</h5>
                    <table class="data-table">
                        <tr><td>纬度 (B)</td><td><b>{result['lat']:.8f}°</b></td></tr>
                        <tr><td>经度 (L)</td><td><b>{result['lon']:.8f}°</b></td></tr>
                    </table>
                    <p style="color:#64748b; font-size:0.8em; margin-top:12px;">注：UTM不含高程信息</p>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("👈 输入参数并点击转换按钮查看结果")
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.conv_result:
        result = st.session_state.conv_result
        if result['type'] in ['blh', 'blh_from_utm']:
            lat, lon = result['lat'], result['lon']
        elif result['type'] == 'xyz':
            lat, lon, _ = xyz_to_blh(result['X'], result['Y'], result['Z'], result['input'][3])
        elif result['type'] == 'utm':
            lat, lon, _ = utm_to_blh(result['easting'], result['northing'], result['zone'], result['band'], result['input'][3])
        else:
            lat, lon = 39.9, 116.4
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">🗺️ 位置地图</h4>', unsafe_allow_html=True)
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=10)
        st.markdown('</div>', unsafe_allow_html=True)

def render_skyplot_page():
    st.markdown('<div class="main-card"><h2 style="color:#b794f4;">🌌 GNSS卫星星空图</h2><p style="color:#94a3b8;">模拟当前可见卫星在天球上的分布（趣味可视化插件）</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col2:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">🎮 参数设置</h4>', unsafe_allow_html=True)
        num_sats = st.slider("可见卫星数量", 4, 32, 16)
        seed = st.number_input("随机种子", value=42)
        regen_btn = st.button("🎲 重新生成星空图", use_container_width=True)
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:8px; padding:12px; margin-top:12px;">
            <p style="color:#94a3b8; font-size:0.85em;">
            <b>💡 说明：</b>星空图以极坐标展示卫星分布<br>
            • 中心 = 天顶 (90°仰角)<br>
            • 边缘 = 地平线 (0°仰角)<br>
            • 角度 = 方位角 (N=0°, E=90°)
            </p>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        np.random.seed(seed if not regen_btn else int(time.time()))
        azimuths = np.random.uniform(0, 360, num_sats)
        elevations = np.random.beta(1.5, 2, num_sats) * 90
        constellations = (['G'] * (num_sats//4) + ['R'] * (num_sats//4) +
                          ['E'] * (num_sats//4) + ['C'] * (num_sats//4))[:num_sats]
        np.random.shuffle(constellations)
        sat_labels = [f"{constellations[i]}{i+1:02d}" for i in range(num_sats)]
        fig = generate_skyplot(azimuths, elevations, sat_labels)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📋 卫星方位列表</h4>', unsafe_allow_html=True)
    constellation_names = {'G': 'GPS', 'R': 'GLONASS', 'E': 'Galileo', 'C': '北斗'}
    sat_data = []
    for i in range(num_sats):
        const = sat_labels[i][0] if i < len(sat_labels) else 'G'
        el = elevations[i]
        status = '🟢 跟踪中' if el > 15 else ('🟡 低仰角' if el > 5 else '🔴 即将消失')
        sat_data.append({'卫星编号': sat_labels[i], '星座': constellation_names.get(const, '未知'),
                         '方位角 (°)': round(azimuths[i], 2), '仰角 (°)': round(el, 2), '信号状态': status})
    st.dataframe(pd.DataFrame(sat_data), use_container_width=True, height=350)
    st.markdown('</div>', unsafe_allow_html=True)

def render_orbit_viewer_page():
    st.markdown('<div class="main-card"><h2 style="color:#f687b3;">🛰️ 3D卫星轨道可视化</h2><p style="color:#94a3b8;">交互式3D展示GNSS卫星绕地球运行轨迹</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">🎮 轨道参数</h4>', unsafe_allow_html=True)
        num_sats = st.slider("显示卫星数", 1, 8, 4, key='orbit_nsats')
        orbit_type = st.selectbox("轨道类型", ["GPS (MEO ~20200km)", "GLONASS (MEO ~19100km)",
                                                "Galileo (MEO ~23222km)", "北斗GEO+IGSO+MEO混合"])
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:8px; padding:12px; margin-top:12px;">
            <p style="color:#94a3b8; font-size:0.85em;"><b>💡 轨道高度参考：</b><br>
            • GPS: 20,200 km<br>• GLONASS: 19,100 km<br>• Galileo: 23,222 km<br>• 北斗GEO: 35,786 km<br>• 北斗MEO: 21,528 km</p>
        </div>""", unsafe_allow_html=True)
        regen_btn = st.button("🔄 重新生成轨道", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        earth_radius = 6371000
        orbit_heights = {'GPS (MEO ~20200km)': 20200000, 'GLONASS (MEO ~19100km)': 19100000,
                         'Galileo (MEO ~23222km)': 23222000, '北斗GEO+IGSO+MEO混合': 21528000}
        orbit_radius = earth_radius + orbit_heights.get(orbit_type, 20200000)
        np.random.seed(int(time.time()) if regen_btn else 42)
        sat_positions_list = []
        sat_names = []
        for i in range(num_sats):
            inclination = np.random.uniform(50, 65) * np.pi / 180
            raan = np.random.uniform(0, 360) * np.pi / 180
            r = orbit_radius * np.random.uniform(0.92, 1.08)
            theta = np.linspace(0, 2 * np.pi, 200)
            pos = []
            for t in theta:
                x_orb = r * np.cos(t)
                y_orb = r * np.sin(t)
                x = x_orb * np.cos(raan) - y_orb * np.cos(inclination) * np.sin(raan)
                y = x_orb * np.sin(raan) + y_orb * np.cos(inclination) * np.cos(raan)
                z = y_orb * np.sin(inclination)
                pos.append([x, y, z])
            sat_positions_list.append(pos)
            sat_names.append(f"{['G','R','E','C'][i%4]}{i+1:02d}")
        fig = generate_3d_orbit_plot(sat_positions_list, sat_names, earth_radius)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-card"><h4 style="color:#63b3ed;">📊 模拟轨道参数</h4>', unsafe_allow_html=True)
    param_data = []
    for i, name in enumerate(sat_names):
        r = orbit_radius * (0.92 + 0.16 * i / max(num_sats-1, 1))
        altitude = r - earth_radius
        period = 2 * np.pi * np.sqrt(r**3 / 3.986005e14) / 60
        param_data.append({'卫星': name, '轨道半径 (km)': round(r/1000, 1),
                           '高度 (km)': round(altitude/1000, 1), '轨道周期 (min)': round(period, 1),
                           '倾角 (°)': round(np.random.uniform(50, 65), 1)})
    st.dataframe(pd.DataFrame(param_data), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

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