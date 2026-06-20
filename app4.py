#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkyTracker Pro - GNSS数据处理平台（修复版）
功能：RINEX数据读取、周跳探测、坐标转换、卫星星空图、3D轨道可视化
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
from typing import List, Dict, Optional

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="SkyTracker Pro",
    page_icon="🛰️",
    layout="wide",
)

# ==================== 简洁CSS ====================
st.markdown("""
<style>
    .stApp { background: #0f172a; color: #e2e8f0; }
    .main-card {
        background: rgba(30,41,59,0.8); border: 1px solid rgba(99,179,237,0.2);
        border-radius: 12px; padding: 20px; margin: 10px 0;
    }
    .glow-text { color: #63b3ed; font-weight: 700; }
    .metric-box {
        background: rgba(15,23,42,0.7); border-radius: 10px; padding: 16px; text-align: center;
    }
    .stButton>button {
        background: #1e3a5f; color: #63b3ed; border: 1px solid rgba(99,179,237,0.3);
        border-radius: 8px; transition: 0.3s;
    }
    .stButton>button:hover { background: #2a4a7f; border-color: #63b3ed; color: white; }
    .toast {
        background: rgba(72,187,120,0.15); border: 1px solid #48bb78; border-radius: 8px;
        padding: 8px 16px; color: #48bb78;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 会话状态 ====================
for key, default in [
    ('animation_shown', False), ('current_page', 'home'),
    ('rinex_data', None), ('nav_data', None), ('detected_slips', None),
    ('conv_result', None), ('demo_df', None), ('injected_slips', None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== 椭球参数 ====================
ELLIPSOIDS = {
    'WGS84': {'a': 6378137.0, 'f': 1/298.257223563, 'name': 'WGS84 (GPS)'},
    'CGCS2000': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'CGCS2000 (北斗)'},
    'PZ90': {'a': 6378136.0, 'f': 1/298.25784, 'name': 'PZ-90 (GLONASS)'},
    'GRS80': {'a': 6378137.0, 'f': 1/298.257222101, 'name': 'GRS80'},
}

# ==================== 开场动画（简化） ====================
def show_intro_animation():
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("""
            <div style="text-align:center;">
                <h1 class="glow-text">🛰️ SkyTracker Pro</h1>
                <p style="color:#94a3b8;">GNSS卫星导航数据处理平台</p>
                <p style="color:#64748b;">📡 RINEX解析 · 🔍 周跳探测 · 🗺️ 坐标转换</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚀 进入平台", use_container_width=True):
                st.session_state.animation_shown = True
                st.rerun()
        time.sleep(4)
        st.session_state.animation_shown = True
        st.rerun()

# ==================== 坐标转换 ====================
def blh_to_xyz(lat_deg, lon_deg, height, ellipsoid='WGS84'):
    ell = ELLIPSOIDS[ellipsoid]; a = ell['a']; f = ell['f']
    e2 = 2*f - f**2
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    sin_lat = math.sin(lat); cos_lat = math.cos(lat)
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    X = (N + height) * cos_lat * math.cos(lon)
    Y = (N + height) * cos_lat * math.sin(lon)
    Z = (N * (1 - e2) + height) * sin_lat
    return X, Y, Z

def xyz_to_blh(X, Y, Z, ellipsoid='WGS84', max_iter=10, tol=1e-12):
    ell = ELLIPSOIDS[ellipsoid]; a = ell['a']; f = ell['f']
    e2 = 2*f - f**2
    lon = math.degrees(math.atan2(Y, X))
    p = math.sqrt(X**2 + Y**2)
    lat = math.atan2(Z, p * (1 - e2))
    for _ in range(max_iter):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1 - e2 * sin_lat**2)
        h = p / math.cos(lat) - N
        lat_new = math.atan2(Z, p * (1 - e2 * N / (N + h)))
        if abs(lat_new - lat) < tol: lat = lat_new; break
        lat = lat_new
    sin_lat = math.sin(lat)
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    height = p / math.cos(lat) - N
    return math.degrees(lat), lon, height

