from typing import List, Set, NoReturn, Dict
import inspect

import emoji
from nltk.corpus import stopwords
import nltk
import streamlit as st
import plotly.express as px
import pandas as pd


PLOTLY_CHART_CONFIG: Dict[str, object] = {
    "displayModeBar": False,
    "responsive": True,
}
PLOTLY_SUPPORTS_WIDTH: bool = "width" in inspect.signature(st.plotly_chart).parameters


def _render_plotly(container, fig) -> None:
    if PLOTLY_SUPPORTS_WIDTH:
        container.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)
    else:
        container.plotly_chart(fig, use_container_width=True, config=PLOTLY_CHART_CONFIG)


def load_stopwords() -> Set[str]:
    """
    Загружает и возвращает множество стоп-слов для русского и английского языков из файлов и с использованием NLTK.
    Если стоп-слова отсутствуют, происходит их загрузка.

    Returns:
        set: Множество стоп-слов.
    """

    try:
        with open("stopwords/stopwords-ru.txt", "r", encoding="utf-8") as file:
            stopwords_ru: List[str] = file.read().splitlines()

    except FileNotFoundError:
        stopwords_ru = []

    try:
        with open("stopwords/stopwords_en.txt", "r", encoding="utf-8") as file:
            stopwords_en: List[str] = file.read().splitlines()

    except FileNotFoundError:
        stopwords_en = []

    try:
        nltk_stopwords: List[str] = stopwords.words("russian") + stopwords.words(
            "english"
        )
    except LookupError:
        nltk.download("stopwords")
        nltk_stopwords = stopwords.words("russian") + stopwords.words("english")

    return set(stopwords_ru + stopwords_en + nltk_stopwords)


def extract_emojis(text: str) -> List[str]:
    """
    Извлекает эмодзи из переданного текста.

    Parameters:
        text (str): Текст для анализа.

    Returns:
        list: Список эмодзи, найденных в тексте.
    """
    return [char for char in text if char in emoji.EMOJI_DATA]


def center_text(text: str, tag: str = "p") -> NoReturn:
    """
    Отображает текст с заданным HTML-тегом и центровкой.
    """
    st.markdown(
        f"<{tag} style='text-align: center;'>{text}</{tag}>", unsafe_allow_html=True
    )


def format_russian_date(dt: pd.Timestamp) -> str:
    """
    Форматирует дату в виде 'день МММ год', заменяя английские сокращения месяцев на русские.
    """
    month_names = {
        "Jan": "Янв",
        "Feb": "Фев",
        "Mar": "Мар",
        "Apr": "Апр",
        "May": "Май",
        "Jun": "Июн",
        "Jul": "Июл",
        "Aug": "Авг",
        "Sep": "Сен",
        "Oct": "Окт",
        "Nov": "Ноя",
        "Dec": "Дек",
    }
    formatted: str = dt.strftime("%d %b %Y")
    for eng, rus in month_names.items():
        formatted = formatted.replace(eng, rus)
    return formatted


def plot_media_stats(media_df: pd.DataFrame, label: str, plotly_template: str) -> NoReturn:
    """
    Выводит статистику для заданного типа медиа.
    label: строка, описывающая тип сообщений, например:
           "голосовых сообщений" или "видеосообщений".
    plotly_template: название шаблона Plotly для единообразного отображения в текущей теме.
    """
    if media_df.empty:
        st.info(f"{label.capitalize()} отсутствуют в датасете.")
        return

    duration_series = media_df["duration"].dropna()
    total_messages = len(media_df)
    avg_duration = float(duration_series.mean()) if not duration_series.empty else 0.0
    total_duration = float(duration_series.sum()) if not duration_series.empty else 0.0
    total_minutes = total_duration / 60 if total_duration else 0.0

    metric_cols = st.columns(3)
    metric_cols[0].metric("Количество", total_messages)
    metric_cols[1].metric("Средняя длительность", f"{avg_duration:.1f} сек")
    metric_cols[2].metric("Суммарно", f"{total_minutes:.1f} мин")

    hour_counts = (
        media_df.groupby(media_df["dt"].dt.hour)
        .size()
        .reindex(range(24), fill_value=0)
        .reset_index(name="count")
    )
    hour_counts.columns = ["hour", "count"]
    hour_counts["hour_label"] = hour_counts["hour"].apply(lambda h: f"{int(h):02d}")

    charts_cols = st.columns(2)
    fig_hourly = px.bar(
        hour_counts,
        x="hour_label",
        y="count",
        color="count",
        color_continuous_scale="Blues",
        labels={"hour_label": "Час", "count": "Сообщений"},
    )
    fig_hourly.update_layout(
        template=plotly_template,
        margin=dict(t=40, b=0, l=0, r=0),
        xaxis=dict(title="Час", tickmode="linear"),
        yaxis=dict(title="Сообщений"),
    )
    _render_plotly(charts_cols[0], fig_hourly)

    if not duration_series.empty:
        fig_duration_hist = px.histogram(
            media_df,
            x="duration",
            nbins=25,
            histnorm="percent",
            labels={"duration": "Длительность (сек)", "percent": "% сообщений"},
            color_discrete_sequence=["#38bdf8"],
        )
        fig_duration_hist.add_vline(x=avg_duration, line_color="#f97316", line_dash="dash")
        fig_duration_hist.update_layout(template=plotly_template)
        _render_plotly(charts_cols[1], fig_duration_hist)
    else:
        charts_cols[1].info("Нет данных о длительности для построения распределения.")

    media_sender_df: pd.DataFrame = media_df[media_df["sender"].notna()]
    if not media_sender_df.empty:
        sender_summary = (
            media_sender_df.groupby("sender")
            .agg(
                count=("sender", "size"),
                total_duration=("duration", "sum"),
            )
            .reset_index()
        )
        sender_summary["total_minutes"] = sender_summary["total_duration"].fillna(0) / 60
        sender_summary = sender_summary.sort_values("count", ascending=False)
        top_sender_summary = sender_summary.head(7).copy()
        top_sender_summary["total_minutes"] = top_sender_summary["total_minutes"].round(1)
        top_sender_summary["minutes_label"] = top_sender_summary["total_minutes"].map(
            lambda value: f"{value:.1f} мин"
        )
        fig_sender_rank = px.bar(
            top_sender_summary.sort_values("count"),
            x="count",
            y="sender",
            orientation="h",
            color="total_minutes",
            color_continuous_scale="PuBu",
            text="minutes_label",
            labels={"count": "Сообщений", "sender": "Отправитель", "total_minutes": "Минут"},
        )
        fig_sender_rank.update_traces(textposition="outside")
        fig_sender_rank.update_layout(
            template=plotly_template,
            coloraxis_colorbar=dict(title="Минут"),
            margin=dict(t=30, b=10, l=0, r=20),
        )
        _render_plotly(st, fig_sender_rank)
    else:
        st.info(f"Нет данных об отправителях для {label}.")
