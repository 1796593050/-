#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GNSS卫星导航数据处理平台 - SkyTracker Pro
功能：RINEX数据读取、周跳探测、坐标转换、卫星星空图、轨道可视化
支持格式：RINEX 2.x/3.x观测文件、导航文件、NMEA-0183、CSV
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import io
import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Union
import base64

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
    /* 全局字体和背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', 'Segoe UI', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #0a0f1e 0%, #111827 30%, #0d1524 60%, #0a0f1e 100%);
    }
    
    /* 主卡片样式 */
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
    
    /* 发光标题 */
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
    
    /* 状态指示灯 */
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
    
    /* 数据表格美化 */
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
    
    /* 按钮样式 */
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
    
    /* 指标卡片 */
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
    
    /* 侧边栏美化 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1524 0%, #111827 100%);
        border-right: 1px solid rgba(99, 179, 237, 0.15);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #cbd5e1;
    }
    
    /* 动画容器 */
    .orbit-container {
        position: relative;
        width: 300px;
        height: 300px;
        margin: 0 auto;
    }
    .orbit-earth {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: 80px; height: 80px;
        border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #4fa8e8, #1a5c8a 60%, #0a2a3f 100%);
        box-shadow: 0 0 40px rgba(79, 168, 232, 0.6), 0 0 80px rgba(79, 168, 232, 0.3);
        z-index: 2;
    }
    .orbit-ring {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        border: 1px dashed rgba(255,255,255,0.2);
        z-index: 1;
        animation: rotate 8s linear infinite;
    }
    .orbit-satellite {
        position: absolute;
        width: 12px; height: 12px;
        background: #fff;
        border-radius: 50%;
        box-shadow: 0 0 12px #63b3ed, 0 0 24px rgba(99, 179, 237, 0.6);
        z-index: 3;
        animation: orbit 6s linear infinite;
    }
    
    @keyframes rotate {
        from { transform: translate(-50%, -50%) rotate(0deg); }
        to { transform: translate(-50%, -50%) rotate(360deg); }
    }
    @keyframes orbit {
        0% { transform: rotate(0deg) translateX(120px) rotate(0deg); }
        100% { transform: rotate(360deg) translateX(120px) rotate(-360deg); }
    }
    
    /* Toast提示 */
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
if 'animation_shown' not in st.session_state:
    st.session_state.animation_shown = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'rinex_data' not in st.session_state:
    st.session_state.rinex_data = None
if 'nav_data' not in st.session_state:
    st.session_state.nav_data = None
if 'detected_slips' not in st.session_state:
    st.session_state.detected_slips = None

# ==================== 地球椭球参数 ====================
ELLIPSOIDS = {
    'WGS84': {'a': 6378137.0, 'f': 1/298.257223563, 'name': 'WGS84 (GPS)'},
    'CGCS2000': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'CGCS2000 (北斗)'},
    'PZ90': {'a': 6378136.0, 'f': 1/298.25784, 'name': 'PZ-90 (GLONASS)'},
    'GRS80': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'GRS80'},
    'Krasovsky': {'a': 6378245.0, 'f': 1/298.3, 'name': 'Krasovsky (北京54)'},
}

# ==================== 开场动画 ====================
def show_intro_animation():
    """显示开场动画 - 卫星环绕地球"""
    placeholder = st.empty()
    
    with placeholder.container():
        st.markdown('<div style="height:60px;"></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center;">
                <div style="position:relative; width:300px; height:300px; margin:0 auto;">
                    <!-- 地球 -->
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); 
                         width:90px; height:90px; border-radius:50%;
                         background: radial-gradient(circle at 38% 32%, #7ec8f8 0%, #2980b9 35%, #0d3b66 70%, #061a2e 100%);
                         box-shadow: 0 0 60px rgba(41,128,185,0.7), 0 0 120px rgba(41,128,185,0.35), 0 0 200px rgba(41,128,185,0.15);
                         z-index:5; animation: earthPulse 3s ease-in-out infinite;">
                        <!-- 大陆轮廓模拟 -->
                        <div style="position:absolute; top:25%; left:30%; width:20px; height:15px; 
                             background:rgba(46,204,113,0.5); border-radius:40% 60% 30% 70%;"></div>
                        <div style="position:absolute; top:40%; left:50%; width:18px; height:12px; 
                             background:rgba(46,204,113,0.4); border-radius:50% 40% 60% 30%;"></div>
                    </div>
                    <!-- 轨道环1 -->
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(-30deg);
                         width:220px; height:220px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.2); z-index:2;
                         animation: orbitSpin 10s linear infinite;"></div>
                    <!-- 轨道环2 -->
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(45deg);
                         width:260px; height:260px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.13); z-index:1;
                         animation: orbitSpin 14s linear infinite reverse;"></div>
                    <!-- 轨道环3 -->
                    <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(80deg);
                         width:180px; height:180px; border-radius:50%;
                         border:1px dashed rgba(255,255,255,0.17); z-index:3;
                         animation: orbitSpin 8s linear infinite;"></div>
                    <!-- 卫星 -->
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
            
            # 进入按钮
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1.2, 1])
            with btn_col2:
                if st.button("🚀 进入平台", use_container_width=True, key="enter_btn"):
                    st.session_state.animation_shown = True
                    st.rerun()
            
            # 自动跳转倒计时
            st.markdown("""
            <p style="text-align:center; color:#64748b; font-size:0.8em; margin-top:12px;">
                动画将在 5 秒后自动进入...
            </p>
            """, unsafe_allow_html=True)
            
            # 自动跳转逻辑
            time.sleep(5)
            st.session_state.animation_shown = True
            st.rerun()

# ==================== 坐标转换工具 ====================
def blh_to_xyz(lat_deg, lon_deg, height, ellipsoid='WGS84'):
    """大地坐标(BLH)转地心地固坐标(ECEF-XYZ)"""
    ell = ELLIPSOIDS[ellipsoid]
    a = ell['a']
    f = ell['f']
    e2 = 2 * f - f ** 2
    
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)
    
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    
    X = (N + height) * cos_lat * cos_lon
    Y = (N + height) * cos_lat * sin_lon
    Z = (N * (1 - e2) + height) * sin_lat
    
    return X, Y, Z

def xyz_to_blh(X, Y, Z, ellipsoid='WGS84', max_iter=10, tol=1e-12):
    """ECEF-XYZ转大地坐标BLH（迭代法）"""
    ell = ELLIPSOIDS[ellipsoid]
    a = ell['a']
    f = ell['f']
    e2 = 2 * f - f ** 2
    
    lon_rad = math.atan2(Y, X)
    
    p = math.sqrt(X**2 + Y**2)
    
    # 初始值
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
    
    lat_deg = math.degrees(lat_rad)
    lon_deg = math.degrees(lon_rad)
    
    return lat_deg, lon_deg, height

def blh_to_utm(lat_deg, lon_deg, ellipsoid='WGS84'):
    """大地坐标转UTM投影"""
    ell = ELLIPSOIDS[ellipsoid]
    a = ell['a']
    f = ell['f']
    e2 = 2 * f - f ** 2
    e2_prime = e2 / (1 - e2)
    
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    
    # 计算UTM带号
    zone = int((lon_deg + 180) / 6) + 1
    # 特殊处理挪威和斯瓦尔巴群岛
    if lat_deg >= 56 and lat_deg < 64 and lon_deg >= 3 and lon_deg < 12:
        zone = 32
    if lat_deg >= 72 and lat_deg < 84:
        if lon_deg >= 0 and lon_deg < 9:
            zone = 31
        elif lon_deg >= 9 and lon_deg < 21:
            zone = 33
        elif lon_deg >= 21 and lon_deg < 33:
            zone = 35
        elif lon_deg >= 33 and lon_deg < 42:
            zone = 37
    
    lon0_deg = (zone - 1) * 6 - 180 + 3
    lon0_rad = math.radians(lon0_deg)
    
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)
    
    N = a / math.sqrt(1 - e2 * sin_lat ** 2)
    T = tan_lat ** 2
    C = e2_prime * cos_lat ** 2
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
    
    # 确定纬度带字母
    if lat_deg >= -80 and lat_deg < -72:
        band = 'C'
    elif lat_deg >= -72 and lat_deg < -64:
        band = 'D'
    elif lat_deg >= -64 and lat_deg < -56:
        band = 'E'
    elif lat_deg >= -56 and lat_deg < -48:
        band = 'F'
    elif lat_deg >= -48 and lat_deg < -40:
        band = 'G'
    elif lat_deg >= -40 and lat_deg < -32:
        band = 'H'
    elif lat_deg >= -32 and lat_deg < -24:
        band = 'J'
    elif lat_deg >= -24 and lat_deg < -16:
        band = 'K'
    elif lat_deg >= -16 and lat_deg < -8:
        band = 'L'
    elif lat_deg >= -8 and lat_deg < 0:
        band = 'M'
    elif lat_deg >= 0 and lat_deg < 8:
        band = 'N'
    elif lat_deg >= 8 and lat_deg < 16:
        band = 'P'
    elif lat_deg >= 16 and lat_deg < 24:
        band = 'Q'
    elif lat_deg >= 24 and lat_deg < 32:
        band = 'R'
    elif lat_deg >= 32 and lat_deg < 40:
        band = 'S'
    elif lat_deg >= 40 and lat_deg < 48:
        band = 'T'
    elif lat_deg >= 48 and lat_deg < 56:
        band = 'U'
    elif lat_deg >= 56 and lat_deg < 64:
        band = 'V'
    elif lat_deg >= 64 and lat_deg < 72:
        band = 'W'
    elif lat_deg >= 72 and lat_deg < 84:
        band = 'X'
    else:
        band = 'Z'
    
    return easting, northing, zone, band, f"{zone}{band}"