def blh_to_utm(lat_deg, lon_deg, ellipsoid='WGS84'):
    ell = ELLIPSOIDS[ellipsoid]; a = ell['a']; f = ell['f']
    e2 = 2*f - f**2; e2p = e2/(1-e2)
    lat = math.radians(lat_deg); lon = math.radians(lon_deg)
    zone = int((lon_deg + 180) / 6) + 1
    # 挪威/斯瓦尔巴特例略
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    sin_lat = math.sin(lat); cos_lat = math.cos(lat); tan_lat = math.tan(lat)
    N = a / math.sqrt(1 - e2 * sin_lat**2)
    T = tan_lat**2; C = e2p * cos_lat**2
    A = (lon - lon0) * cos_lat
    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat
             - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*lat)
             + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*lat)
             - (35*e2**3/3072) * math.sin(6*lat))
    k0 = 0.9996
    easting = k0 * N * (A + (1-T+C)*A**3/6 + (5-18*T+T**2+72*C-58*e2p)*A**5/120) + 500000
    northing = k0 * (M + N * tan_lat * (A**2/2 + (5-T+9*C+4*C**2)*A**4/24 + (61-58*T+T**2+600*C-330*e2p)*A**6/720))
    if lat_deg < 0: northing += 10000000
    # 纬度带字母略（简化为返回）
    bands = 'CDEFGHJKLMNPQRSTUVWX'
    idx = int((lat_deg + 80) // 8)
    band = bands[idx] if 0 <= idx < len(bands) else 'Z'
    return easting, northing, zone, band, f"{zone}{band}"

def utm_to_blh(easting, northing, zone, band, ellipsoid='WGS84', northern=True):
    ell = ELLIPSOIDS[ellipsoid]; a = ell['a']; f = ell['f']
    e2 = 2*f - f**2; e2p = e2/(1-e2)
    k0 = 0.9996
    x = easting - 500000
    y = northing - (0 if northern else 10000000)
    M = y / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    e1 = (1 - math.sqrt(1-e2)) / (1 + math.sqrt(1-e2))
    lat = mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu) + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu) \
          + (151*e1**3/96)*math.sin(6*mu) + (1097*e1**4/512)*math.sin(8*mu)
    sin_lat = math.sin(lat); cos_lat = math.cos(lat); tan_lat = math.tan(lat)
    N = a / math.sqrt(1 - e2*sin_lat**2)
    T = tan_lat**2; C = e2p * cos_lat**2
    D = x / (N * k0)
    lat = lat - (N*tan_lat/(a*(1-e2))) * (D**2/2 - (5+3*T+10*C-4*C**2-9*e2p)*D**4/24)
    lon0 = math.radians((zone - 1)*6 - 180 + 3)
    lon = lon0 + (D - (1+2*T+C)*D**3/6 + (5-2*C+28*T-3*C**2+8*e2p+24*T**2)*D**5/120) / cos_lat
    return math.degrees(lat), math.degrees(lon), 0.0

