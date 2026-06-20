import streamlit as st
import time
import random
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="GNSS-SAT 智能分析平台",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 开场动画（仅在首次加载时显示）
# ============================================================
if "startup_done" not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(
            """
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh;">
                <div style="font-size: 80px; animation: spin 2s linear infinite;">🛰️</div>
                <h1 style="color: #3b6aff;">GNSS-SAT 智能分析平台</h1>
                <p style="color: #7a8bb5;">正在初始化卫星链路...</p>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </div>
            """,
            unsafe_allow_html=True
        )
    time.sleep(2)
    placeholder.empty()
    st.session_state.startup_done = True

# ============================================================
# 数据生成器（模拟 GNSS 观测数据）
# ============================================================
def generate_mock_data(seed=None):
    if seed is not None:
        random.seed(seed)
    systems = ['GPS', 'GLONASS', 'Galileo', '北斗']
    sys_colors = {
        'GPS': '#4a6cff',
        'GLONASS': '#34d399',
        'Galileo': '#fbbf24',
        '北斗': '#f472b6'
    }
    satellites = []
    total = random.randint(28, 36)
    sys_counts = {
        'GPS': random.randint(8, 12),
        'GLONASS': random.randint(6, 9),
        'Galileo': random.randint(5, 8),
        '北斗': random.randint(5, 8)
    }
    # 调整总数
    diff = total - sum(sys_counts.values())
    if diff > 0:
        sys_counts['GPS'] += diff
    elif diff < 0:
        for key in list(sys_counts.keys()):
            if diff < 0:
                reduce = min(sys_counts[key], -diff)
                sys_counts[key] -= reduce
                diff += reduce

    sat_id = 1
    for sys, cnt in sys_counts.items():
        for _ in range(cnt):
            prn_num = random.randint(1, 40)
            prn = f"{sys}{prn_num:02d}"
            elevation = random.uniform(5, 85)
            azimuth = random.uniform(0, 360)
            snr = random.uniform(30, 55)
            quality = min(1.0, max(0.2, (snr - 28) / 30))
            satellites.append({
                'id': sat_id,
                'system': sys,
                'prn': prn,
                'elevation': elevation,
                'azimuth': azimuth,
                'snr': snr,
                'quality': quality,
                'color': sys_colors.get(sys, '#a78bfa')
            })
            sat_id += 1

    random.shuffle(satellites)
    epochs = random.randint(120, 300)
    interval = random.choice([5, 10, 15, 30, 60])
    completeness = round(random.uniform(85, 99), 1)
    data_size = f"{random.uniform(1.5, 8):.1f} MB"
    formats = ['RINEX 3.04', 'GNS', 'CRX'][:random.randint(2, 4)]

    return {
        'satellites': satellites,
        'epochs': epochs,
        'interval': interval,
        'completeness': completeness,
        'systems': [s for s, c in sys_counts.items() if c > 0],
        'sys_counts': sys_counts,
        'total_satellites': len(satellites),
        'data_size': data_size,
        'formats': formats
    }

# ============================================================
# 绘图函数
# ============================================================
def plot_sky_map(satellites):
    """绘制卫星星空极坐标散点图"""
    if not satellites:
        fig = go.Figure()
        fig.update_layout(
            polar=dict(
                radialaxis=dict(range=[0, 90], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            annotations=[dict(text="等待数据...", x=0.5, y=0.5, showarrow=False, font=dict(size=20))]
        )
        return fig

    df = pd.DataFrame(satellites)
    fig = go.Figure()
    # 按系统分组
    for sys in df['system'].unique():
        subset = df[df['system'] == sys]
        fig.add_trace(go.Scatterpolar(
            r=subset['elevation'],
            theta=subset['azimuth'],
            mode='markers',
            marker=dict(
                size=8 + subset['quality'] * 6,
                color=subset['color'],
                opacity=0.8,
                line=dict(width=0.5, color='white')
            ),
            text=subset['prn'],
            name=sys,
            hovertemplate='<b>%{text}</b><br>仰角: %{r:.1f}°<br>方位: %{theta:.1f}°<br>SNR: %{marker.size:.1f} dBHz<extra></extra>'
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 90], tickangle=0, tickfont=dict(size=10)),
            angularaxis=dict(direction="clockwise", tickfont=dict(size=10))
        ),
        showlegend=True,
        height=500,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def plot_heatmap(satellites):
    """信号质量热力图（取前36颗卫星）"""
    if not satellites:
        fig = go.Figure()
        fig.add_annotation(text="暂无信号数据", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=250)
        return fig

    df = pd.DataFrame(satellites[:36])
    # 准备网格数据：按系统分组，用SNR作为值
    # 为了展示热力图，我们简单地将卫星排成6x6网格
    n = len(df)
    rows = 6
    cols = 6
    values = np.full((rows, cols), np.nan)
    texts = np.empty((rows, cols), dtype=object)
    for i, (_, row) in enumerate(df.iterrows()):
        r = i // cols
        c = i % cols
        if r < rows and c < cols:
            values[r, c] = row['snr']
            texts[r, c] = f"{row['prn']}<br>SNR: {row['snr']:.1f}"

    fig = go.Figure(data=go.Heatmap(
        z=values,
        text=texts,
        hoverinfo='text',
        colorscale='RdYlGn',
        zmin=30,
        zmax=55,
        showscale=False,
        xgap=2,
        ygap=2
    ))
    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False)
    )
    return fig