def utm_to_blh(easting, northing, zone, band, ellipsoid='WGS84', northern_hemisphere=True):
    """UTM投影转大地坐标"""
    ell = ELLIPSOIDS[ellipsoid]
    a = ell['a']
    f = ell['f']
    e2 = 2 * f - f ** 2
    e2_prime = e2 / (1 - e2)
    
    k0 = 0.9996
    x = easting - 500000
    
    if not northern_hemisphere:
        y = northing - 10000000
    else:
        y = northing
    
    M = y / k0
    
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    
    lat_rad = mu + (3*e1/2 - 27*e1**3/32) * math.sin(2*mu) \
              + (21*e1**2/16 - 55*e1**4/32) * math.sin(4*mu) \
              + (151*e1**3/96) * math.sin(6*mu) \
              + (1097*e1**4/512) * math.sin(8*mu)
    
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    tan_lat = math.tan(lat_rad)
    
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    T = tan_lat**2
    C = e2_prime * cos_lat**2
    
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
    
    lat_deg = math.degrees(lat_rad)
    lon_deg = math.degrees(lon_rad)
    
    sin_lat_final = math.sin(lat_rad)
    N_final = a / math.sqrt(1 - e2 * sin_lat_final**2)
    height = 0  # UTM不包含高程信息
    
    return lat_deg, lon_deg, height