# ==================== RINEX解析 ====================
class RinexParser:
    @staticmethod
    def parse_obs_header(lines):
        header = {'version':'2.11','obs_types':[],'num_obs':0,'approx_pos':[0,0,0]}
        for line in lines:
            label = line[60:].strip()
            if 'RINEX VERSION' in label: header['version'] = line[:20].strip()
            elif '# / TYPES OF OBSERV' in label:
                header['num_obs'] = int(line[:6])
                header['obs_types'] = line[6:60].strip().split()
            elif 'APPROX POSITION XYZ' in label:
                parts = line[:60].strip().split()
                if len(parts)>=3: header['approx_pos'] = [float(p) for p in parts[:3]]
            elif 'END OF HEADER' in label: break
        return header

    @staticmethod
    def parse_obs_data(lines, header):
        records = []
        data_lines = lines[lines.index(next(l for l in lines if 'END OF HEADER' in l))+1:]
        i = 0; ntypes = header['num_obs']; obs_types = header['obs_types'][:ntypes]
        while i < len(data_lines):
            line = data_lines[i]
            if len(line) < 30: i+=1; continue
            try:
                yr = int(line[:3]); yr += 1900 if yr>=80 else 2000
                mo, dy, hr, mi = int(line[3:6]), int(line[6:9]), int(line[9:12]), int(line[12:15])
                sec = float(line[15:26])
                epoch = datetime(yr, mo, dy, hr, mi, int(sec), int((sec-int(sec))*1e6))
                flag = int(line[28:29]) if len(line)>28 else 0
                nsat = int(line[29:32]) if len(line)>29 else 0
                sats_str = line[32:].strip()
                sat_ids = [sats_str[j:j+3].strip() for j in range(0, len(sats_str), 3) if sats_str[j:j+3].strip()]
                # 处理可能续行
                while len(sat_ids) < nsat:
                    i+=1; extra = data_lines[i].strip()
                    sat_ids += [extra[j:j+3].strip() for j in range(0, len(extra), 3) if extra[j:j+3].strip()]
                i+=1
                for sat in sat_ids[:nsat]:
                    if i >= len(data_lines): break
                    obs_line = data_lines[i]
                    vals = []; rem = ntypes
                    while rem > 0:
                        take = min(rem, 5)
                        for k in range(take):
                            s = obs_line[k*14:(k+1)*14].strip()
                            vals.append(float(s) if s else np.nan)
                        rem -= take
                        if rem > 0: i+=1; obs_line = data_lines[i]
                    rec = {'epoch':epoch, 'satellite':sat, 'epoch_flag':flag}
                    for k, ot in enumerate(obs_types):
                        rec[ot] = vals[k] if k < len(vals) else np.nan
                    records.append(rec)
                    i+=1
            except: i+=1
        return pd.DataFrame(records)

    @staticmethod
    def parse_nav_header(lines):
        header = {'version':'2.11','ion_alpha':[0]*4,'ion_beta':[0]*4}
        for line in lines:
            label = line[60:].strip()
            if 'ION ALPHA' in label:
                header['ion_alpha'] = [float(p.replace('D','E')) for p in line[:60].split()[:4]]
            elif 'ION BETA' in label:
                header['ion_beta'] = [float(p.replace('D','E')) for p in line[:60].split()[:4]]
            elif 'END OF HEADER' in label: break
        return header

    @staticmethod
    def parse_nav_data(lines, header):
        records = []
        data_lines = lines[lines.index(next(l for l in lines if 'END OF HEADER' in l))+1:]
        i = 0
        while i < len(data_lines)-7:
            try:
                line = data_lines[i]
                if len(line) < 22: i+=1; continue
                prn = line[:3].strip()
                yr = int(line[3:6]); yr += 1900 if yr>=80 else 2000
                mo, dy, hr, mi = int(line[6:9]), int(line[9:12]), int(line[12:15]), int(line[15:18])
                sec = float(line[18:22])
                toc = datetime(yr, mo, dy, hr, mi, int(sec))
                rec = {'satellite':prn, 'toc':toc,
                       'af0':float(line[22:41].replace('D','E')),
                       'af1':float(line[41:60].replace('D','E'))}
                i+=1; l2 = data_lines[i]
                rec['af2'] = float(l2[:19].replace('D','E'))
                rec['crs'] = float(l2[19:38].replace('D','E'))
                rec['delta_n'] = float(l2[38:57].replace('D','E'))
                rec['M0'] = float(l2[57:76].replace('D','E')) if len(l2)>57 else 0
                i+=1; l3 = data_lines[i]
                rec['cuc'] = float(l3[:19].replace('D','E'))
                rec['ecc'] = float(l3[19:38].replace('D','E'))
                rec['cus'] = float(l3[38:57].replace('D','E'))
                rec['sqrt_a'] = float(l3[57:76].replace('D','E')) if len(l3)>57 else 0
                i+=1; l4 = data_lines[i]
                rec['toe'] = float(l4[:19].replace('D','E'))
                rec['cic'] = float(l4[19:38].replace('D','E'))
                rec['OMEGA0'] = float(l4[38:57].replace('D','E'))
                rec['cis'] = float(l4[57:76].replace('D','E')) if len(l4)>57 else 0
                i+=1; l5 = data_lines[i]
                rec['i0'] = float(l5[:19].replace('D','E'))
                rec['crc'] = float(l5[19:38].replace('D','E'))
                rec['omega'] = float(l5[38:57].replace('D','E'))
                rec['OMEGA_DOT'] = float(l5[57:76].replace('D','E')) if len(l5)>57 else 0
                i+=1; l6 = data_lines[i]
                rec['i_dot'] = float(l6[:19].replace('D','E'))
                i+=1; l7 = data_lines[i]
                rec['week_num'] = int(float(l7[:19].replace('D','E'))) if l7[:19].strip() else 0
                records.append(rec)
                i+=1
            except: i+=1
        return pd.DataFrame(records)

