import streamlit as st

# 读取你的 HTML 文件内容
with open("index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# 嵌入 HTML（允许执行 JavaScript）[reference:16]
st.html(html_content, unsafe_allow_javascript=True)