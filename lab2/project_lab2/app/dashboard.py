#!/usr/bin/env python3

import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Подключение к БД
DB_PATH = os.getenv("DB_PATH", "/app/data/hr.db")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Загрузка данных из SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM employees;", conn)
    conn.close()
    return df

st.set_page_config(page_title="HR Retention Analytics", layout="wide")
st.title("HR Retention Analytics — Анализ удержания сотрудников")

try:
    df = load_data()
except Exception as e:
    st.error(f"Не удалось подключиться к БД: {e}")
    st.info("Убедитесь, что данные загружены: сначала запустите генератор и загрузчик.")
    st.stop()

# Ключевые метрики
col1, col2, col3, col4, col5 = st.columns(5)

total = len(df)
active = len(df[df["left"] == "Нет"])
left = len(df[df["left"] == "Да"])

col1.metric("Всего сотрудников", f"{total:,}")
col2.metric("Работают", f"{active:,}", f"{active/total*100:.1f}%")
col3.metric("Уволились", f"{left:,}", f"{left/total*100:.1f}%")
col4.metric("Производительность", f"{df['performance'].mean():.2f}")
col5.metric("Удовлетворенность", f"{df['satisfaction'].mean():.2f}")

st.markdown("---")

# ГРАФИК 1
st.subheader("Количество уволившихся по должностям")

left_by_position = (
    df[df["left"] == "Да"]
    .groupby("position")
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=True)
)

fig_positions = px.bar(
    left_by_position,
    x="count",
    y="position",
    orientation="h",
    color="count",
    color_continuous_scale="Reds",
    labels={"count": "Количество уволившихся", "position": "Должность"}
)
fig_positions.update_layout(height=400, yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_positions, use_container_width=True)

st.markdown("---")

# ГРАФИК 2
st.subheader("Распределение уволившихся по уровню удовлетворенности")

left_df = df[df["left"] == "Да"].copy()
left_df["satisfaction_group"] = "3-4 (Средняя)" 
left_df.loc[left_df["satisfaction"] < 3, "satisfaction_group"] = "1-2 (Низкая)"
left_df.loc[left_df["satisfaction"] == 5, "satisfaction_group"] = "5 (Высокая)"

satisfaction_pie = (
    left_df.groupby("satisfaction_group")
    .size()
    .reset_index(name="count")
)

fig_pie = px.pie(
    satisfaction_pie,
    values="count",
    names="satisfaction_group",
    title="Количество уволившихся по уровню удовлетворенности",
    color_discrete_sequence=px.colors.sequential.Reds_r,
    hole=0.3
)
fig_pie.update_traces(textposition='inside', textinfo='percent+label')
fig_pie.update_layout(height=500)
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ГРАФИК 3
st.subheader("Процент увольнений по группам стажа")

df["experience_group"] = pd.cut(
    df["experience"],
    bins=[0, 1, 3, 5, 10, 20, 30],
    labels=["0-1 год", "1-3 года", "3-5 лет", "5-10 лет", "10-20 лет", "20+ лет"],
    right=False
)

experience_rate = (
    df.groupby("experience_group")
    .agg(
        total=("id", "count"),
        left_count=("left", lambda x: (x == "Да").sum())
    )
    .reset_index()
)
experience_rate["left_rate"] = (experience_rate["left_count"] / experience_rate["total"] * 100).round(1)

fig_experience_rate = px.bar(
    experience_rate,
    x="experience_group",
    y="left_rate",
    color="left_rate",
    color_continuous_scale="Reds",
    labels={"experience_group": "Стаж", "left_rate": "% увольнений"},
    text="left_rate"
)
fig_experience_rate.update_traces(texttemplate='%{text}%', textposition='outside')
fig_experience_rate.update_layout(height=400)
st.plotly_chart(fig_experience_rate, use_container_width=True)

st.caption("Данные: синтетический датасет hr_data.csv • Streamlit + Plotly + SQLite")