# ==================== 周跳探测 ====================
class CycleSlipDetector:
    @staticmethod
    def gf_combination(L1, L2, f1=1575.42e6, f2=1227.60e6, th=0.05):
        c = 299792458.0; lam1 = c/f1; lam2 = c/f2
        gf = L1*lam1 - L2*lam2
        diff = np.abs(np.diff(gf, prepend=gf[0]))
        slips = np.where(diff > th)[0]
        return gf, slips

    @staticmethod
    def mw_combination(L1, L2, P1, P2, f1=1575.42e6, f2=1227.60e6, th=2.0):
        c = 299792458.0; lam_w = c/(f1-f2)
        mw = (f1*L1*c/f1 - f2*L2*c/f2)/(f1-f2)/lam_w - (f1*P1 + f2*P2)/(f1+f2)/lam_w
        slips = []
        if len(mw) > 10:
            for i in range(10, len(mw)):
                win = mw[i-10:i]
                mu, std = np.nanmean(win), np.nanstd(win)
                if std > 0 and abs(mw[i]-mu) > th*std:
                    slips.append(i)
        return mw, np.array(slips)

    @staticmethod
    def detect_all(df, f1=1575.42e6, f2=1227.60e6):
        results = {'slips':[]}
        l1c = [c for c in df.columns if 'L1' in c.upper() or 'C1' in c.upper()]
        l2c = [c for c in df.columns if 'L2' in c.upper()]
        p1c = [c for c in df.columns if 'P1' in c.upper() or 'C1' in c.upper()]
        p2c = [c for c in df.columns if 'P2' in c.upper()]
        if not l1c or not l2c: return results
        l1_col, l2_col = l1c[0], l2c[0]
        for sat in df['satellite'].unique():
            sdf = df[df['satellite']==sat].sort_values('epoch')
            l1 = sdf[l1_col].values; l2 = sdf[l2_col].values
            mask = ~(np.isnan(l1) | np.isnan(l2))
            if mask.sum() < 5: continue
            l1v, l2v = l1[mask], l2[mask]; idx = np.where(mask)[0]
            gf, gs = CycleSlipDetector.gf_combination(l1v, l2v, f1, f2)
            for s in gs:
                if s < len(idx):
                    results['slips'].append({
                        'satellite':sat, 'epoch':sdf.iloc[idx[s]]['epoch'],
                        'method':'GF','gf_value':gf[s]
                    })
            if p1c and p2c:
                p1v = sdf[p1c[0]].values[mask]; p2v = sdf[p2c[0]].values[mask]
                if len(p1v)==len(l1v):
                    mw, ms = CycleSlipDetector.mw_combination(l1v, l2v, p1v, p2v, f1, f2)
                    for s in ms:
                        if s < len(idx):
                            results['slips'].append({
                                'satellite':sat, 'epoch':sdf.iloc[idx[s]]['epoch'],
                                'method':'MW','mw_value':mw[s]
                            })
        return results