# ==================== RINEX解析器 ====================
class RinexParser:
    """RINEX观测文件和导航文件解析器"""
    
    @staticmethod
    def parse_observation_header(lines: List[str]) -> Dict:
        """解析RINEX观测文件头部"""
        header = {
            'version': '2.11',
            'rinex_type': 'O',
            'system': 'G',
            'marker_name': '',
            'observer': '',
            'receiver': '',
            'antenna': '',
            'approx_position': [0, 0, 0],
            'antenna_delta': [0, 0, 0],
            'observation_types': [],
            'num_obs_types': 0,
            'time_of_first_obs': '',
            'interval': 0,
            'num_satellites': 0,
            'prn_list': [],
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
                    header['approx_position'] = [float(parts[0]), float(parts[1]), float(parts[2])]
            elif 'ANTENNA: DELTA H/E/N' in label:
                parts = line[0:60].strip().split()
                if len(parts) >= 3:
                    header['antenna_delta'] = [float(parts[0]), float(parts[1]), float(parts[2])]
            elif '# / TYPES OF OBSERV' in label or 'SYS / # / OBS TYPES' in label:
                if float(header['version']) >= 3.0:
                    # RINEX 3格式
                    sys_char = line[0:1] if len(line) > 0 else 'G'
                    if sys_char == header.get('system', 'G'):
                        ntypes = int(line[3:6]) if len(line) > 5 else 0
                        header['num_obs_types'] = ntypes
                        obs_str = line[7:60].strip()
                        header['observation_types'].extend(obs_str.split())
                else:
                    ntypes = int(line[0:6]) if len(line) > 5 else 0
                    header['num_obs_types'] = ntypes
                    obs_str = line[6:60].strip()
                    header['observation_types'].extend(obs_str.split())
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
        """解析RINEX观测数据"""
        records = []
        i = 0
        version = float(header.get('version', '2.11'))
        nobs = header.get('num_obs_types', 0)
        
        # 找到END OF HEADER
        data_start = 0
        for j, line in enumerate(lines):
            if 'END OF HEADER' in line:
                data_start = j + 1
                break
        
        data_lines = lines[data_start:]
        line_idx = 0
        
        while line_idx < len(data_lines):
            line = data_lines[line_idx]
            if not line.strip() or len(line) < 30:
                line_idx += 1
                continue
            
            # 解析历元行
            try:
                if version < 3.0:
                    # RINEX 2.x
                    yr = int(line[0:3])
                    if yr >= 80:
                        yr += 1900
                    else:
                        yr += 2000
                    month = int(line[3:6])
                    day = int(line[6:9])
                    hour = int(line[9:12])
                    minute = int(line[12:15])
                    second = float(line[15:26])
                    epoch_flag = int(line[28:29]) if len(line) > 28 else 0
                    num_sats = int(line[29:32]) if len(line) > 29 else 0
                    
                    epoch_time = datetime(yr, month, day, hour, minute, int(second), 
                                          int((second - int(second)) * 1e6))
                    
                    # 读取卫星列表
                    sat_line = line[32:].strip()
                    sat_ids = []
                    for k in range(0, len(sat_line), 3):
                        sat_id = sat_line[k:k+3].strip()
                        if sat_id:
                            sat_ids.append(sat_id)
                    
                    # 如果一行不够，继续读取
                    while len(sat_ids) < num_sats:
                        line_idx += 1
                        if line_idx >= len(data_lines):
                            break
                        extra_line = data_lines[line_idx]
                        for k in range(0, len(extra_line.strip()), 3):
                            sat_id = extra_line.strip()[k:k+3].strip()
                            if sat_id:
                                sat_ids.append(sat_id)
                    
                    line_idx += 1
                    
                    # 读取各卫星观测值
                    for sat_id in sat_ids[:num_sats]:
                        if line_idx >= len(data_lines):
                            break
                        obs_line = data_lines[line_idx]
                        record = {
                            'epoch': epoch_time,
                            'satellite': sat_id.strip(),
                            'epoch_flag': epoch_flag,
                        }
                        
                        # 读取观测值（每行最多5个值，每个14字符）
                        obs_values = []
                        remaining = nobs
                        current_line = obs_line
                        while remaining > 0 and line_idx < len(data_lines):
                            vals_in_line = min(remaining, 5)
                            for k in range(vals_in_line):
                                start = k * 14
                                end = start + 14
                                val_str = current_line[start:end].strip() if len(current_line) > start else ''
                                try:
                                    obs_values.append(float(val_str)) if val_str else obs_values.append(np.nan)
                                except:
                                    obs_values.append(np.nan)
                            remaining -= vals_in_line
                            if remaining > 0:
                                line_idx += 1
                                if line_idx < len(data_lines):
                                    current_line = data_lines[line_idx]
                        
                        # 填充观测值
                        for k, obs_type in enumerate(header.get('observation_types', [])[:nobs]):
                            if k < len(obs_values):
                                record[obs_type] = obs_values[k]
                            else:
                                record[obs_type] = np.nan
                        
                        records.append(record)
                        line_idx += 1
                        
                else:
                    # RINEX 3.x格式
                    # > 2024 01 15 10 30 00.0000000  0 12
                    epoch_str = line[1:].strip()
                    parts = epoch_str.split()
                    if len(parts) >= 6:
                        yr = int(parts[0])
                        month = int(parts[1])
                        day = int(parts[2])
                        hour = int(parts[3])
                        minute = int(parts[4])
                        second = float(parts[5])
                        epoch_flag = int(parts[6]) if len(parts) > 6 else 0
                        num_sats = int(parts[7]) if len(parts) > 7 else 0
                        
                        epoch_time = datetime(yr, month, day, hour, minute, int(second),
                                              int((second - int(second)) * 1e6))
                        
                        line_idx += 1
                        for _ in range(num_sats):
                            if line_idx >= len(data_lines):
                                break
                            sat_line = data_lines[line_idx]
                            sat_id = sat_line[0:3].strip()
                            record = {
                                'epoch': epoch_time,
                                'satellite': sat_id,
                                'epoch_flag': epoch_flag,
                            }
                            
                            obs_str = sat_line[3:].strip()
                            obs_parts = obs_str.split()
                            for k, obs_type in enumerate(header.get('observation_types', [])[:nobs]):
                                if k < len(obs_parts):
                                    try:
                                        record[obs_type] = float(obs_parts[k])
                                    except:
                                        record[obs_type] = np.nan
                                else:
                                    record[obs_type] = np.nan
                            
                            records.append(record)
                            line_idx += 1
                    else:
                        line_idx += 1
            except Exception as e:
                line_idx += 1
                continue
        
        if records:
            df = pd.DataFrame(records)
            return df
        return pd.DataFrame()
    
    @staticmethod
    def parse_navigation_header(lines: List[str]) -> Dict:
        """解析导航文件头部"""
        header = {
            'version': '2.11',
            'rinex_type': 'N',
            'ion_alpha': [0, 0, 0, 0],
            'ion_beta': [0, 0, 0, 0],
            'leap_seconds': 0,
        }
        
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
        """解析GPS导航文件广播星历"""
        records = []
        
        data_start = 0
        for j, line in enumerate(lines):
            if 'END OF HEADER' in line:
                data_start = j + 1
                break
        
        data_lines = lines[data_start:]
        line_idx = 0
        
        while line_idx < len(data_lines) - 7:
            try:
                line = data_lines[line_idx]
                if not line.strip():
                    line_idx += 1
                    continue
                
                # 第一行：卫星PRN和日期时间
                prn = line[0:3].strip()
                yr = int(line[3:6])
                if yr >= 80:
                    yr += 1900
                else:
                    yr += 2000
                month = int(line[6:9])
                day = int(line[9:12])
                hour = int(line[12:15])
                minute = int(line[15:18])
                second = float(line[18:22])
                
                toc = datetime(yr, month, day, hour, minute, int(second))
                
                # 解析8行广播星历数据
                record = {
                    'satellite': prn,
                    'toc': toc,
                }
                
                # 第1行剩余部分
                record['af0'] = float(line[22:41].replace('D', 'E'))
                record['af1'] = float(line[41:60].replace('D', 'E'))
                
                # 第2行
                line_idx += 1
                l2 = data_lines[line_idx]
                record['af2'] = float(l2[0:19].replace('D', 'E'))
                record['crs'] = float(l2[19:38].replace('D', 'E'))
                record['delta_n'] = float(l2[38:57].replace('D', 'E'))
                record['M0'] = float(l2[57:76].replace('D', 'E')) if len(l2) > 57 else 0
                
                # 第3行
                line_idx += 1
                l3 = data_lines[line_idx]
                record['cuc'] = float(l3[0:19].replace('D', 'E'))
                record['ecc'] = float(l3[19:38].replace('D', 'E'))
                record['cus'] = float(l3[38:57].replace('D', 'E'))
                record['sqrt_a'] = float(l3[57:76].replace('D', 'E')) if len(l3) > 57 else 0
                
                # 第4行
                line_idx += 1
                l4 = data_lines[line_idx]
                record['toe'] = float(l4[0:19].replace('D', 'E'))
                record['cic'] = float(l4[19:38].replace('D', 'E'))
                record['OMEGA0'] = float(l4[38:57].replace('D', 'E'))
                record['cis'] = float(l4[57:76].replace('D', 'E')) if len(l4) > 57 else 0
                
                # 第5行
                line_idx += 1
                l5 = data_lines[line_idx]
                record['i0'] = float(l5[0:19].replace('D', 'E'))
                record['crc'] = float(l5[19:38].replace('D', 'E'))
                record['omega'] = float(l5[38:57].replace('D', 'E'))
                record['OMEGA_DOT'] = float(l5[57:76].replace('D', 'E')) if len(l5) > 57 else 0
                
                # 第6行
                line_idx += 1
                l6 = data_lines[line_idx]
                record['i_dot'] = float(l6[0:19].replace('D', 'E'))
                
                # 第7行
                line_idx += 1
                l7 = data_lines[line_idx]
                record['week_num'] = int(float(l7[0:19].replace('D', 'E'))) if l7[0:19].strip() else 0
                
                records.append(record)
                line_idx += 1
                
            except Exception as e:
                line_idx += 1
                continue
        
        if records:
            return pd.DataFrame(records)
        return pd.DataFrame()

# ==================== 周跳探测算法 ====================
class CycleSlipDetector:
    """周跳探测 - GF组合和MW组合"""
    
    @staticmethod
    def gf_combination(L1, L2, f1=1575.42e6, f2=1227.60e6, threshold=0.05):
        """
        几何无关组合(GF组合)周跳探测
        GF = L1 - (f1/f2) * L2（以周为单位）
        或简化为 GF = L1 - L2（近似）
        """
        c = 299792458.0
        lambda1 = c / f1
        lambda2 = c / f2
        
        # L1和L2以周为单位，转为米
        L1_m = L1 * lambda1
        L2_m = L2 * lambda2
        
        # GF组合（以米为单位）
        gf = L1_m - L2_m
        
        # 检测跳变
        gf_diff = np.diff(gf, prepend=gf[0])
        slips = np.where(np.abs(gf_diff) > threshold)[0]
        
        return gf, slips, gf_diff
    
    @staticmethod
    def mw_combination(L1, L2, P1, P2, f1=1575.42e6, f2=1227.60e6, threshold=2.0):
        """
        Melbourne-Wübbena组合周跳探测
        MW = (f1*L1 - f2*L2)/(f1-f2) - (f1*P1 + f2*P2)/(f1+f2)
        结果以周为单位
        """
        c = 299792458.0
        lambda1 = c / f1
        lambda2 = c / f2
        
        # 转为米
        L1_m = L1 * lambda1
        L2_m = L2 * lambda2
        
        # 宽巷组合（以米为单位，转为周需除以宽巷波长）
        lambda_w = c / (f1 - f2)  # 宽巷波长约0.86m
        mw = (f1 * L1_m - f2 * L2_m) / (f1 - f2) / lambda_w - (f1 * P1 + f2 * P2) / (f1 + f2) / lambda_w
        
        # 使用滑动窗口检测
        window_size = min(10, len(mw))
        slips = []
        
        if len(mw) > window_size:
            for i in range(window_size, len(mw)):
                window_mean = np.nanmean(mw[i-window_size:i])
                window_std = np.nanstd(mw[i-window_size:i])
                if window_std > 0 and abs(mw[i] - window_mean) > threshold * window_std:
                    slips.append(i)
        
        return mw, np.array(slips)
    
    @staticmethod
    def detect_all(df: pd.DataFrame, f1=1575.42e6, f2=1227.60e6) -> Dict:
        """综合周跳探测"""
        results = {'slips': [], 'gf_values': None, 'mw_values': None, 'summary': ''}
        
        # 查找L1和L2观测值列
        l1_cols = [c for c in df.columns if 'L1' in c.upper() or 'C1' in c.upper()]
        l2_cols = [c for c in df.columns if 'L2' in c.upper() or 'C2' in c.upper()]
        p1_cols = [c for c in df.columns if 'P1' in c.upper() or 'C1' in c.upper()]
        p2_cols = [c for c in df.columns if 'P2' in c.upper()]
        
        if not l1_cols or not l2_cols:
            return results
        
        l1_col = l1_cols[0]
        l2_col = l2_cols[0]
        
        # 对每颗卫星分别处理
        all_slips = []
        for sat in df['satellite'].unique():
            sat_data = df[df['satellite'] == sat].sort_values('epoch').reset_index(drop=True)
            
            l1_vals = sat_data[l1_col].values
            l2_vals = sat_data[l2_col].values
            
            # 去除NaN
            valid_mask = ~(np.isnan(l1_vals) | np.isnan(l2_vals))
            
            if np.sum(valid_mask) < 5:
                continue
            
            l1_clean = l1_vals[valid_mask]
            l2_clean = l2_vals[valid_mask]
            valid_indices = np.where(valid_mask)[0]
            
            # GF探测
            gf, gf_slips, _ = CycleSlipDetector.gf_combination(l1_clean, l2_clean, f1, f2)
            
            for slip_idx in gf_slips:
                if slip_idx < len(valid_indices):
                    orig_idx = valid_indices[slip_idx]
                    epoch = sat_data.iloc[orig_idx]['epoch']
                    all_slips.append({
                        'satellite': sat,
                        'epoch': epoch,
                        'index': orig_idx,
                        'method': 'GF组合',
                        'gf_value': gf[slip_idx] if slip_idx < len(gf) else 0,
                    })
            
            # MW探测（如果有伪距观测值）
            if p1_cols and p2_cols:
                p1_col = p1_cols[0]
                p2_col = p2_cols[0]
                p1_vals = sat_data[p1_col].values[valid_mask]
                p2_vals = sat_data[p2_col].values[valid_mask]
                
                if len(p1_vals) == len(l1_clean):
                    mw, mw_slips = CycleSlipDetector.mw_combination(
                        l1_clean, l2_clean, p1_vals, p2_vals, f1, f2
                    )
                    for slip_idx in mw_slips:
                        if slip_idx < len(valid_indices):
                            orig_idx = valid_indices[slip_idx]
                            epoch = sat_data.iloc[orig_idx]['epoch']
                            all_slips.append({
                                'satellite': sat,
                                'epoch': epoch,
                                'index': orig_idx,
                                'method': 'MW组合',
                                'mw_value': mw[slip_idx] if slip_idx < len(mw) else 0,
                            })
        
        results['slips'] = all_slips
        results['summary'] = f"检测到 {len(all_slips)} 处疑似周跳，涉及 {len(set(s['satellite'] for s in all_slips))} 颗卫星"
        
        return results

# ==================== 模拟数据生成 ====================
def generate_simulated_obs_data(num_epochs=100, num_sats=8, slip_epochs=None):
    """生成模拟的GNSS观测数据（用于演示周跳探测）"""
    if slip_epochs is None:
        slip_epochs = [25, 55, 78]
    
    np.random.seed(42)
    
    epochs = [datetime(2024, 6, 21, 10, 0, 0) + timedelta(seconds=30*i) for i in range(num_epochs)]
    
    records = []
    for i, epoch in enumerate(epochs):
        for sat_idx in range(num_sats):
            sat_id = f"G{sat_idx+1:02d}"
            
            # 模拟L1和L2载波相位观测值（以周为单位）
            base_l1 = 1e7 + sat_idx * 1e5 + i * 5000
            base_l2 = 8e6 + sat_idx * 8e4 + i * 3900
            
            # 添加噪声
            l1 = base_l1 + np.random.normal(0, 0.01)
            l2 = base_l2 + np.random.normal(0, 0.012)
            
            # 在特定历元注入周跳
            if i in slip_epochs and sat_idx in [1, 3, 5]:
                l1 += np.random.choice([-15, 12, -8, 20]) * np.random.choice([1, 2, 3])
                l2 += np.random.choice([-10, 8, -6, 15])
            
            # 模拟伪距
            p1 = 2.1e7 + sat_idx * 2e5 + i * 5000 + np.random.normal(0, 0.5)
            p2 = 2.1e7 + sat_idx * 2e5 + i * 5000 + np.random.normal(0, 0.6)
            
            records.append({
                'epoch': epoch,
                'satellite': sat_id,
                'L1': l1,
                'L2': l2,
                'P1': p1,
                'P2': p2,
                'epoch_flag': 0,
            })
    
    df = pd.DataFrame(records)
    return df, slip_epochs

# ==================== 卫星位置计算 ====================
def compute_satellite_position(nav_record: Dict, time_gps: datetime, system='GPS') -> Optional[np.ndarray]:
    """
    基于广播星历计算卫星位置（ECEF坐标）
    简化版GPS卫星位置计算
    """
    try:
        mu = 3.986005e14  # 地球引力常数
        omega_e = 7.2921151467e-5  # 地球自转角速度
        
        toc = nav_record.get('toc')
        if toc is None:
            return None
        
        dt = (time_gps - toc).total_seconds()
        
        sqrt_a = nav_record.get('sqrt_a', 5153.5)
        a = sqrt_a ** 2
        
        delta_n = nav_record.get('delta_n', 0)
        n0 = math.sqrt(mu / a**3)
        n = n0 + delta_n
        
        M0 = nav_record.get('M0', 0)
        M = M0 + n * dt
        
        ecc = nav_record.get('ecc', 0.01)
        
        # 迭代求解偏近点角E
        E = M
        for _ in range(10):
            E_new = M + ecc * math.sin(E)
            if abs(E_new - E) < 1e-12:
                E = E_new
                break
            E = E_new
        
        # 真近点角
        v = math.atan2(math.sqrt(1 - ecc**2) * math.sin(E), math.cos(E) - ecc)
        
        # 升交角距
        omega = nav_record.get('omega', 0)
        phi = v + omega
        
        # 摄动改正
        cus = nav_record.get('cus', 0)
        cuc = nav_record.get('cuc', 0)
        crs = nav_record.get('crs', 0)
        crc = nav_record.get('crc', 0)
        cis = nav_record.get('cis', 0)
        cic = nav_record.get('cic', 0)
        
        delta_u = cus * math.sin(2*phi) + cuc * math.cos(2*phi)
        delta_r = crs * math.sin(2*phi) + crc * math.cos(2*phi)
        delta_i = cis * math.sin(2*phi) + cic * math.cos(2*phi)
        
        u = phi + delta_u
        r = a * (1 - ecc * math.cos(E)) + delta_r
        i0 = nav_record.get('i0', 0.96)
        i_dot = nav_record.get('i_dot', 0)
        i = i0 + delta_i + i_dot * dt
        
        # 轨道平面坐标
        x_orb = r * math.cos(u)
        y_orb = r * math.sin(u)
        
        # 升交点赤经
        OMEGA0 = nav_record.get('OMEGA0', 0)
        OMEGA_DOT = nav_record.get('OMEGA_DOT', 0)
        OMEGA = OMEGA0 + (OMEGA_DOT - omega_e) * dt - omega_e * (toc - datetime(1980, 1, 6)).total_seconds()
        
        # ECEF坐标
        X = x_orb * math.cos(OMEGA) - y_orb * math.cos(i) * math.sin(OMEGA)
        Y = x_orb * math.sin(OMEGA) + y_orb * math.cos(i) * math.cos(OMEGA)
        Z = y_orb * math.sin(i)
        
        return np.array([X, Y, Z])
        
    except Exception:
        return None

# ==================== NMEA解析器 ====================
def parse_nmea_sentence(sentence: str) -> Dict:
    """解析NMEA-0183语句"""
    result = {'type': 'unknown', 'valid': False}
    
    if not sentence.startswith('$'):
        return result
    
    # 去除校验和
    if '*' in sentence:
        sentence, checksum = sentence.split('*', 1)
    
    parts = sentence.split(',')
    talker_id = parts[0][1:]
    
    if talker_id in ['GPGGA', 'GNGGA']:
        result['type'] = 'GGA'
        if len(parts) >= 15:
            try:
                lat_deg = float(parts[2][:2]) if parts[2] else 0
                lat_min = float(parts[2][2:]) if len(parts[2]) > 2 else 0
                lat = lat_deg + lat_min / 60
                if parts[3] == 'S':
                    lat = -lat
                
                lon_deg = float(parts[4][:3]) if parts[4] else 0
                lon_min = float(parts[4][3:]) if len(parts[4]) > 3 else 0
                lon = lon_deg + lon_min / 60
                if parts[5] == 'W':
                    lon = -lon
                
                result.update({
                    'latitude': lat,
                    'longitude': lon,
                    'quality': int(parts[6]) if parts[6] else 0,
                    'num_sats': int(parts[7]) if parts[7] else 0,
                    'hdop': float(parts[8]) if parts[8] else 0,
                    'altitude': float(parts[9]) if parts[9] else 0,
                    'valid': True,
                })
            except:
                pass
    
    elif talker_id in ['GPRMC', 'GNRMC']:
        result['type'] = 'RMC'
        if len(parts) >= 10:
            try:
                lat_deg = float(parts[3][:2]) if parts[3] else 0
                lat_min = float(parts[3][2:]) if len(parts[3]) > 2 else 0
                lat = lat_deg + lat_min / 60
                if parts[4] == 'S':
                    lat = -lat
                
                lon_deg = float(parts[5][:3]) if parts[5] else 0
                lon_min = float(parts[5][3:]) if len(parts[5]) > 3 else 0
                lon = lon_deg + lon_min / 60
                if parts[6] == 'W':
                    lon = -lon
                
                result.update({
                    'latitude': lat,
                    'longitude': lon,
                    'speed': float(parts[7]) if parts[7] else 0,
                    'valid': parts[2] == 'A',
                })
            except:
                pass
    
    return result

# ==================== 星空图生成 ====================
def generate_skyplot(sat_azimuths, sat_elevations, sat_labels=None):
    """生成GNSS星空图（极坐标图）"""
    fig = go.Figure()
    
    # 转换仰角为半径（90度仰角在中心，0度在边缘）
    radii = [90 - el for el in sat_elevations]
    
    # 转换方位角（从北顺时针，plotly从东逆时针）
    theta = [(90 - az) % 360 for az in sat_azimuths]
    
    if sat_labels is None:
        sat_labels = [f'SAT{i+1}' for i in range(len(sat_azimuths))]
    
    # 添加同心圆（仰角线）
    for el_level in [0, 30, 60, 90]:
        circle_r = 90 - el_level
        circle_theta = np.linspace(0, 360, 200)
        fig.add_trace(go.Scatterpolar(
            r=[circle_r] * 200,
            theta=circle_theta,
            mode='lines',
            line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
            showlegend=False,
            hoverinfo='none',
        ))
    
    # 添加卫星点
    colors = ['#63b3ed', '#48bb78', '#f6e05e', '#fc8181', '#b794f4', 
              '#f687b3', '#68d391', '#fbd38d', '#63b3ed', '#48bb78']
    
    for i, (r, t, label) in enumerate(zip(radii, theta, sat_labels)):
        fig.add_trace(go.Scatterpolar(
            r=[r],
            theta=[t],
            mode='markers+text',
            marker=dict(
                size=14,
                color=colors[i % len(colors)],
                symbol='circle',
                line=dict(color='white', width=1.5),
            ),
            text=label,
            textposition='top center',
            textfont=dict(size=9, color='white'),
            name=label,
            hovertemplate=f'<b>{label}</b><br>方位角: {sat_azimuths[i]:.1f}°<br>仰角: {sat_elevations[i]:.1f}°',
        ))
    
    # 添加N/E/S/W标记
    for direction, angle in [('N', 0), ('E', 90), ('S', 180), ('W', 270)]:
        fig.add_trace(go.Scatterpolar(
            r=[95],
            theta=[angle],
            mode='text',
            text=[direction],
            textfont=dict(size=14, color='white', family='Inter'),
            showlegend=False,
            hoverinfo='none',
        ))
    
    fig.update_polar(
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
            direction='clockwise',
        ),
        bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_layout(
        title=dict(
            text='🛰️ GNSS卫星星空图',
            font=dict(size=16, color='#e2e8f0'),
            x=0.5,
        ),
        height=500,
        margin=dict(l=40, r=40, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            font=dict(size=10, color='#94a3b8'),
            bgcolor='rgba(15,23,42,0.8)',
            bordercolor='rgba(255,255,255,0.1)',
        ),
    )
    
    return fig

# ==================== 3D轨道可视化 ====================
def generate_3d_orbit_plot(sat_positions_list, sat_names, earth_radius=6371000):
    """生成3D卫星轨道图"""
    fig = go.Figure()
    
    # 绘制地球（球体近似）
    u = np.linspace(0, 2*np.pi, 60)
    v = np.linspace(0, np.pi, 40)
    x_earth = earth_radius * np.outer(np.cos(u), np.sin(v))
    y_earth = earth_radius * np.outer(np.sin(u), np.sin(v))
    z_earth = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
    
    fig.add_trace(go.Surface(
        x=x_earth, y=y_earth, z=z_earth,
        colorscale=[[0, '#1a3a5c'], [0.5, '#2980b9'], [1, '#0d2137']],
        showscale=False,
        opacity=0.85,
        name='地球',
        hoverinfo='none',
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.3, roughness=0.5),
    ))
    
    colors = ['#63b3ed', '#48bb78', '#f6e05e', '#fc8181', '#b794f4', '#f687b3']
    
    for i, (positions, name) in enumerate(zip(sat_positions_list, sat_names)):
        if positions is None or len(positions) < 2:
            continue
        pos_array = np.array(positions)
        color = colors[i % len(colors)]
        
        fig.add_trace(go.Scatter3d(
            x=pos_array[:, 0],
            y=pos_array[:, 1],
            z=pos_array[:, 2],
            mode='lines+markers',
            line=dict(color=color, width=2.5),
            marker=dict(size=3, color=color),
            name=name,
            hovertemplate=f'<b>{name}</b><br>X: %{{x:.0f}}<br>Y: %{{y:.0f}}<br>Z: %{{z:.0f}}',
        ))
    
    # 坐标轴范围
    max_range = earth_radius * 1.8
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-max_range, max_range], title='X (m)', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(range=[-max_range, max_range], title='Y (m)', gridcolor='rgba(255,255,255,0.1)'),
            zaxis=dict(range=[-max_range, max_range], title='Z (m)', gridcolor='rgba(255,255,255,0.1)'),
            aspectmode='cube',
            bgcolor='rgba(0,0,0,0)',
        ),
        title=dict(
            text='🌍 GNSS卫星3D轨道可视化',
            font=dict(size=16, color='#e2e8f0'),
            x=0.5,
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            font=dict(size=10, color='#94a3b8'),
            bgcolor='rgba(15,23,42,0.8)',
        ),
    )
    
    return fig