def plot_system_bars(sys_counts):
    """多系统卫星数量条形图"""
    if not sys_counts or all(c == 0 for c in sys_counts.values()):
        fig = go.Figure()
        fig.add_annotation(text="暂无系统数据", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=200)
        return fig

    sys = list(sys_counts.keys())
    cnt = list(sys_counts.values())
    colors = ['#4a6cff', '#34d399', '#fbbf24', '#f472b6']
    fig = go.Figure(data=[
        go.Bar(x=sys, y=cnt, marker_color=colors[:len(sys)], text=cnt, textposition='outside')
    ])
    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=20, b=20),
        yaxis=dict(title="卫星数量", tickfont=dict(size=12)),
        xaxis=dict(tickfont=dict(size=12)),
        showlegend=False
    )
    return fig

# ============================================================
# 生成结论文本
# ============================================================
def generate_conclusion(data):
    if not data:
        return "上传数据并点击「开始分析」后，系统将自动生成评估结论。"
    sat = data['satellites']
    good = sum(1 for s in sat if s['quality'] > 0.7)
    medium = sum(1 for s in sat if 0.4 < s['quality'] <= 0.7)
    poor = sum(1 for s in sat if s['quality'] <= 0.4)
    sys_str = '、'.join(data['systems'])
    comp = data['completeness']

    if comp >= 90:
        level, color = "优秀", "#34d399"
    elif comp >= 80:
        level, color = "良好", "#fbbf24"
    elif comp >= 70:
        level, color = "一般", "#f97316"
    else:
        level, color = "需关注", "#f87171"

    text = f"""
    <span style="color:{color};font-weight:bold;">● {level}</span> 
    共观测到 <strong>{data['total_satellites']}</strong> 颗卫星，涵盖 {sys_str} 系统。
    数据完整率 <strong>{comp}%</strong>，采样间隔 {data['interval']} s。
    信号质量分布：<span style="color:#34d399;">良好 {good}</span> · 
    <span style="color:#fbbf24;">中等 {medium}</span> · 
    <span style="color:#f87171;">较弱 {poor}</span>。
    { '⚠️ 建议检查较弱信号卫星的观测条件。' if poor > 3 else '✅ 整体信号质量良好，满足高精度定位要求。' }
    推荐使用 {data['systems'][0] if data['systems'] else 'GPS'} + {data['systems'][1] if len(data['systems']) > 1 else 'GLONASS'} 双系统解算方案。
    """
    return text

# ============================================================
# 初始化 Session State
# ============================================================
if 'data' not in st.session_state:
    st.session_state.data = None
if 'files' not in st.session_state:
    st.session_state.files = []
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