# ==================== 模拟数据 ====================
def generate_demo_obs(epochs=120, sats=8, slip_epochs=[25,55,78]):
    np.random.seed(42)
    base_time = datetime(2024,6,21,10,0,0)
    data = []
    for i in range(epochs):
        t = base_time + timedelta(seconds=30*i)
        for s in range(sats):
            l1 = 1e7 + s*1e5 + i*5000 + np.random.normal(0,0.01)
            l2 = 8e6 + s*8e4 + i*3900 + np.random.normal(0,0.012)
            if i in slip_epochs and s in [1,3,5]:
                l1 += np.random.choice([-15,12,20])
                l2 += np.random.choice([-10,8])
            p1 = 2.1e7 + s*2e5 + i*5000 + np.random.normal(0,0.5)
            p2 = 2.1e7 + s*2e5 + i*5000 + np.random.normal(0,0.6)
            data.append({'epoch':t, 'satellite':f'G{s+1:02d}', 'L1':l1, 'L2':l2, 'P1':p1, 'P2':p2})
    return pd.DataFrame(data)

# ==================== 星空图（修复版） ====================
def generate_skyplot(azimuths, elevations, labels):
    fig = go.Figure()
    # 同心圆
    for el in [0, 30, 60]:
        r = 90 - el
        theta = np.linspace(0, 360, 200)
        fig.add_trace(go.Scatterpolar(
            r=[r]*200, theta=theta, mode='lines',
            line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='none'))
    # 卫星点
    colors = ['#63b3ed','#48bb78','#f6e05e','#fc8181','#b794f4','#f687b3']
    for i, (az, el, lab) in enumerate(zip(azimuths, elevations, labels)):
        r = 90 - el
        theta = (90 - az) % 360
        fig.add_trace(go.Scatterpolar(
            r=[r], theta=[theta], mode='markers+text',
            marker=dict(size=14, color=colors[i%6], line=dict(color='white',width=1.5)),
            text=lab, textposition='top center', textfont=dict(size=9, color='white'),
            name=lab, hovertemplate=f'<b>{lab}</b><br>方位:{az:.1f}°<br>仰角:{el:.1f}°'))
    # 方向标记
    for d, ang in [('N',0),('E',90),('S',180),('W',270)]:
        fig.add_trace(go.Scatterpolar(r=[95], theta=[ang], mode='text',
            text=[d], textfont=dict(size=14,color='white'), showlegend=False, hoverinfo='none'))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0,95], visible=False, showticklabels=False),
            angularaxis=dict(tickmode='array', tickvals=list(range(0,360,30)),
                             ticktext=[f'{x}°' for x in range(0,360,30)],
                             tickfont=dict(size=9, color='#94a3b8'),
                             gridcolor='rgba(255,255,255,0.1)',
                             rotation=90, direction='clockwise')),
        showlegend=True, height=500,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(size=10,color='#94a3b8')))
    return fig

# ==================== 3D轨道图 ====================
def generate_3d_orbit(sat_positions, sat_names):
    fig = go.Figure()
    R = 6371000
    u, v = np.linspace(0,2*np.pi,60), np.linspace(0,np.pi,40)
    x = R * np.outer(np.cos(u), np.sin(v))
    y = R * np.outer(np.sin(u), np.sin(v))
    z = R * np.outer(np.ones(np.size(u)), np.cos(v))
    fig.add_trace(go.Surface(x=x, y=y, z=z, colorscale=[[0,'#1a3a5c'],[0.5,'#2980b9'],[1,'#0d2137']],
                             showscale=False, opacity=0.85, hoverinfo='none'))
    colors = ['#63b3ed','#48bb78','#f6e05e','#fc8181','#b794f4','#f687b3']
    for i, (pos, name) in enumerate(zip(sat_positions, sat_names)):
        arr = np.array(pos)
        fig.add_trace(go.Scatter3d(x=arr[:,0], y=arr[:,1], z=arr[:,2],
                                   mode='lines+markers', line=dict(color=colors[i%6],width=2),
                                   marker=dict(size=2), name=name))
    fig.update_layout(
        scene=dict(xaxis=dict(range=[-1.6*R,1.6*R]), yaxis=dict(range=[-1.6*R,1.6*R]),
                   zaxis=dict(range=[-1.6*R,1.6*R]), aspectmode='cube',
                   bgcolor='rgba(0,0,0,0)'),
        height=600, paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(size=10,color='#94a3b8')))
    return fig