# ==================== 主界面组件 ====================
def render_sidebar():
    """渲染侧边栏导航"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:16px 0;">
            <span style="font-size:1.6em;">🛰️</span>
            <h3 style="color:#63b3ed; margin:4px 0; font-weight:600;">SkyTracker Pro</h3>
            <p style="color:#64748b; font-size:0.8em;">GNSS数据处理平台 v2.0</p>
        </div>
        <hr style="border-color:rgba(255,255,255,0.1);">
        """, unsafe_allow_html=True)
        
        # 导航菜单
        menu_options = {
            'home': '🏠 首页总览',
            'data_reader': '📡 数据读取',
            'slip_detector': '🔍 周跳探测',
            'coord_converter': '🗺️ 坐标转换',
            'skyplot': '🌌 卫星星空图',
            'orbit_viewer': '🛰️ 3D轨道可视化',
        }
        
        for key, label in menu_options.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True,
                        help=f"跳转到{label.split(' ',1)[1]}"):
                st.session_state.current_page = key
                st.rerun()
        
        st.markdown('<hr style="border-color:rgba(255,255,255,0.1);">', unsafe_allow_html=True)
        
        # 状态信息
        st.markdown(f"""
        <div style="font-size:0.8em; color:#64748b; padding:8px;">
            <p><span class="status-dot green"></span> 系统就绪</p>
            <p>📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>🛰️ GNSS星座: GPS+GLONASS+Galileo+北斗</p>
        </div>
        """, unsafe_allow_html=True)