# ============================================================
# 侧边栏：控制与趣味插件
# ============================================================
with st.sidebar:
    st.header("🛰️ 控制中心")
    uploaded_files = st.file_uploader(
        "上传数据文件（ZIP, RINEX, GNS, HTML, Excel 等）",
        accept_multiple_files=True,
        type=['zip', 'rnx', 'GNS', 'html', 'xlsx', 'crx', 'nav', 'obs']
    )
    if uploaded_files:
        st.session_state.files = uploaded_files
        st.success(f"已上传 {len(uploaded_files)} 个文件")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 开始分析", use_container_width=True):
            if st.session_state.files or True:  # 允许无文件时使用模拟数据
                with st.spinner("正在分析..."):
                    time.sleep(1.5)  # 模拟处理
                    st.session_state.data = generate_mock_data()
                    st.session_state.analyzed = True
                st.success("分析完成！")
                st.balloons()
    with col2:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.session_state.data = generate_mock_data()
            st.session_state.analyzed = True
            st.rerun()

    st.markdown("---")
    st.subheader("🎮 趣味插件")

    if st.button("🍀 今日幸运卫星", use_container_width=True):
        if st.session_state.data and st.session_state.data['satellites']:
            sat = random.choice(st.session_state.data['satellites'])
            st.info(f"🛰️ 幸运卫星：**{sat['prn']}** ({sat['system']})\n"
                    f"仰角 {sat['elevation']:.1f}° · SNR {sat['snr']:.1f} dBHz")
            st.balloons()
        else:
            st.warning("请先分析数据！")

    # 信号模拟滑块（趣味交互）
    snr_offset = st.slider("📶 模拟信号偏移", -10, 10, 0, help="调整滑块，实时改变模拟卫星的SNR值")
    if st.button("应用偏移", use_container_width=True):
        if st.session_state.data:
            for sat in st.session_state.data['satellites']:
                sat['snr'] = np.clip(sat['snr'] + snr_offset, 20, 65)
                sat['quality'] = np.clip((sat['snr'] - 28) / 30, 0.2, 1.0)
            st.rerun()
        else:
            st.warning("请先分析数据")

    # 导出按钮
    st.markdown("---")
    st.subheader("📥 导出成果")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data['satellites'])
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 导出 CSV", data=csv, file_name="gnss_observations.csv", mime="text/csv", use_container_width=True)
        # TXT 报告
        report = f"""GNSS-SAT 分析报告
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
观测历元: {st.session_state.data['epochs']}
卫星总数: {st.session_state.data['total_satellites']}
系统: {', '.join(st.session_state.data['systems'])}
采样间隔: {st.session_state.data['interval']} s
完整率: {st.session_state.data['completeness']}%
数据大小: {st.session_state.data['data_size']}
结论: {generate_conclusion(st.session_state.data)}
"""
        st.download_button("📄 导出 TXT", data=report, file_name="gnss_report.txt", mime="text/plain", use_container_width=True)

# ============================================================
# 主界面展示
# ============================================================
st.title("🛰️ GNSS-SAT 智能分析平台")
st.caption("多系统 · 实时星空 · 自动质检")

if not st.session_state.data:
    st.info("👈 请上传数据或点击「开始分析」加载演示数据")
else:
    data = st.session_state.data

    # 统计卡片
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("观测历元", data['epochs'])
    with col2:
        st.metric("卫星总数", data['total_satellites'])
    with col3:
        st.metric("导航系统", len(data['systems']))
    with col4:
        st.metric("采样间隔", f"{data['interval']} s")
    with col5:
        st.metric("数据完整率", f"{data['completeness']}%")

    # 星空图
    st.subheader("🌌 卫星星空分布")
    fig_sky = plot_sky_map(data['satellites'])
    st.plotly_chart(fig_sky, use_container_width=True)

    # 热力图 + 系统对比 两列
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📶 信号质量热力图")
        fig_heat = plot_heatmap(data['satellites'])
        st.plotly_chart(fig_heat, use_container_width=True)
    with col_right:
        st.subheader("📊 多系统卫星数量")
        fig_sys = plot_system_bars(data['sys_counts'])
        st.plotly_chart(fig_sys, use_container_width=True)

    # 结论
    st.subheader("🤖 智能分析结论")
    conclusion = generate_conclusion(data)
    st.markdown(f'<div style="background:rgba(22,30,60,0.6);border-radius:14px;padding:16px 20px;border-left:4px solid #3b6aff;">{conclusion}</div>', unsafe_allow_html=True)

    # 显示数据详情（折叠）
    with st.expander("📋 查看全部卫星数据"):
        df_all = pd.DataFrame(data['satellites'])
        st.dataframe(df_all, use_container_width=True)

# ============================================================
# 页脚
# ============================================================
st.markdown("---")
st.caption("🛰️ GNSS-SAT 智能分析平台 · 数据仅本地处理 · 模拟数据演示")