# ==================== 页面渲染 ====================
def sidebar():
    with st.sidebar:
        st.markdown("## 🛰️ SkyTracker Pro")
        pages = {
            'home':'🏠 首页总览', 'data_reader':'📡 数据读取',
            'slip_detector':'🔍 周跳探测', 'coord_converter':'🗺️ 坐标转换',
            'skyplot':'🌌 卫星星空图', 'orbit_viewer':'🛰️ 3D轨道可视化'}
        for k,v in pages.items():
            if st.button(v, use_container_width=True, key=f'nav_{k}'):
                st.session_state.current_page = k; st.rerun()
        st.markdown("---")
        st.caption(f"📍 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def home_page():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<h1 class='glow-text'>🛰️ SkyTracker Pro</h1>", unsafe_allow_html=True)
    st.markdown("专业GNSS数据处理平台 · RINEX解析 · 周跳探测 · 坐标转换 · 可视化", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    for col, (icon, title, desc) in zip([col1,col2,col3,col4], [
        ('📡','RINEX解析','2.x / 3.x'), ('🔍','周跳探测','GF+MW组合'),
        ('🗺️','坐标转换','BLH/XYZ/UTM'), ('🌌','可视化','星空图+3D')]):
        with col: st.markdown(f"<div class='metric-box'><b>{icon}</b><br>{title}<br><small>{desc}</small></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📡 数据读取", use_container_width=True): st.session_state.current_page='data_reader'; st.rerun()
    with col2:
        if st.button("🔍 周跳探测", use_container_width=True): st.session_state.current_page='slip_detector'; st.rerun()
    with col3:
        if st.button("🗺️ 坐标转换", use_container_width=True): st.session_state.current_page='coord_converter'; st.rerun()

def data_reader_page():
    st.markdown('<div class="main-card"><h3>📡 数据读取</h3></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📂 上传与解析", "📊 数据预览"])
    with tab1:
        obs_file = st.file_uploader("RINEX观测文件", type=['obs','rnx','o','txt'], key='obs')
        nav_file = st.file_uploader("RINEX导航文件", type=['nav','n','sp3','txt'], key='nav')
        if obs_file:
            content = obs_file.read().decode('utf-8','replace').split('\n')
            header = RinexParser.parse_obs_header(content)
            df = RinexParser.parse_obs_data(content, header)
            st.session_state.rinex_data = {'header':header, 'df':df}
            st.markdown(f"<div class='toast'>✅ 解析成功：{len(df)}条记录，{df['satellite'].nunique()}颗卫星</div>", unsafe_allow_html=True)
        if nav_file:
            content = nav_file.read().decode('utf-8','replace').split('\n')
            header = RinexParser.parse_nav_header(content)
            df = RinexParser.parse_nav_data(content, header)
            st.session_state.nav_data = {'header':header, 'df':df}
            st.markdown(f"<div class='toast'>✅ 导航文件解析：{len(df)}条星历</div>", unsafe_allow_html=True)
    with tab2:
        if st.session_state.rinex_data:
            df = st.session_state.rinex_data['df'].head(50)
            st.dataframe(df, use_container_width=True)
        else: st.info("请先上传观测文件")

def slip_detector_page():
    st.markdown('<div class="main-card"><h3>🔍 周跳探测</h3></div>', unsafe_allow_html=True)
    use_demo = st.checkbox("使用演示数据", True)
    if st.button("开始探测", use_container_width=True):
        if use_demo:
            df = generate_demo_obs()
            st.session_state.demo_df = df
            results = CycleSlipDetector.detect_all(df)
        elif st.session_state.rinex_data:
            df = st.session_state.rinex_data['df']
            st.session_state.demo_df = df
            results = CycleSlipDetector.detect_all(df)
        else: results = None
        if results:
            st.session_state.detected_slips = results
            slips = results['slips']
            st.success(f"检测到 {len(slips)} 处疑似周跳")
            if slips:
                st.dataframe(pd.DataFrame(slips))
    # 可视化GF时序
    if st.session_state.detected_slips and 'demo_df' in st.session_state:
        df = st.session_state.demo_df
        sats = sorted(df['satellite'].unique())[:4]
        fig = make_subplots(rows=len(sats), cols=1, shared_xaxes=True,
                            subplot_titles=[f'SAT {s}' for s in sats])
        c=299792458.0; lam1=c/1575.42e6; lam2=c/1227.60e6
        for i, sat in enumerate(sats):
            sdf = df[df['satellite']==sat].sort_values('epoch')
            gf = sdf['L1']*lam1 - sdf['L2']*lam2
            fig.add_trace(go.Scatter(y=gf, mode='lines', name=f'{sat} GF'), row=i+1, col=1)
            # 标记周跳
            slips_idx = [s['index'] for s in st.session_state.detected_slips['slips'] if s['satellite']==sat and s['index']<len(gf)]
            if slips_idx:
                fig.add_trace(go.Scatter(x=slips_idx, y=[gf.iloc[j] for j in slips_idx],
                                         mode='markers', marker=dict(color='red',size=8,symbol='x'),
                                         name=f'{sat} slip'), row=i+1, col=1)
        fig.update_layout(height=200*len(sats), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

def coord_converter_page():
    st.markdown('<div class="main-card"><h3>🗺️ 坐标转换</h3></div>', unsafe_allow_html=True)
    direction = st.radio("转换方向", ["BLH→XYZ", "XYZ→BLH", "BLH→UTM", "UTM→BLH"], horizontal=True)
    ell = st.selectbox("椭球", list(ELLIPSOIDS.keys()), format_func=lambda x:ELLIPSOIDS[x]['name'])
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**输入**")
        if 'BLH→' in direction:
            lat = st.number_input("纬度°", 39.9, format="%.6f"); lon = st.number_input("经度°", 116.4, format="%.6f")
            h = st.number_input("大地高m", 50.0, format="%.2f")
            if st.button("转换", use_container_width=True):
                if direction=='BLH→XYZ':
                    X,Y,Z = blh_to_xyz(lat,lon,h,ell)
                    st.session_state.conv_result = {'type':'xyz','X':X,'Y':Y,'Z':Z}
                else:
                    e,n,z,b,zb = blh_to_utm(lat,lon,ell)
                    st.session_state.conv_result = {'type':'utm','easting':e,'northing':n,'zone_band':zb}
        elif 'XYZ→' in direction:
            X = st.number_input("X m", -2176842.0); Y = st.number_input("Y m", 4389234.0); Z = st.number_input("Z m", 4070692.0)
            if st.button("转换", use_container_width=True):
                lat,lon,h = xyz_to_blh(X,Y,Z,ell)
                st.session_state.conv_result = {'type':'blh','lat':lat,'lon':lon,'height':h}
        else:
            east = st.number_input("东向m", 450000.0); north = st.number_input("北向m", 4420000.0)
            zone = st.number_input("带号", 50,1,60); band = st.selectbox("纬度带", list('CDEFGHJKLMNPQRSTUVWX'), index=10)
            north_hemi = st.checkbox("北半球", True)
            if st.button("转换", use_container_width=True):
                lat,lon,h = utm_to_blh(east,north,zone,band,ell,north_hemi)
                st.session_state.conv_result = {'type':'blh','lat':lat,'lon':lon,'height':0}
    with col2:
        st.markdown("**结果**")
        if st.session_state.conv_result:
            res = st.session_state.conv_result
            if res['type']=='xyz':
                st.write(f"X: {res['X']:.4f} m"); st.write(f"Y: {res['Y']:.4f} m"); st.write(f"Z: {res['Z']:.4f} m")
            elif res['type']=='utm':
                st.write(f"Easting: {res['easting']:.3f} m"); st.write(f"Northing: {res['northing']:.3f} m")
                st.write(f"Zone: {res['zone_band']}")
            elif res['type']=='blh':
                st.write(f"纬度: {res['lat']:.8f}°"); st.write(f"经度: {res['lon']:.8f}°")
                st.write(f"大地高: {res['height']:.3f} m")
            # 地图
            if res['type']=='blh': lat, lon = res['lat'], res['lon']
            elif res['type']=='xyz': lat,lon,_ = xyz_to_blh(res['X'],res['Y'],res['Z'],'WGS84')
            else: lat,lon = 39.9,116.4
            st.map(pd.DataFrame({'lat':[lat],'lon':[lon]}), zoom=10)

def skyplot_page():
    st.markdown('<div class="main-card"><h3>🌌 GNSS卫星星空图</h3></div>', unsafe_allow_html=True)
    num = st.slider("卫星数量", 4, 32, 16)
    if st.button("生成星空图"):
        np.random.seed(int(time.time()))
        az = np.random.uniform(0,360,num)
        el = np.random.beta(1.5,2,num)*90
        labels = [f"{['G','R','E','C'][i%4]}{i+1:02d}" for i in range(num)]
        fig = generate_skyplot(az, el, labels)
        st.plotly_chart(fig, use_container_width=True)
        # 列表
        data = []
        for i in range(num):
            data.append({'卫星':labels[i], '方位角':round(az[i],1), '仰角':round(el[i],1),
                         '状态':'🟢' if el[i]>15 else '🟡'})
        st.dataframe(pd.DataFrame(data), use_container_width=True)

def orbit_viewer_page():
    st.markdown('<div class="main-card"><h3>🛰️ 3D轨道可视化</h3></div>', unsafe_allow_html=True)
    n_sats = st.slider("卫星数", 1, 6, 3)
    if st.button("生成轨道"):
        R = 6371000; heights = {'GPS':20200000,'GLONASS':19100000,'Galileo':23222000,'北斗':21528000}
        orbit_r = R + heights['GPS']
        positions = []
        names = []
        np.random.seed(int(time.time()))
        for i in range(n_sats):
            inc = np.random.uniform(50,65)*np.pi/180
            raan = np.random.uniform(0,360)*np.pi/180
            r = orbit_r * np.random.uniform(0.9,1.1)
            theta = np.linspace(0,2*np.pi,200)
            pos = []
            for t in theta:
                x_orb = r*np.cos(t); y_orb = r*np.sin(t)
                x = x_orb*np.cos(raan) - y_orb*np.cos(inc)*np.sin(raan)
                y = x_orb*np.sin(raan) + y_orb*np.cos(inc)*np.cos(raan)
                z = y_orb*np.sin(inc)
                pos.append([x,y,z])
            positions.append(pos)
            names.append(f"{['G','R','E','C'][i%4]}{i+1:02d}")
        fig = generate_3d_orbit(positions, names)
        st.plotly_chart(fig, use_container_width=True)

# ==================== 主程序 ====================
def main():
    if not st.session_state.animation_shown:
        show_intro_animation()
        return
    sidebar()
    page = st.session_state.current_page
    if page == 'home': home_page()
    elif page == 'data_reader': data_reader_page()
    elif page == 'slip_detector': slip_detector_page()
    elif page == 'coord_converter': coord_converter_page()
    elif page == 'skyplot': skyplot_page()
    elif page == 'orbit_viewer': orbit_viewer_page()
    else: home_page()

if __name__ == "__main__":
    main()