def render_home_page():
    """首页总览"""
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
        # 快速状态面板
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:12px; padding:16px; text-align:center;">
            <p style="font-size:3em; margin:0;">🛰️</p>
            <p style="color:#63b3ed; font-weight:600;">多系统支持</p>
            <p style="color:#94a3b8; font-size:0.85em;">GPS | GLONASS | Galileo | 北斗</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 指标卡片行
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
    
    # 快速入口
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.markdown('<h3 style="color:#e2e8f0;">⚡ 快速入口</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📡 开始读取数据", use_container_width=True, key="quick_data"):
            st.session_state.current_page = 'data_reader'
            st.rerun()
    with col2:
        if st.button("🔍 周跳探测演示", use_container_width=True, key="quick_slip"):
            st.session_state.current_page = 'slip_detector'
            st.rerun()
    with col3:
        if st.button("🗺️ 坐标转换工具", use_container_width=True, key="quick_coord"):
            st.session_state.current_page = 'coord_converter'
            st.rerun()

def render_data_reader_page():
    """数据读取页面"""
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#63b3ed;">📡 数据读取模块</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">支持RINEX观测文件、导航文件、NMEA-0183及CSV格式</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📂 文件上传", "📊 数据预览", "ℹ️ 文件信息"])
    
    with tab1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            obs_file = st.file_uploader(
                "上传RINEX观测文件 (.obs / .rnx / .o)",
                type=['obs', 'rnx', 'o', 'txt', 'dat'],
                key='obs_uploader'
            )
            
            if obs_file is not None:
                st.markdown('<div class="toast">✅ 观测文件已加载</div>', unsafe_allow_html=True)
        
        with col2:
            nav_file = st.file_uploader(
                "上传RINEX导航文件 (.nav / .n / .sp3)",
                type=['nav', 'n', 'sp3', 'txt', 'dat'],
                key='nav_uploader'
            )
            
            if nav_file is not None:
                st.markdown('<div class="toast">✅ 导航文件已加载</div>', unsafe_allow_html=True)
        
        # NMEA或CSV
        aux_file = st.file_uploader(
            "上传NMEA日志或CSV数据（可选）",
            type=['nmea', 'log', 'csv', 'txt'],
            key='aux_uploader'
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 处理上传的文件
        if obs_file is not None:
            content = obs_file.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            
            header = RinexParser.parse_observation_header(lines)
            df = RinexParser.parse_observation_data(lines, header)
            
            st.session_state.rinex_data = {
                'header': header,
                'dataframe': df,
                'lines': lines,
                'filename': obs_file.name,
            }
            
            st.markdown(f"""
            <div class="main-card">
                <h4 style="color:#48bb78;">✅ 解析成功</h4>
                <p>文件: <b>{obs_file.name}</b> | 版本: RINEX {header['version']} | 
                观测类型数: {header['num_obs_types']} | 数据行数: {len(df)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if nav_file is not None:
            content = nav_file.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            
            nav_header = RinexParser.parse_navigation_header(lines)
            nav_df = RinexParser.parse_navigation_data(lines, nav_header)
            
            st.session_state.nav_data = {
                'header': nav_header,
                'dataframe': nav_df,
                'filename': nav_file.name,
            }
            
            st.markdown(f"""
            <div class="main-card">
                <h4 style="color:#48bb78;">✅ 导航文件解析成功</h4>
                <p>文件: <b>{nav_file.name}</b> | 卫星数: {len(nav_df['satellite'].unique()) if not nav_df.empty else 0} | 
                星历记录: {len(nav_df)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        if aux_file is not None:
            content = aux_file.read().decode('utf-8', errors='replace')
            if aux_file.name.endswith('.csv'):
                try:
                    aux_df = pd.read_csv(io.StringIO(content))
                    st.session_state.aux_data = aux_df
                    st.markdown(f'<div class="toast">✅ CSV数据已加载 ({len(aux_df)} 行)</div>', unsafe_allow_html=True)
                except:
                    st.warning("CSV解析失败，请检查格式")
            else:
                # 尝试NMEA解析
                nmea_results = []
                for line in content.split('\n'):
                    if line.strip().startswith('$'):
                        result = parse_nmea_sentence(line.strip())
                        if result['valid']:
                            nmea_results.append(result)
                if nmea_results:
                    st.session_state.nmea_data = nmea_results
                    st.markdown(f'<div class="toast">✅ NMEA数据已解析 ({len(nmea_results)} 条有效定位)</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        if st.session_state.rinex_data is not None:
            df = st.session_state.rinex_data['dataframe']
            st.markdown(f'<p style="color:#94a3b8;">共 {len(df)} 条观测记录</p>', unsafe_allow_html=True)
            
            # 显示数据表格
            display_df = df.head(50).copy()
            for col in display_df.columns:
                if display_df[col].dtype in [np.float64, float]:
                    display_df[col] = display_df[col].round(4)
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
            )
            
            if len(df) > 50:
                st.info(f"仅显示前50行，共{len(df)}行数据")
        else:
            st.info("📂 请先在「文件上传」标签页中上传RINEX观测文件")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        if st.session_state.rinex_data is not None:
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
            
            # 观测类型列表
            obs_types = header.get('observation_types', [])
            if obs_types:
                st.markdown(f"""
                <h4 style="color:#63b3ed;">📊 观测类型</h4>
                <p style="color:#cbd5e1;">{' | '.join([f'<code style="background:rgba(99,179,237,0.15);padding:2px 8px;border-radius:4px;">{t}</code>' for t in obs_types])}</p>
                """, unsafe_allow_html=True)
        else:
            st.info("📂 请先上传RINEX文件")
        st.markdown('</div>', unsafe_allow_html=True)

def render_slip_detector_page():
    """周跳探测页面"""
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#48bb78;">🔍 周跳探测模块</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">GF组合 + MW组合双算法联合探测</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">⚙️ 探测参数设置</h4>', unsafe_allow_html=True)
        
        use_demo = st.checkbox("使用演示数据（模拟含周跳的观测数据）", value=True, key='use_demo_slip')
        
        if not use_demo:
            st.info("请先在「数据读取」模块上传RINEX观测文件")
        
        col_a, col_b = st.columns(2)
        with col_a:
            gf_threshold = st.number_input("GF阈值 (米)", value=0.05, step=0.01, format="%.3f",
                                           help="GF组合跳变检测阈值")
        with col_b:
            mw_threshold = st.number_input("MW阈值 (标准差倍数)", value=2.0, step=0.5,
                                           help="MW组合滑动窗口检测阈值")
        
        detect_btn = st.button("🔍 开始探测", use_container_width=True, key='detect_btn')
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">📊 探测结果统计</h4>', unsafe_allow_html=True)
        
        if detect_btn or st.session_state.detected_slips is not None:
            if use_demo:
                # 生成演示数据
                slip_epochs_injected = [25, 55, 78]
                demo_df, injected = generate_simulated_obs_data(
                    num_epochs=120, num_sats=8, slip_epochs=slip_epochs_injected
                )
                # 添加satellite列名确保兼容
                results = CycleSlipDetector.detect_all(demo_df)
                st.session_state.detected_slips = results
                st.session_state.demo_df = demo_df
                st.session_state.injected_slips = slip_epochs_injected
            elif st.session_state.rinex_data is not None:
                df = st.session_state.rinex_data['dataframe']
                results = CycleSlipDetector.detect_all(df)
                st.session_state.detected_slips = results
                st.session_state.demo_df = df
            else:
                results = None
        
        if st.session_state.detected_slips is not None:
            results = st.session_state.detected_slips
            slips = results.get('slips', [])
            
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="color:#fc8181;">{len(slips)}</div>
                    <div class="metric-label">疑似周跳总数</div>
                </div>
                """, unsafe_allow_html=True)
            with col_s2:
                unique_sats = len(set(s['satellite'] for s in slips)) if slips else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="color:#f6e05e;">{unique_sats}</div>
                    <div class="metric-label">受影响卫星数</div>
                </div>
                """, unsafe_allow_html=True)
            with col_s3:
                gf_count = len([s for s in slips if 'GF' in s.get('method', '')])
                mw_count = len([s for s in slips if 'MW' in s.get('method', '')])
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="color:#63b3ed;">{gf_count}+{mw_count}</div>
                    <div class="metric-label">GF+MW检出</div>
                </div>
                """, unsafe_allow_html=True)
            
            if slips:
                slips_df = pd.DataFrame(slips)
                st.dataframe(slips_df, use_container_width=True, height=200)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 可视化
    if st.session_state.detected_slips is not None and 'demo_df' in st.session_state:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">📈 GF组合时序图（含周跳标记）</h4>', unsafe_allow_html=True)
        
        demo_df = st.session_state.demo_df
        results = st.session_state.detected_slips
        
        # 选择卫星进行可视化
        sats = sorted(demo_df['satellite'].unique()) if 'satellite' in demo_df.columns else []
        if sats:
            selected_sats = st.multiselect(
                "选择卫星查看", sats, default=sats[:4] if len(sats) >= 4 else sats,
                key='slip_viz_sats'
            )
            
            fig = make_subplots(rows=len(selected_sats), cols=1, 
                               shared_xaxes=True,
                               subplot_titles=[f"卫星 {s}" for s in selected_sats])
            
            for idx, sat in enumerate(selected_sats):
                sat_data = demo_df[demo_df['satellite'] == sat].sort_values('epoch')
                
                # 计算GF值
                if 'L1' in sat_data.columns and 'L2' in sat_data.columns:
                    c = 299792458.0
                    f1, f2 = 1575.42e6, 1227.60e6
                    lambda1, lambda2 = c/f1, c/f2
                    gf_vals = sat_data['L1'].values * lambda1 - sat_data['L2'].values * lambda2
                    
                    row = idx + 1
                    fig.add_trace(
                        go.Scatter(y=gf_vals, mode='lines', name=f'{sat} GF',
                                  line=dict(color='#63b3ed', width=1.5)),
                        row=row, col=1
                    )
                    
                    # 标记周跳
                    sat_slips = [s for s in results.get('slips', []) if s['satellite'] == sat]
                    if sat_slips:
                        slip_indices = [s['index'] for s in sat_slips if s['index'] < len(gf_vals)]
                        slip_values = [gf_vals[i] for i in slip_indices if i < len(gf_vals)]
                        fig.add_trace(
                            go.Scatter(x=slip_indices, y=slip_values, mode='markers',
                                      marker=dict(color='#fc8181', size=10, symbol='x'),
                                      name=f'{sat} 周跳'),
                            row=row, col=1
                        )
            
            fig.update_layout(
                height=200 * len(selected_sats),
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#94a3b8'),
                legend=dict(font=dict(size=9, color='#94a3b8')),
            )
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.08)')
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.08)')
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_coord_converter_page():
    """坐标转换页面"""
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#f6e05e;">🗺️ 坐标转换模块</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">支持BLH ↔ XYZ ↔ UTM全链路转换，多椭球参数</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 转换方向选择
    conv_direction = st.radio(
        "选择转换方向",
        ["BLH → XYZ (大地坐标转地心地固)", "XYZ → BLH (地心地固转大地坐标)",
         "BLH → UTM (大地坐标转UTM投影)", "UTM → BLH (UTM投影转大地坐标)"],
        horizontal=True,
        key='conv_direction'
    )
    
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">📝 输入参数</h4>', unsafe_allow_html=True)
        
        # 椭球选择
        ellipsoid = st.selectbox("选择椭球参数", list(ELLIPSOIDS.keys()), index=0,
                                 format_func=lambda x: ELLIPSOIDS[x]['name'])
        
        # 预设坐标
        presets = {
            '自定义': None,
            '北京 (天安门)': (39.9087, 116.3975, 50),
            '上海 (外滩)': (31.2304, 121.4737, 10),
            '广州 (珠江新城)': (23.1291, 113.2644, 20),
            '成都 (天府广场)': (30.6598, 104.0633, 500),
            '拉萨 (布达拉宫)': (29.6573, 91.1172, 3650),
            '纽约 (时代广场)': (40.7580, -73.9855, 10),
            '伦敦 (大本钟)': (51.5007, -0.1246, 5),
        }
        
        preset_choice = st.selectbox("或选择预设坐标", list(presets.keys()), key='preset_coord')
        
        if 'BLH →' in conv_direction:
            if preset_choice != '自定义' and presets[preset_choice]:
                lat, lon, h = presets[preset_choice]
            else:
                lat = st.number_input("纬度 (°)", value=39.9087, format="%.6f",
                                     help="北纬为正，南纬为负 (-90 ~ 90)")
                lon = st.number_input("经度 (°)", value=116.3975, format="%.6f",
                                     help="东经为正，西经为负 (-180 ~ 180)")
                h = st.number_input("大地高 (m)", value=50.0, format="%.3f")
            
            if 'UTM' not in conv_direction:
                if st.button("🔄 转换 BLH → XYZ", use_container_width=True):
                    X, Y, Z = blh_to_xyz(lat, lon, h, ellipsoid)
                    st.session_state.conv_result = {
                        'type': 'xyz',
                        'X': X, 'Y': Y, 'Z': Z,
                        'input': (lat, lon, h, ellipsoid),
                    }
            else:
                if st.button("🔄 转换 BLH → UTM", use_container_width=True):
                    easting, northing, zone, band, zone_band = blh_to_utm(lat, lon, ellipsoid)
                    st.session_state.conv_result = {
                        'type': 'utm',
                        'easting': easting, 'northing': northing,
                        'zone': zone, 'band': band, 'zone_band': zone_band,
                        'input': (lat, lon, h, ellipsoid),
                    }
        
        elif 'XYZ →' in conv_direction:
            if preset_choice != '自定义' and presets[preset_choice]:
                lat, lon, h = presets[preset_choice]
                X, Y, Z = blh_to_xyz(lat, lon, h, ellipsoid)
                st.info(f"预设坐标转换得到的XYZ: X={X:.3f}, Y={Y:.3f}, Z={Z:.3f}")
            
            X = st.number_input("X (m)", value=-2176842.0, format="%.3f")
            Y = st.number_input("Y (m)", value=4389234.0, format="%.3f")
            Z = st.number_input("Z (m)", value=4070692.0, format="%.3f")
            
            if st.button("🔄 转换 XYZ → BLH", use_container_width=True):
                lat, lon, h = xyz_to_blh(X, Y, Z, ellipsoid)
                st.session_state.conv_result = {
                    'type': 'blh',
                    'lat': lat, 'lon': lon, 'height': h,
                    'input': (X, Y, Z, ellipsoid),
                }
        
        elif 'UTM →' in conv_direction:
            easting = st.number_input("东向 (m)", value=450000.0, format="%.3f")
            northing = st.number_input("北向 (m)", value=4420000.0, format="%.3f")
            zone = st.number_input("UTM带号", value=50, min_value=1, max_value=60)
            band = st.selectbox("纬度带", list('CDEFGHJKLMNPQRSTUVWX'), index=10)
            northern = st.checkbox("北半球", value=True)
            
            if st.button("🔄 转换 UTM → BLH", use_container_width=True):
                lat, lon, h = utm_to_blh(easting, northing, zone, band, ellipsoid, northern)
                st.session_state.conv_result = {
                    'type': 'blh_from_utm',
                    'lat': lat, 'lon': lon, 'height': h,
                    'input': (easting, northing, zone, band, ellipsoid),
                }
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#48bb78;">✅ 转换结果</h4>', unsafe_allow_html=True)
        
        if 'conv_result' in st.session_state and st.session_state.conv_result:
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
                    <p style="color:#64748b; font-size:0.8em; margin-top:12px;">
                    椭球: {ELLIPSOIDS[result['input'][3]]['name']} | 
                    输入: ({result['input'][0]:.6f}°, {result['input'][1]:.6f}°, {result['input'][2]:.3f}m)
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
            elif result['type'] == 'blh':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">大地坐标 (BLH)</h5>
                    <table class="data-table">
                        <tr><td>纬度 (B)</td><td><b>{result['lat']:.8f}°</b></td></tr>
                        <tr><td>经度 (L)</td><td><b>{result['lon']:.8f}°</b></td></tr>
                        <tr><td>大地高 (H)</td><td><b>{result['height']:.4f} m</b></td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
            elif result['type'] == 'utm':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">UTM投影坐标</h5>
                    <table class="data-table">
                        <tr><td>东向 (Easting)</td><td><b>{result['easting']:.3f} m</b></td></tr>
                        <tr><td>北向 (Northing)</td><td><b>{result['northing']:.3f} m</b></td></tr>
                        <tr><td>带号</td><td><b>{result['zone_band']}</b> (Zone {result['zone']}{result['band']})</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
            elif result['type'] == 'blh_from_utm':
                st.markdown(f"""
                <div style="background:rgba(72,187,120,0.1); border-radius:12px; padding:20px;">
                    <h5 style="color:#48bb78;">大地坐标 (从UTM反算)</h5>
                    <table class="data-table">
                        <tr><td>纬度 (B)</td><td><b>{result['lat']:.8f}°</b></td></tr>
                        <tr><td>经度 (L)</td><td><b>{result['lon']:.8f}°</b></td></tr>
                    </table>
                    <p style="color:#64748b; font-size:0.8em; margin-top:12px;">注：UTM不含高程信息</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("👈 输入参数并点击转换按钮查看结果")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 地图显示
    if 'conv_result' in st.session_state and st.session_state.conv_result:
        result = st.session_state.conv_result
        if result['type'] in ['blh', 'blh_from_utm']:
            lat, lon = result['lat'], result['lon']
        elif result['type'] == 'xyz':
            lat, lon, _ = xyz_to_blh(result['X'], result['Y'], result['Z'],
                                      result['input'][3] if len(result['input']) > 3 else 'WGS84')
        elif result['type'] == 'utm':
            lat, lon, _ = utm_to_blh(result['easting'], result['northing'],
                                      result['zone'], result['band'],
                                      result['input'][3] if len(result['input']) > 3 else 'WGS84')
        else:
            lat, lon = 39.9, 116.4
        
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">🗺️ 位置地图</h4>', unsafe_allow_html=True)
        
        map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_df, zoom=10)
        st.markdown('</div>', unsafe_allow_html=True)

def render_skyplot_page():
    """卫星星空图页面（趣味插件）"""
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#b794f4;">🌌 GNSS卫星星空图</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">模拟当前可见卫星在天球上的分布（趣味可视化插件）</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">🎮 参数设置</h4>', unsafe_allow_html=True)
        
        num_sats = st.slider("可见卫星数量", 4, 32, 16, key='skyplot_nsats')
        seed = st.number_input("随机种子", value=42, key='skyplot_seed')
        regen_btn = st.button("🎲 重新生成星空图", use_container_width=True)
        
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:8px; padding:12px; margin-top:12px;">
            <p style="color:#94a3b8; font-size:0.85em;">
            <b>💡 说明：</b>星空图以极坐标展示卫星分布<br>
            • 中心 = 天顶 (90°仰角)<br>
            • 边缘 = 地平线 (0°仰角)<br>
            • 角度 = 方位角 (N=0°, E=90°)<br>
            • 实际使用时需导航文件计算真实位置
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        
        # 生成模拟或真实的卫星分布
        np.random.seed(seed if not regen_btn else int(time.time()))
        
        # 模拟卫星分布（真实情况需要基于导航文件和接收机位置计算）
        azimuths = np.random.uniform(0, 360, num_sats)
        # 仰角分布偏向高仰角（模拟实际观测条件）
        elevations = np.random.beta(1.5, 2, num_sats) * 90
        
        # 为卫星生成标签（混合不同星座）
        constellations = ['G'] * (num_sats // 4) + ['R'] * (num_sats // 4) + \
                        ['E'] * (num_sats // 4) + ['C'] * (num_sats // 4)
        constellations = constellations[:num_sats]
        np.random.shuffle(constellations)
        
        sat_labels = [f"{constellations[i]}{i+1:02d}" for i in range(num_sats)]
        
        fig = generate_skyplot(azimuths, elevations, sat_labels)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 卫星列表
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color:#63b3ed;">📋 卫星方位列表</h4>', unsafe_allow_html=True)
    
    sat_table_data = []
    constellation_names = {'G': 'GPS', 'R': 'GLONASS', 'E': 'Galileo', 'C': '北斗'}
    for i in range(num_sats):
        const = sat_labels[i][0] if i < len(sat_labels) else 'G'
        sat_table_data.append({
            '卫星编号': sat_labels[i] if i < len(sat_labels) else f'G{i+1:02d}',
            '星座': constellation_names.get(const, '未知'),
            '方位角 (°)': round(azimuths[i], 2),
            '仰角 (°)': round(elevations[i], 2),
            '信号状态': '🟢 跟踪中' if elevations[i] > 15 else ('🟡 低仰角' if elevations[i] > 5 else '🔴 即将消失'),
        })
    
    sat_df = pd.DataFrame(sat_table_data)
    st.dataframe(sat_df, use_container_width=True, height=350,
                 column_config={
                     '卫星编号': st.column_config.TextColumn('卫星编号', width='small'),
                     '星座': st.column_config.TextColumn('星座', width='small'),
                     '信号状态': st.column_config.TextColumn('信号状态', width='medium'),
                 })
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_orbit_viewer_page():
    """3D卫星轨道可视化页面（趣味插件）"""
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h2 style="color:#f687b3;">🛰️ 3D卫星轨道可视化</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8;">交互式3D展示GNSS卫星绕地球运行轨迹</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.markdown('<h4 style="color:#63b3ed;">🎮 轨道参数</h4>', unsafe_allow_html=True)
        
        num_sats = st.slider("显示卫星数", 1, 8, 4, key='orbit_nsats')
        orbit_type = st.selectbox("轨道类型", ["GPS (MEO ~20200km)", "GLONASS (MEO ~19100km)",
                                                "Galileo (MEO ~23222km)", "北斗GEO+IGSO+MEO混合"],
                                  key='orbit_type')
        
        st.markdown("""
        <div style="background:rgba(15,23,42,0.6); border-radius:8px; padding:12px; margin-top:12px;">
            <p style="color:#94a3b8; font-size:0.85em;">
            <b>💡 轨道高度参考：</b><br>
            • GPS: 20,200 km<br>
            • GLONASS: 19,100 km<br>
            • Galileo: 23,222 km<br>
            • 北斗GEO: 35,786 km<br>
            • 北斗MEO: 21,528 km
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        regen_orbit_btn = st.button("🔄 重新生成轨道", use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        
        # 生成模拟轨道
        earth_radius = 6371000
        orbit_heights = {
            'GPS (MEO ~20200km)': 20200000,
            'GLONASS (MEO ~19100km)': 19100000,
            'Galileo (MEO ~23222km)': 23222000,
            '北斗GEO+IGSO+MEO混合': 21528000,
        }
        orbit_radius = earth_radius + orbit_heights.get(orbit_type, 20200000)
        
        sat_positions_list = []
        sat_names = []
        
        np.random.seed(int(time.time()) if regen_orbit_btn else 42)
        
        for i in range(num_sats):
            # 随机轨道倾角和升交点
            inclination = np.random.uniform(50, 65) * np.pi / 180
            raan = np.random.uniform(0, 360) * np.pi / 180
            orbit_r = orbit_radius * np.random.uniform(0.92, 1.08)
            
            # 生成轨道点
            num_points = 200
            theta = np.linspace(0, 2*np.pi, num_points)
            
            positions = []
            for t in theta:
                # 轨道平面坐标
                x_orb = orbit_r * np.cos(t)
                y_orb = orbit_r * np.sin(t)
                
                # 旋转到ECEF
                x = x_orb * np.cos(raan) - y_orb * np.cos(inclination) * np.sin(raan)
                y = x_orb * np.sin(raan) + y_orb * np.cos(inclination) * np.cos(raan)
                z = y_orb * np.sin(inclination)
                
                positions.append([x, y, z])
            
            sat_positions_list.append(positions)
            
            constellation = ['G', 'R', 'E', 'C'][i % 4]
            sat_names.append(f"{constellation}{i+1:02d}")
        
        fig = generate_3d_orbit_plot(sat_positions_list, sat_names, earth_radius)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 轨道参数表
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color:#63b3ed;">📊 模拟轨道参数</h4>', unsafe_allow_html=True)
    
    param_data = []
    for i, name in enumerate(sat_names):
        orbit_r = orbit_radius * (0.92 + 0.16 * (i / max(num_sats-1, 1)))
        altitude = orbit_r - earth_radius
        period_min = 2 * np.pi * np.sqrt(orbit_r**3 / 3.986005e14) / 60
        
        param_data.append({
            '卫星': name,
            '轨道半径 (km)': round(orbit_r / 1000, 1),
            '高度 (km)': round(altitude / 1000, 1),
            '轨道周期 (min)': round(period_min, 1),
            '倾角 (°)': round(np.random.uniform(50, 65), 1),
        })
    
    param_df = pd.DataFrame(param_data)
    st.dataframe(param_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== 主程序 ====================
def main():
    """主程序入口"""
    
    # 开场动画
    if not st.session_state.animation_shown:
        show_intro_animation()
        return
    
    # 渲染侧边栏
    render_sidebar()
    
    # 根据当前页面渲染内容
    current_page = st.session_state.current_page
    
    if current_page == 'home':
        render_home_page()
    elif current_page == 'data_reader':
        render_data_reader_page()
    elif current_page == 'slip_detector':
        render_slip_detector_page()
    elif current_page == 'coord_converter':
        render_coord_converter_page()
    elif current_page == 'skyplot':
        render_skyplot_page()
    elif current_page == 'orbit_viewer':
        render_orbit_viewer_page()
    else:
        render_home_page()

if __name__ == "__main__":
    main()