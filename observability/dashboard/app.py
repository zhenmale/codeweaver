"""
CodeWeaver 实时监控面板
基于 Streamlit 构建，展示 Token 消耗、Agent 状态、成本分析
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


st.set_page_config(
    page_title="CodeWeaver Dashboard",
    page_icon="brain",
    layout="wide",
)

st.title("CodeWeaver - Cognitive Architecture Dashboard")
st.markdown("---")

# 侧边栏配置
st.sidebar.header("配置")
days = st.sidebar.slider("统计天数", 1, 30, 7)
selected_agents = st.sidebar.multiselect(
    "选择 Agent",
    ["architect", "quantum", "semantic", "synthesis", "oracle"],
    default=["architect", "quantum", "semantic", "synthesis", "oracle"],
)

# 模拟数据生成
@st.cache_data
def generate_demo_data(days: int):
    np.random.seed(42)
    dates = [datetime.now() - timedelta(days=i) for i in range(days)]
    dates.reverse()

    data = []
    for date in dates:
        for agent in ["architect", "quantum", "semantic", "synthesis", "oracle"]:
            for _ in range(np.random.randint(100, 300)):
                model = np.random.choice(
                    ["MiMo-V2.5-Pro", "MiMo-V2.5", "claude-3-opus"],
                    p=[0.55, 0.25, 0.20],
                )
                if model == "MiMo-V2.5-Pro":
                    input_t = np.random.randint(3000, 10000)
                    output_t = np.random.randint(2000, 10000)
                elif model == "claude-3-opus":
                    input_t = np.random.randint(5000, 20000)
                    output_t = np.random.randint(5000, 30000)
                else:
                    input_t = np.random.randint(1000, 5000)
                    output_t = np.random.randint(500, 3000)

                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "agent": agent,
                    "model": model,
                    "input_tokens": input_t,
                    "output_tokens": output_t,
                    "total_tokens": input_t + output_t,
                    "latency_ms": np.random.randint(2000, 30000),
                    "success": np.random.random() > 0.05,
                    "cache_hit": np.random.random() > 0.7,
                })

    return pd.DataFrame(data)


df = generate_demo_data(days)

# 过滤
df_filtered = df[df["agent"].isin(selected_agents)]

# 顶部指标
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_tokens = df_filtered["total_tokens"].sum()
    st.metric("总 Token 消耗", f"{total_tokens:,.0f}")
with col2:
    daily_avg = total_tokens / days
    st.metric("日均消耗", f"{daily_avg:,.0f}")
with col3:
    success_rate = df_filtered["success"].mean() * 100
    st.metric("成功率", f"{success_rate:.1f}%")
with col4:
    cache_rate = df_filtered["cache_hit"].mean() * 100
    st.metric("缓存命中率", f"{cache_rate:.1f}%")

st.markdown("---")

# 图表区域
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("每日 Token 消耗趋势")
    daily_tokens = df_filtered.groupby("date")["total_tokens"].sum().reset_index()
    fig = px.line(daily_tokens, x="date", y="total_tokens", markers=True)
    fig.update_layout(xaxis_title="日期", yaxis_title="Token 数量")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Agent Token 分布")
    agent_tokens = df_filtered.groupby("agent")["total_tokens"].sum().reset_index()
    fig = px.pie(agent_tokens, values="total_tokens", names="agent", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("模型使用分布")
    model_tokens = df_filtered.groupby("model")["total_tokens"].sum().reset_index()
    fig = px.bar(model_tokens, x="model", y="total_tokens", color="model")
    st.plotly_chart(fig, use_container_width=True)

with col_right2:
    st.subheader("延迟分布")
    fig = px.histogram(df_filtered, x="latency_ms", nbins=50, color="agent")
    fig.update_layout(xaxis_title="延迟 (ms)", yaxis_title="调用次数")
    st.plotly_chart(fig, use_container_width=True)

# Agent 详情表格
st.markdown("---")
st.subheader("Agent 性能详情")
agent_stats = df_filtered.groupby("agent").agg({
    "total_tokens": ["sum", "mean"],
    "latency_ms": "mean",
    "success": "mean",
    "cache_hit": "mean",
}).round(2)
agent_stats.columns = ["总Token", "平均Token", "平均延迟(ms)", "成功率", "缓存命中率"]
st.dataframe(agent_stats, use_container_width=True)

# 页脚
st.markdown("---")
st.caption(f"CodeWeaver Dashboard | 数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
