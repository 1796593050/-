import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import zipfile
import io
import base64
import re
import random
from datetime import datetime
import time

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="GNSS-SAT 智能分析平台",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 自定义 CSS（粉蓝主题）
st.markdown("""
<style>
    /* 背景与卡片 */
    .main {
        background: radial-gradient(ellipse at 20% 50%, #111833, #070a14);
    }
    .css-18e3th9 {
        background-color: rgba(16, 22, 48, 0.7) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(74, 108, 255, 0.1);
        border-radius: 20px;
        padding: 1.5rem;
    }
    .css-1d391kg {
        background-color: transparent !important;
    }
    /* 标题 */
    h1, h2, h3 {
        color: #e8edf5 !important;
    }
    .stMetric {
        background: rgba(22, 30, 60, 0.4);
        border-radius: 14px;
        padding: 10px;
        border: 1px solid rgba(74, 108, 255, 0.05);
    }
    .stMetric label {
        color: #7a8bb5 !important;
    }
    .stMetric .css-1xarl3l {
        color: #e8edf5 !important;
    }
    /* 按钮 */
    .stButton button {
        background: linear-gradient(135deg, #3b6aff, #6b4cff);
        color: white;
        border: none;
        border-radius: 40px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(59, 106, 255, 0.3);
    }
    /* 上传区域 */
    .stFileUploader > div {
        border: 2px dashed rgba(74, 108, 255, 0.2);
        border-radius: 16px;
        padding: 20px;
        background: rgba(22, 30, 60, 0.2);
    }
    .stFileUploader > div:hover {
        border-color: #4a6cff;
    }
    /* 进度条 */
    .stProgress > div {
        background: linear-gradient(90deg, #3b6aff, #7b4cff);
    }
    /* 结论框 */
    .conclusion {
        background: rgba(22, 30, 60, 0.3);
        border-left: 4px solid #3b6aff;
        border-radius: 14px;
        padding: 16px 20px;
        color: #c8d6f0;
    }
    .lucky {
        background: rgba(251, 191, 36, 0.06);
        border: 1px solid rgba(251, 191, 36, 0.15);
        border-radius: 12px;
        padding: 10px 16px;
        color: #fbbf24;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 开场动画（使用 st.spinner + 延时）
# ============================================================
if "splash_done" not in st.session_state:
    with st.spinner("🛰️ 正在初始化 GNSS-SAT 星趣分析引擎 ..."):
        time.sleep(1.8)
    st.session_state.splash_done = True
    st.balloons()

# ============================================================
# 状态管理
# ============================================================
if "data" not in st.session_state:
    st.session_state.data = None          # 模拟数据字典
if "files" not in st.session_state:
    st.session_state.files = []           # 上传的文件名列表
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False

# ============================================================
# 模拟数据生成器（含周跳注入）
# ============================================================
def generate_mock_data():
    systems = ['GPS', 'GLONASS', 'Galileo', '北斗']
    colors = {'GPS': '#4a6cff', 'GLONASS': '#34d399', 'Galileo': '#fbbf24', '北斗': '#f472b6', '其他': '#a78bfa'}
    # 随机分配卫星数量
    counts = {
        'GPS': np.random.randint(8, 13),
        'GLONASS': np.random.randint(6, 10),
        'Galileo': np.random.randint(5, 9),
        '北斗': np.random.randint(5, 9)
    }
    total = sum(counts.values())
    satellites = []
    for sys, cnt in counts.items():
        for i in range(cnt):
            prn = (sys == 'GPS') and np.random.randint(1, 33) or \
                  (sys == 'GLONASS') and np.random.randint(1, 25) or \
                  (sys == 'Galileo') and np.random.randint(1, 31) or \
                  np.random.randint(1, 41)
            elev = np.random.uniform(5, 90)
            azim = np.random.uniform(0, 360)
            snr = np.random.uniform(30, 55)
            quality = np.clip((snr - 28) / 30, 0.1, 1.0)
            # 随机注入周跳 (约5%概率)
            cycle_slip = np.random.random() < 0.05
            satellites.append({
                'prn': f"{sys}{prn:02d}",
                'system': sys,
                'elevation': elev,
                'azimuth': azim,
                'snr': snr,
                'quality': quality,
                'color': colors.get(sys, '#a78bfa'),
                'cycle_slip': cycle_slip,
                'l1': np.random.uniform(30, 55),
                'l2': np.random.uniform(28, 50),
                'l5': np.random.uniform(25, 45),
            })
    # 随机打乱
    np.random.shuffle(satellites)
    epochs = np.random.randint(120, 300)
    interval = np.random.choice([5, 10, 15, 30, 60])
    completeness = np.random.uniform(85, 99)
    return {
        'satellites': satellites,
        'epochs': epochs,
        'interval': interval,
        'completeness': round(completeness, 1),
        'systems': [s for s, c in counts.items() if c > 0],
        'sysCounts': counts,
        'totalSatellites': len(satellites),
        'dataSize': f"{np.random.uniform(1.5, 6.5):.1f} MB",
        'formats': ['RINEX 3.04', 'GNS', 'CRX'][:np.random.randint(2, 4)],
        'cycle_slip_count': sum(1 for s in satellites if s['cycle_slip']),
    }

# ============================================================
# 绘图函数
# ============================================================
def plot_sky_map(satellites, lucky_prn=None):
    if not satellites:
        fig = go.Figure()
        fig.add_annotation(text="等待数据...", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 90])),
            showlegend=False,
            height=450,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        return fig

    # 极坐标散点图：角度=方位角，半径=仰角
    df = pd.DataFrame(satellites)
    df['radius'] = df['elevation']  # 仰角作为半径
    df['theta'] = df['azimuth']

    # 颜色映射
    color_map = {sys: col for sys, col in zip(df['system'].unique(), px.colors.qualitative.Plotly)}
    # 修正为实际系统颜色
    sys_colors = {'GPS': '#4a6cff', 'GLONASS': '#34d399', 'Galileo': '#fbbf24', '北斗': '#f472b6', '其他': '#a78bfa'}
    df['color'] = df['system'].map(sys_colors).fillna('#a78bfa')
    # 大小根据SNR
    df['size'] = df['snr'] * 0.3 + 5

    fig = go.Figure()
    # 添加网格（手动）
    fig.add_trace(go.Scatterpolar(
        r=[30, 30, 30, 30],
        theta=[0, 90, 180, 270],
        mode='lines',
        line=dict(color='rgba(74,108,255,0.08)', width=0.5),
        showlegend=False,
        hoverinfo='skip',
    ))
    fig.add_trace(go.Scatterpolar(
        r=[60, 60, 60, 60],
        theta=[0, 90, 180, 270],
        mode='lines',
        line=dict(color='rgba(74,108,255,0.08)', width=0.5),
        showlegend=False,
        hoverinfo='skip',
    ))
    # 卫星散点
    for sys, group in df.groupby('system'):
        fig.add_trace(go.Scatterpolar(
            r=group['radius'],
            theta=group['theta'],
            mode='markers+text',
            name=sys,
            text=group['prn'],
            textposition='middle center',
            textfont=dict(size=8, color='white'),
            marker=dict(
                size=group['size'],
                color=group['color'],
                opacity=0.8,
                line=dict(width=1, color='rgba(255,255,255,0.3)'),
            ),
            hovertemplate='<b>%{text}</b><br>仰角: %{r:.1f}°<br>方位: %{theta:.1f}°<br>SNR: %{marker.size:.1f} dBHz<extra></extra>',
            customdata=group['prn'],
        ))

    # 高亮幸运卫星
    if lucky_prn:
        lucky_data = df[df['prn'] == lucky_prn]
        if not lucky_data.empty:
            fig.add_trace(go.Scatterpolar(
                r=lucky_data['radius'],
                theta=lucky_data['theta'],
                mode='markers',
                marker=dict(
                    size=lucky_data['size'].iloc[0] * 1.8,
                    color='#fbbf24',
                    symbol='star',
                    line=dict(width=2, color='white'),
                ),
                showlegend=False,
                hoverinfo='skip',
            ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                range=[0, 90],
                tickvals=[0, 30, 60, 90],
                ticktext=['0°', '30°', '60°', '90°'],
                gridcolor='rgba(74,108,255,0.06)',
                linecolor='rgba(74,108,255,0.1)',
            ),
            angularaxis=dict(
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                gridcolor='rgba(74,108,255,0.06)',
                linecolor='rgba(74,108,255,0.1)',
            ),
            bgcolor='rgba(0,0,0,0)',
        ),
        height=450,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(font=dict(color='#8a9fc5')),
        hovermode='closest',
    )
    return fig

def plot_heatmap(satellites):
    if not satellites:
        return None
    # 取前36颗
    data = satellites[:36]
    # 构建网格 6x6
    grid = np.zeros((6, 6))
    for i, sat in enumerate(data):
        row = i // 6
        col = i % 6
        grid[row, col] = sat['snr']
    # 使用 imshow
    fig = go.Figure(data=go.Heatmap(
        z=grid,
        colorscale=[[0, '#f87171'], [0.4, '#f97316'], [0.7, '#fbbf24'], [1, '#34d399']],
        zmin=25, zmax=55,
        text=[[data[i*6+j]['prn'] if i*6+j < len(data) else '' for j in range(6)] for i in range(6)],
        texttemplate='%{text}',
        textfont=dict(size=8, color='white'),
        hoverongaps=False,
        hovertemplate='SNR: %{z:.1f} dBHz<extra></extra>',
        showscale=False,
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, gridcolor='rgba(0,0,0,0)'),
        yaxis=dict(showticklabels=False, gridcolor='rgba(0,0,0,0)'),
    )
    return fig

def plot_system_bars(sysCounts):
    if not sysCounts:
        return None
    df = pd.DataFrame(list(sysCounts.items()), columns=['System', 'Count'])
    colors = {'GPS': '#4a6cff', 'GLONASS': '#34d399', 'Galileo': '#fbbf24', '北斗': '#f472b6', '其他': '#a78bfa'}
    df['Color'] = df['System'].map(colors).fillna('#a78bfa')
    fig = px.bar(df, x='Count', y='System', orientation='h', color='System',
                 color_discrete_map=colors,
                 text='Count',
                 height=200,
                 )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=True, tickfont=dict(color='#b0c4f0')),
        showlegend=False,
    )
    return fig

# ============================================================
# 主界面
# ============================================================
st.title("🛰️ GNSS-SAT 智能分析平台")
st.caption("粉蓝 · 星趣版 · 支持多格式 · 自动质检与报告")

# 布局：上传区 + 操作栏
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📂 数据上传")
    uploaded_files = st.file_uploader(
        "拖拽或点击上传",
        type=['zip', 'rnx', 'GNS', 'html', 'xlsx', 'crx', 'nav', 'obs'],
        accept_multiple_files=True,
        key="uploader",
    )
    if uploaded_files:
        # 更新文件列表
        st.session_state.files = [f.name for f in uploaded_files]
        # 如果尚未生成数据，生成模拟
        if st.session_state.data is None:
            st.session_state.data = generate_mock_data()
            # 根据文件名增加格式识别
            names = " ".join([f.name for f in uploaded_files])
            if 'zip' in names:
                st.session_state.data['formats'].append('ZIP')
            if 'html' in names:
                st.session_state.data['formats'].append('HTML')
            st.session_state.analyzed = False

    # 显示文件列表
    if st.session_state.files:
        st.write("已上传文件：")
        for fname in st.session_state.files:
            st.markdown(f"- 📄 {fname}")
    else:
        st.info("等待上传数据...")

    # 按钮组
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        analyze_btn = st.button("🚀 开始分析", use_container_width=True)
    with col_btn2:
        reset_btn = st.button("🔄 重置", use_container_width=True)

    if reset_btn:
        st.session_state.data = None
        st.session_state.files = []
        st.session_state.analyzed = False
        st.rerun()

with col2:
    st.subheader("📊 数据概览")
    if st.session_state.data:
        data = st.session_state.data
        # 使用 metrics 展示
        m1, m2, m3 = st.columns(3)
        m1.metric("观测历元", data['epochs'])
        m2.metric("卫星总数", data['totalSatellites'])
        m3.metric("导航系统", len(data['systems']))
        m4, m5, m6 = st.columns(3)
        m4.metric("采样间隔", f"{data['interval']} s")
        m5.metric("完整率", f"{data['completeness']}%")
        m6.metric("识别格式", ", ".join(data['formats']))
    else:
        st.info("请上传数据以查看概览")

# ============================================================
# 分析逻辑
# ============================================================
if analyze_btn:
    if st.session_state.data is None:
        st.warning("请先上传数据文件")
    else:
        # 模拟分析进度
        progress_bar = st.progress(0, text="分析中...")
        status_text = st.empty()
        for i in range(1, 101, 10):
            time.sleep(0.15)
            progress_bar.progress(i)
            if i < 30:
                status_text.info("🔍 识别数据格式...")
            elif i < 60:
                status_text.info("📊 计算观测质量 & 周跳探测...")
            elif i < 85:
                status_text.info("🌐 分析卫星分布...")
            else:
                status_text.info("📝 生成报告...")
        progress_bar.empty()
        status_text.empty()
        st.session_state.analyzed = True
        # 重新生成数据（模拟真实分析结果）
        st.session_state.data = generate_mock_data()
        # 注入周跳信息
        st.success("✅ 分析完成！")
        st.balloons()

# ============================================================
# 展示分析结果
# ============================================================
if st.session_state.analyzed and st.session_state.data:
    data = st.session_state.data
    satellites = data['satellites']

    # 幸运卫星 (SNR最高)
    lucky = max(satellites, key=lambda x: x['snr']) if satellites else None
    lucky_prn = lucky['prn'] if lucky else None

    # 布局：图表区
    st.divider()
    st.subheader("🌐 卫星星空分布")
    fig_sky = plot_sky_map(satellites, lucky_prn)
    st.plotly_chart(fig_sky, use_container_width=True)

    # 交互说明
    st.caption("💡 悬停查看卫星详情 · 幸运卫星 🌟 以星形高亮")

    # 第二行：热力图 + 系统对比
    col3, col4 = st.columns([1, 1])
    with col3:
        st.subheader("📶 信号质量热力图")
        fig_heat = plot_heatmap(satellites)
        if fig_heat:
            st.plotly_chart(fig_heat, use_container_width=True)
        st.caption("颜色：绿（强） → 黄 → 红（弱）")

    with col4:
        st.subheader("📊 多系统卫星数量")
        fig_sys = plot_system_bars(data['sysCounts'])
        if fig_sys:
            st.plotly_chart(fig_sys, use_container_width=True)

    # 结论 + 幸运卫星
    st.divider()
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("🧠 智能分析结论")
        # 生成结论文本
        good = sum(1 for s in satellites if s['quality'] > 0.7)
        poor = sum(1 for s in satellites if s['quality'] <= 0.4)
        medium = len(satellites) - good - poor
        level = "优秀" if data['completeness'] >= 90 else "良好" if data['completeness'] >= 80 else "一般"
        color = "#34d399" if level == "优秀" else "#fbbf24" if level == "良好" else "#f97316"
        sys_str = ", ".join(data['systems'])
        conclusion = f"""
        <div class="conclusion">
            <span style="color:{color};font-weight:600;">● {level}</span> 
            共观测到 <strong style="color:#98b0ff;">{data['totalSatellites']}</strong> 颗卫星，涵盖 {sys_str} 系统。
            数据完整率 <strong style="color:#98b0ff;">{data['completeness']}%</strong>，采样间隔 {data['interval']}s。
            信号质量分布：<span style="color:#34d399;">良好 {good}</span> · 
            <span style="color:#fbbf24;">中等 {medium}</span> · 
            <span style="color:#f87171;">较弱 {poor}</span>。
            { '⚠️ 检测到周跳，建议处理。' if data['cycle_slip_count'] > 0 else '✅ 未检测到明显周跳。'}
            推荐使用 {data['systems'][0] if data['systems'] else 'GPS'} + {data['systems'][1] if len(data['systems'])>1 else 'GLONASS'} 双系统解算。
        </div>
        """
        st.markdown(conclusion, unsafe_allow_html=True)

    with col6:
        st.subheader("🌟 今日幸运卫星")
        if lucky:
            st.markdown(f"""
            <div class="lucky">
                <i class="fas fa-star" style="color:#fbbf24;"></i>
                <strong style="color:white;font-size:1.2rem;">{lucky['prn']}</strong><br>
                SNR: {lucky['snr']:.1f} dBHz<br>
                系统: {lucky['system']}<br>
                仰角: {lucky['elevation']:.1f}°
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("暂无卫星数据")

    # 导出按钮
    st.divider()
    st.subheader("📥 成果导出")
    col7, col8, col9 = st.columns(3)

    # 生成 CSV
    def generate_csv():
        df = pd.DataFrame(satellites)
        # 选择列
        cols = ['prn', 'system', 'elevation', 'azimuth', 'snr', 'quality', 'cycle_slip']
        df = df[cols]
        return df.to_csv(index=False).encode('utf-8')

    with col7:
        csv_data = generate_csv()
        st.download_button(
            label="📊 导出 CSV",
            data=csv_data,
            file_name=f"GNSS_观测数据_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # 导出 PNG (使用 plotly 的静态图)
    with col8:
        # 生成星空图 PNG 下载
        fig_png = plot_sky_map(satellites, lucky_prn)
        img_bytes = fig_png.to_image(format="png", width=800, height=600)
        st.download_button(
            label="🖼️ 导出 PNG",
            data=img_bytes,
            file_name=f"GNSS_星空图_{datetime.now().strftime('%Y%m%d')}.png",
            mime="image/png",
            use_container_width=True,
        )

    # 导出 TXT
    def generate_txt():
        lines = []
        lines.append("=" * 40)
        lines.append("  GNSS-SAT 星趣分析报告")
        lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 40)
        lines.append(f"观测历元: {data['epochs']}")
        lines.append(f"卫星总数: {data['totalSatellites']}")
        lines.append(f"导航系统: {', '.join(data['systems'])}")
        lines.append(f"采样间隔: {data['interval']} s")
        lines.append(f"数据完整率: {data['completeness']}%")
        lines.append(f"数据大小: {data['dataSize']}")
        lines.append(f"识别格式: {', '.join(data['formats'])}")
        lines.append(f"周跳数: {data['cycle_slip_count']}")
        lines.append("\n--- 卫星详情 ---")
        for s in satellites:
            lines.append(f"{s['prn']} | {s['system']} | 仰角 {s['elevation']:.1f}° | 方位 {s['azimuth']:.1f}° | SNR {s['snr']:.1f} dBHz | 周跳 {s['cycle_slip']}")
        lines.append("\n--- 系统统计 ---")
        for sys, cnt in data['sysCounts'].items():
            lines.append(f"{sys}: {cnt} 颗")
        lines.append("\n--- 结论 ---")
        good = sum(1 for s in satellites if s['quality'] > 0.7)
        poor = sum(1 for s in satellites if s['quality'] <= 0.4)
        lines.append(f"信号质量: 良好 {good}, 较弱 {poor}")
        if data['cycle_slip_count'] > 0:
            lines.append("⚠️ 检测到周跳，建议处理。")
        else:
            lines.append("✅ 未检测到明显周跳。")
        if lucky:
            lines.append(f"🌟 幸运卫星: {lucky['prn']} (SNR {lucky['snr']:.1f} dBHz)")
        lines.append("=" * 40)
        return "\n".join(lines)

    with col9:
        txt_data = generate_txt()
        st.download_button(
            label="📄 导出 TXT",
            data=txt_data,
            file_name=f"GNSS_报告_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # 显示周跳统计信息
    if data['cycle_slip_count'] > 0:
        st.warning(f"⚠️ 检测到 {data['cycle_slip_count']} 个周跳，已在数据中标记。")

# ============================================================
# 底部信息
# ============================================================
st.divider()
st.caption("🛰️ GNSS-SAT 星趣版 · 数据仅本地处理 · 点击星空探索卫星")
