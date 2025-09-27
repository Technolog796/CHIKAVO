from typing import Optional, NoReturn, List, Dict
import inspect

import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import timedelta
from collections import Counter
from src.telegram_analysis import process_json, get_word_frequency
from src.utils import load_stopwords, format_russian_date, plot_media_stats


TYPE_DETAILS: Dict[str, Dict[str, str]] = {
    "text": {
        "name": "Текстовые сообщения",
        "title": "Живые беседы",
        "icon": "💬",
        "color": "#6366F1",
        "tagline": "В {share:.1f}% сообщений вы делитесь мыслями словами.",
    },
    "photo": {
        "name": "Фотографии",
        "title": "Фотоистории",
        "icon": "📸",
        "color": "#F97316",
        "tagline": "Яркие кадры составляют {share:.1f}% переписки.",
    },
    "video": {
        "name": "Видеосообщения",
        "title": "Видеоэффект",
        "icon": "🎬",
        "color": "#FBBF24",
        "tagline": "Делитесь движением — {share:.1f}% истории в видеоформате.",
    },
    "sticker": {
        "name": "Стикеры",
        "title": "Настроение в стикерах",
        "icon": "😄",
        "color": "#22D3EE",
        "tagline": "Эмоции в картинках — {share:.1f}% сообщений.",
    },
    "audio/voice": {
        "name": "Голосовые",
        "title": "Голоса друзей",
        "icon": "🎙",
        "color": "#10B981",
        "tagline": "Живое общение — {share:.1f}% сообщений в голосе.",
    },
    "file": {
        "name": "Файлы",
        "title": "Полезные файлы",
        "icon": "📂",
        "color": "#8B5CF6",
        "tagline": "Практичные вложения — {share:.1f}% сообщений.",
    },
}

DEFAULT_TYPE_DETAIL: Dict[str, str] = {
    "name": "Сообщения",
    "title": "Интересный формат",
    "icon": "✨",
    "color": "#14B8A6",
    "tagline": "Этот тип лидирует по популярности.",
}

WEEKDAY_NAMES: Dict[int, str] = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}

MONTH_LABELS: Dict[int, str] = {
    1: "Янв",
    2: "Фев",
    3: "Мар",
    4: "Апр",
    5: "Май",
    6: "Июн",
    7: "Июл",
    8: "Авг",
    9: "Сен",
    10: "Окт",
    11: "Ноя",
    12: "Дек",
}

PLOTLY_CONFIG: Dict[str, object] = {
    "displayModeBar": False,
    "responsive": True,
}
PLOTLY_SUPPORTS_WIDTH: bool = "width" in inspect.signature(st.plotly_chart).parameters


def render_plotly(fig, container=None) -> None:
    target = container if container is not None else st
    if PLOTLY_SUPPORTS_WIDTH:
        target.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    else:
        target.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


def run_app() -> NoReturn:
    """
    Запускает Streamlit-приложение для анализа экспорта переписки Telegram в формате JSON.
    Приложение отображает статистику, графики и аналитические отчёты по сообщениям, включая текстовые и медиа-сообщения.
    """
    st.set_page_config(
        page_title="Анализ Telegram Чата",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    def inject_theme() -> None:
        palette = {
            "app_bg": "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
            "card_bg": "rgba(30, 41, 59, 0.72)",
            "card_border": "rgba(148, 163, 184, 0.18)",
            "text": "#e2e8f0",
            "muted": "#94a3b8",
            "accent": "#38bdf8",
            "accent_soft": "rgba(56, 189, 248, 0.18)",
            "sidebar_bg": "linear-gradient(160deg, #0f172a 0%, #1e293b 100%)",
            "badge_shadow": "0 10px 30px rgba(56, 189, 248, 0.15)",
        }

        st.markdown(
            f"""
            <style>
            :root {{
                --app-bg: {palette["app_bg"]};
                --card-bg: {palette["card_bg"]};
                --card-border: {palette["card_border"]};
                --text-color: {palette["text"]};
                --muted-color: {palette["muted"]};
                --accent-color: {palette["accent"]};
                --accent-soft: {palette["accent_soft"]};
            }}
            .stApp {{
                background: var(--app-bg);
                color: var(--text-color);
            }}
            section[data-testid="stSidebar"] {{
                background: {palette["sidebar_bg"]};
            }}
            section[data-testid="stSidebar"] * {{
                color: var(--text-color) !important;
            }}
            h1, h2, h3, h4, h5, h6, p, div, span {{
                color: var(--text-color);
            }}
            .metric-card {{
                display: flex;
                gap: 1rem;
                align-items: center;
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 14px;
                padding: 1.25rem 1.5rem;
                box-shadow: 0 18px 30px rgba(15, 23, 42, 0.12);
            }}
            .metric-card h3 {{
                margin: 0;
                color: var(--text-color);
            }}
            .metric-subtitle {{
                margin: 0.15rem 0 0;
                color: var(--muted-color);
                font-size: 0.9rem;
            }}
            .metric-icon {{
                font-size: 2rem;
                line-height: 1;
            }}
            .highlight-card {{
                border-left: 6px solid var(--accent-color);
            }}
            .tag-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.4rem 0.95rem;
                border-radius: 999px;
                background: var(--accent-soft);
                color: var(--accent-color);
                font-weight: 600;
                font-size: 0.85rem;
                box-shadow: {palette["badge_shadow"]};
                white-space: nowrap;
            }}
            .badge-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 1rem;
            }}
            .section-title {{
                font-weight: 700;
                color: var(--text-color);
                margin-bottom: 0.6rem;
                font-size: 1.2rem;
            }}
            .section-title span {{
                color: var(--accent-color);
            }}
            .stTabs [data-baseweb="tab"] {{
                background: var(--card-bg);
                border-radius: 14px 14px 0 0;
                padding: 0.7rem 1.4rem;
                border: 1px solid transparent;
                color: var(--muted-color);
                font-weight: 600;
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                border-color: var(--accent-color);
            }}
            .stTabs [aria-selected="true"][data-baseweb="tab"] {{
                color: var(--accent-color);
                border-color: var(--accent-color);
                background: rgba(255, 255, 255, 0.04);
            }}
            div[data-testid="stMetricValue"] {{
                color: var(--text-color) !important;
            }}
            div[data-testid="stMetricLabel"] {{
                color: var(--muted-color) !important;
            }}
            .stPlotlyChart {{
                background: transparent;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

    inject_theme()

    with st.sidebar:
        st.header("Панель")
        st.caption("Файл экспорта JSON можно получить в настройках Telegram Desktop.")

    st.title("Анализ переписки в Telegram")
    st.subheader("Постройте визуальную историю вашего общения")
    st.write(
        "Загрузите JSON-файл экспорта из Telegram и посмотрите, как менялась активность, какие медиа преобладают и какие слова звучат чаще всего."
    )

    uploaded_file = st.file_uploader(
        "Выберите JSON-файл",
        type=["json"],
        help="Файл экспорта переписки из Telegram",
    )
    if uploaded_file is None:
        st.info("Пожалуйста, загрузите файл для начала анализа.")
        return

    try:
        data: dict = json.load(uploaded_file)
    except Exception:
        st.error("Ошибка: Неверный формат файла. Загрузите корректный JSON.")
        return

    daily_counts, corpus, df, emojis_list = process_json(data)
    if daily_counts is None or df is None:
        return

    df = df.sort_values("dt").reset_index(drop=True)
    daily_counts = daily_counts.sort_values("date_dt").reset_index(drop=True)

    years: List[int] = sorted(df["dt"].dt.year.unique().tolist())
    plotly_template: str = "plotly_dark"

    total_messages: int = len(df)
    total_text_length: int = int(df["text_length"].sum())
    avg_text_length: float = float(df["text_length"].mean()) if total_messages else 0.0
    total_emojis: int = len(emojis_list)
    max_messages_day: int = int(daily_counts["count"].max()) if not daily_counts.empty else 0
    min_messages_day: int = int(daily_counts["count"].min()) if not daily_counts.empty else 0
    active_days: int = daily_counts[daily_counts["count"] > 0].shape[0]
    conversation_span_days: int = (
        (df["dt"].max().date() - df["dt"].min().date()).days + 1 if not df.empty else 0
    )

    monthly_activity = (
        df.groupby(pd.Grouper(key="dt", freq="ME"))
        .size()
        .reset_index(name="count")
    )
    if not monthly_activity.empty:
        monthly_activity["month_label"] = (
            monthly_activity["dt"].dt.month.map(MONTH_LABELS).fillna("???")
            + " "
            + monthly_activity["dt"].dt.year.astype(str)
        )
        monthly_activity["month_order"] = monthly_activity["dt"].dt.strftime("%Y-%m")

    monthly_types = (
        df.groupby([pd.Grouper(key="dt", freq="ME"), "type"])
        .size()
        .reset_index(name="count")
    )
    if not monthly_types.empty:
        monthly_types["month_label"] = (
            monthly_types["dt"].dt.month.map(MONTH_LABELS).fillna("???")
            + " "
            + monthly_types["dt"].dt.year.astype(str)
        )
        monthly_types["month_order"] = monthly_types["dt"].dt.strftime("%Y-%m")
        monthly_types["type_label"] = monthly_types["type"].map(
            lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["name"]
        )

    hourly_counts = (
        df.groupby("hour")
        .size()
        .reindex(range(24), fill_value=0)
        .reset_index(name="count")
    )
    hourly_counts["hour_label"] = hourly_counts["hour"].apply(lambda h: f"{int(h):02d}:00")
    peak_hour_label: str = (
        hourly_counts.loc[hourly_counts["count"].idxmax(), "hour_label"]
        if not hourly_counts.empty
        else "00:00"
    )

    peak_day_label: Optional[str] = None
    if not daily_counts.empty:
        peak_day = daily_counts.loc[daily_counts["count"].idxmax(), "date_dt"]
        peak_day_label = format_russian_date(peak_day)

    weekday_counts = (
        df.assign(weekday=df["dt"].dt.dayofweek)
        .groupby("weekday")
        .size()
        .reindex(range(7), fill_value=0)
        .reset_index(name="count")
    )
    top_weekday_label: Optional[str] = None
    if not weekday_counts.empty:
        top_weekday = int(weekday_counts.loc[weekday_counts["count"].idxmax(), "weekday"])
        top_weekday_label = WEEKDAY_NAMES.get(top_weekday)

    type_counts = df["type"].value_counts()
    top_type: str = type_counts.idxmax() if not type_counts.empty else "text"
    top_type_count: int = int(type_counts.get(top_type, 0))
    top_type_share: float = (top_type_count / total_messages * 100) if total_messages else 0.0
    type_meta = TYPE_DETAILS.get(top_type, DEFAULT_TYPE_DETAIL)
    try:
        top_type_tagline: str = type_meta.get("tagline", DEFAULT_TYPE_DETAIL["tagline"]).format(
            share=top_type_share
        )
    except (KeyError, ValueError):
        top_type_tagline = type_meta.get("tagline", DEFAULT_TYPE_DETAIL["tagline"])
    highlight_color: str = type_meta.get("color", DEFAULT_TYPE_DETAIL["color"])
    highlight_icon: str = type_meta.get("icon", DEFAULT_TYPE_DETAIL["icon"])
    highlight_title: str = type_meta.get("title", DEFAULT_TYPE_DETAIL["title"])
    top_type_label: str = type_meta.get("name", DEFAULT_TYPE_DETAIL["name"])

    type_counts_df = type_counts.reset_index()
    type_counts_df.columns = ["type", "count"]
    type_counts_df["type_label"] = type_counts_df["type"].map(
        lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["name"]
    )
    type_color_map = {
        details["name"]: details["color"] for details in TYPE_DETAILS.values()
    }
    type_color_map.setdefault(DEFAULT_TYPE_DETAIL["name"], DEFAULT_TYPE_DETAIL["color"])

    today = pd.Timestamp.today().normalize()
    last_week_start = today - timedelta(days=6)
    last_week_dates = pd.date_range(last_week_start, today)
    last_week_df = pd.DataFrame({"date_dt": last_week_dates})
    last_week_data = pd.merge(
        last_week_df, daily_counts[["date_dt", "count"]], on="date_dt", how="left"
    ).fillna(0)
    if not last_week_data.empty:
        last_week_data["count"] = last_week_data["count"].astype(int)
        last_week_data["date_label"] = last_week_data["date_dt"].apply(format_russian_date)

    activity_matrix = (
        df.assign(weekday=df["dt"].dt.dayofweek)
        .groupby(["weekday", "hour"])
        .size()
        .reset_index(name="count")
    )
    activity_pivot = pd.DataFrame()
    if not activity_matrix.empty:
        activity_matrix["weekday_label"] = activity_matrix["weekday"].map(WEEKDAY_NAMES)
        weekday_order = [WEEKDAY_NAMES[i] for i in range(7)]
        activity_pivot = (
            activity_matrix.pivot(index="weekday_label", columns="hour", values="count")
            .reindex(weekday_order)
            .fillna(0)
        )
        activity_pivot.columns = [f"{int(col):02d}:00" for col in activity_pivot.columns]

    media_types = ["photo", "video", "sticker", "file", "audio/voice"]
    media_df = df[df["type"].isin(media_types)]
    voice_df = df[df["type"] == "audio/voice"]
    video_df = df[df["type"] == "video"]
    text_df = df[df["type"] == "text"]
    sticker_df = df[df["type"] == "sticker"]

    reaction_emoji_counter: Counter = Counter()
    reaction_list: List[Dict[str, str]] = []
    for msg in data.get("messages", []):
        for reaction in msg.get("reactions", []):
            if reaction.get("type") == "emoji":
                emoji_used = reaction.get("emoji")
                count = reaction.get("count", 0)
                if emoji_used:
                    reaction_emoji_counter[emoji_used] += count
                for recent_info in reaction.get("recent", []):
                    user_from = recent_info.get("from")
                    if user_from and emoji_used:
                        reaction_list.append({"user": user_from, "emoji": emoji_used})
    total_reactions: int = int(sum(reaction_emoji_counter.values()))

    emoji_counter = Counter(emojis_list)

    summary_tab, activity_tab, media_tab, text_tab, reactions_tab, extras_tab, raw_tab = st.tabs(
        ["Сводка", "Активность", "Медиа", "Текст", "Реакции", "Дополнительно", "Данные"]
    )

    with summary_tab:
        st.markdown("<h3 class='section-title'><span>Ключевые</span> показатели</h3>", unsafe_allow_html=True)
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Всего сообщений", total_messages)
            st.metric("Дней активности", active_days)
        with metric_col2:
            st.metric("Макс. сообщений в день", max_messages_day)
            st.metric("Мин. сообщений в день", min_messages_day)
        with metric_col3:
            st.metric("Общее кол-во символов", total_text_length)
            st.metric("Средняя длина текста", f"{avg_text_length:.1f}")

        st.markdown(
            f"""
            <div class="metric-card highlight-card" style="border-left-color: {highlight_color};">
                <div class="metric-icon">{highlight_icon}</div>
                <div>
                    <p class="metric-subtitle">Любимый формат</p>
                    <h3>{highlight_title}</h3>
                    <p class="metric-subtitle">{top_type_tagline}</p>
                    <div class="tag-badge">{top_type_label} · {top_type_share:.1f}%</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        badges: List[str] = []
        if peak_day_label:
            badges.append(f"<div class='tag-badge'>Самый активный день: {peak_day_label}</div>")
        badges.append(f"<div class='tag-badge'>Пиковый час: {peak_hour_label}</div>")
        if top_weekday_label:
            badges.append(f"<div class='tag-badge'>Главный день недели: {top_weekday_label}</div>")
        if conversation_span_days and conversation_span_days > 0:
            badges.append(f"<div class='tag-badge'>Длительность общения: {conversation_span_days} дней</div>")

        if badges:
            badges_html = "<div class='badge-row'>" + "".join(badges) + "</div>"
            st.markdown(badges_html, unsafe_allow_html=True)

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        chart_cols = st.columns((2, 1.1))
        if not monthly_activity.empty:
            ordered_months = monthly_activity.sort_values("month_order")["month_label"].tolist()
            fig_monthly_summary = px.line(
                monthly_activity.sort_values("month_order"),
                x="month_label",
                y="count",
                labels={"month_label": "Месяц", "count": "Сообщений"},
            )
            fig_monthly_summary.update_traces(mode="lines+markers", line_shape="spline", fill="tozeroy")
            fig_monthly_summary.update_layout(
                template=plotly_template,
                hovermode="x unified",
                xaxis=dict(categoryorder="array", categoryarray=ordered_months),
            )
            render_plotly(fig_monthly_summary, chart_cols[0])

        if not type_counts_df.empty:
            fig_type_share = px.pie(
                type_counts_df,
                names="type_label",
                values="count",
                hole=0.5,
                color="type_label",
                color_discrete_map={
                    label: type_color_map.get(label, highlight_color)
                    for label in type_counts_df["type_label"]
                },
            )
            fig_type_share.update_traces(
                textposition="outside",
                texttemplate="%{label}<br>%{percent:.1%}",
                textfont=dict(color="#e2e8f0", size=12),
                pull=0.02,
            )
            fig_type_share.update_layout(
                template=plotly_template,
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
            )
            render_plotly(fig_type_share, chart_cols[1])

    with activity_tab:
        st.markdown("<h3 class='section-title'><span>Активность</span> во времени</h3>", unsafe_allow_html=True)
        if not daily_counts.empty:
            tick_interval_months: int = st.slider(
                "Интервал подписей по оси X (месяцы)",
                min_value=1,
                max_value=12,
                value=3,
                key="tick_interval_slider",
            )
            fig_daily = px.area(
                daily_counts,
                x="date_dt",
                y="count",
                labels={"date_dt": "Дата", "count": "Сообщений"},
            )
            fig_daily.update_traces(line_shape="spline")
            min_date = daily_counts["date_dt"].min()
            max_date = daily_counts["date_dt"].max()
            tick_dates: List[pd.Timestamp] = []
            if pd.notna(min_date) and pd.notna(max_date):
                current_tick = pd.Timestamp(min_date).normalize()
                while current_tick <= max_date:
                    tick_dates.append(current_tick)
                    current_tick += pd.DateOffset(months=tick_interval_months)
            if tick_dates:
                tick_texts = [format_russian_date(tick) for tick in tick_dates]
                fig_daily.update_xaxes(
                    tickmode="array",
                    tickvals=tick_dates,
                    ticktext=tick_texts,
                )
            fig_daily.update_layout(template=plotly_template, hovermode="x unified")
            render_plotly(fig_daily)

        hourly_col, heatmap_col = st.columns((1.35, 1))
        fig_hourly = px.area(
            hourly_counts,
            x="hour_label",
            y="count",
            labels={"hour_label": "Час дня", "count": "Сообщений"},
        )
        fig_hourly.update_traces(
            line_shape="spline",
            mode="lines+markers",
            marker=dict(size=6, color=highlight_color),
            line=dict(color=highlight_color, width=3),
            fillcolor="rgba(56, 189, 248, 0.25)",
        )
        fig_hourly.update_layout(template=plotly_template)
        render_plotly(fig_hourly, hourly_col)

        if not activity_pivot.empty:
            fig_heatmap = px.imshow(
                activity_pivot,
                color_continuous_scale="YlGnBu",
                aspect="auto",
                labels=dict(color="Сообщений"),
            )
            fig_heatmap.update_layout(
                template=plotly_template,
                coloraxis_colorbar=dict(title="Сообщений"),
            )
            fig_heatmap.update_yaxes(title="День недели")
            fig_heatmap.update_xaxes(title="Час дня")
            render_plotly(fig_heatmap, heatmap_col)
        else:
            heatmap_col.info("Недостаточно данных для тепловой карты.")

        if not last_week_data.empty:
            st.markdown("<h4 class='section-title'><span>Последняя</span> неделя</h4>", unsafe_allow_html=True)
            fig_last_week = px.area(
                last_week_data,
                x="date_label",
                y="count",
                labels={"date_label": "Дата", "count": "Сообщений"},
            )
            fig_last_week.update_traces(
                line_shape="spline",
                mode="lines+markers",
                marker=dict(size=6, color=highlight_color),
                line=dict(color=highlight_color, width=3),
                fillcolor="rgba(59, 130, 246, 0.25)",
            )
            fig_last_week.update_layout(template=plotly_template)
            render_plotly(fig_last_week)

        if len(years) > 1:
            st.markdown("<h4 class='section-title'><span>Сравнение</span> по годам</h4>", unsafe_allow_html=True)
            selected_years: List[int] = st.multiselect(
                "Выберите годы", years, default=years, key="year_compare"
            )
            if selected_years:
                df_years = df[df["dt"].dt.year.isin(selected_years)].copy()
                df_years["year"] = df_years["dt"].dt.year.astype(str)
                daily_year_counts = (
                    df_years.groupby([df_years["dt"].dt.date, "year"])
                    .size()
                    .reset_index(name="count")
                )
                daily_year_counts["date"] = pd.to_datetime(daily_year_counts["dt"])
                daily_year_counts.drop(columns=["dt"], inplace=True)
                color_palette = px.colors.qualitative.Vivid
                year_color_map = {
                    str(year): (
                        highlight_color if year == 2025 else color_palette[i % len(color_palette)]
                    )
                    for i, year in enumerate(sorted(selected_years))
                }
                fig_yearly_trend = px.line(
                    daily_year_counts,
                    x="date",
                    y="count",
                    color="year",
                    labels={"date": "Дата", "count": "Сообщений", "year": "Год"},
                    color_discrete_map=year_color_map,
                )
                fig_yearly_trend.update_traces(mode="lines", line_shape="spline")
                fig_yearly_trend.update_layout(template=plotly_template, hovermode="x unified")
                for trace in fig_yearly_trend.data:
                    if trace.name == "2025":
                        trace.update(line=dict(width=4))
                    else:
                        trace.update(line=dict(width=2, dash="dot"))

                year_type_counts = (
                    df_years.groupby(["year", "type"])
                    .size()
                    .reset_index(name="count")
                )
                year_type_counts["type_label"] = year_type_counts["type"].map(
                    lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["name"]
                )
                year_type_counts = year_type_counts.sort_values("year")
                fig_yearly_types = px.area(
                    year_type_counts,
                    x="year",
                    y="count",
                    color="type_label",
                    groupnorm="fraction",
                    labels={"year": "Год", "count": "Доля сообщений", "type_label": "Тип"},
                    color_discrete_map={
                        label: type_color_map.get(label, highlight_color)
                        for label in year_type_counts["type_label"].unique()
                    },
                )
                fig_yearly_types.update_layout(
                    template=plotly_template,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                )

                yearly_cols = st.columns(2)
                render_plotly(fig_yearly_trend, yearly_cols[0])
                render_plotly(fig_yearly_types, yearly_cols[1])

    with media_tab:
        st.markdown("<h3 class='section-title'><span>Медиа</span> активность</h3>", unsafe_allow_html=True)
        if media_df.empty:
            st.info("Нет медиа-сообщений в выбранном наборе данных.")
        else:
            media_cols = st.columns((1.2, 1))
            media_counts = (
                media_df["type"].value_counts().reset_index(name="count").rename(columns={"index": "type"})
            )
            media_counts["type_label"] = media_counts["type"].map(
                lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["name"]
            )
            media_counts["color"] = media_counts["type"].map(
                lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["color"]
            )
            media_counts["share"] = media_counts["count"] / media_counts["count"].sum() * 100
            media_counts = media_counts.sort_values("count", ascending=True)
            media_counts["share_label"] = media_counts["share"].map(lambda x: f"{x:.1f}%")

            fig_media_bar = px.bar(
                media_counts,
                x="count",
                y="type_label",
                orientation="h",
                text="share_label",
                color="type_label",
                color_discrete_map={row["type_label"]: row["color"] for _, row in media_counts.iterrows()},
                labels={"count": "Количество", "type_label": "Тип медиа"},
            )
            fig_media_bar.update_traces(textposition="outside")
            fig_media_bar.update_layout(
                template=plotly_template,
                showlegend=False,
                margin=dict(t=30, b=10, l=0, r=10),
            )
            render_plotly(fig_media_bar, media_cols[0])

            if not monthly_types.empty:
                monthly_media = monthly_types[monthly_types["type"].isin(media_types)]
                if not monthly_media.empty:
                    ordered_media_months = (
                        monthly_media.sort_values("month_order")["month_label"].unique().tolist()
                    )
                    fig_media_trend = px.area(
                        monthly_media.sort_values("month_order"),
                        x="month_label",
                        y="count",
                        color="type_label",
                        line_group="type_label",
                        labels={"month_label": "Месяц", "count": "Сообщений"},
                    )
                    fig_media_trend.update_layout(
                        template=plotly_template,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
                        xaxis=dict(categoryorder="array", categoryarray=ordered_media_months),
                    )
                    render_plotly(fig_media_trend, media_cols[1])

            media_extra_cols = st.columns((1, 1))
            weekday_counts = (
                media_df.assign(weekday=media_df["dt"].dt.weekday)
                .groupby(["weekday", "type"])
                .size()
                .reset_index(name="count")
            )
            if not weekday_counts.empty:
                weekday_counts["weekday_label"] = weekday_counts["weekday"].map(WEEKDAY_NAMES)
                weekday_counts["type_label"] = weekday_counts["type"].map(
                    lambda value: TYPE_DETAILS.get(value, DEFAULT_TYPE_DETAIL)["name"]
                )
                fig_weekday = px.bar(
                    weekday_counts,
                    x="weekday_label",
                    y="count",
                    color="type_label",
                    barmode="stack",
                    labels={"weekday_label": "День недели", "count": "Сообщений", "type_label": "Тип"},
                    color_discrete_map=type_color_map,
                )
                fig_weekday.update_layout(
                    template=plotly_template,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(t=30, b=10, l=0, r=10),
                    xaxis=dict(categoryorder="array", categoryarray=[WEEKDAY_NAMES[i] for i in range(7)]),
                )
                render_plotly(fig_weekday, media_extra_cols[0])
            else:
                media_extra_cols[0].info("Недостаточно данных для распределения по дням недели.")

            media_sender_df = media_df[media_df["sender"].notna()]
            if not media_sender_df.empty:
                top_media_senders = (
                    media_sender_df.groupby("sender")
                    .size()
                    .reset_index(name="count")
                    .sort_values("count", ascending=False)
                    .head(10)
                )
                fig_media_senders = px.bar(
                    top_media_senders.sort_values("count"),
                    x="count",
                    y="sender",
                    orientation="h",
                    text="count",
                    color="count",
                    color_continuous_scale="Aggrnyl",
                    labels={"count": "Медиа сообщений", "sender": "Отправитель"},
                )
                fig_media_senders.update_traces(textposition="outside")
                fig_media_senders.update_layout(
                    template=plotly_template,
                    coloraxis_showscale=False,
                    margin=dict(t=30, b=10, l=0, r=10),
                )
                render_plotly(fig_media_senders, media_extra_cols[1])
            else:
                media_extra_cols[1].info("Нет данных об отправителях медиа-сообщений.")

        detail_cols = st.columns(2)
        with detail_cols[0]:
            if voice_df.empty:
                st.info("Нет голосовых сообщений.")
            else:
                st.markdown("<div class='tag-badge'>Голосовые сообщения</div>", unsafe_allow_html=True)
                plot_media_stats(voice_df, "голосовых сообщений", plotly_template)
        with detail_cols[1]:
            if video_df.empty:
                st.info("Нет видеосообщений.")
            else:
                st.markdown("<div class='tag-badge'>Видеосообщения</div>", unsafe_allow_html=True)
                plot_media_stats(video_df, "видеосообщений", plotly_template)

    with text_tab:
        st.markdown("<h3 class='section-title'><span>Текстовая</span> статистика</h3>", unsafe_allow_html=True)
        if text_df.empty:
            st.info("Нет текстовых сообщений.")
        else:
            text_messages = text_df[text_df["sender"].notna()].copy()
            if text_messages.empty:
                st.info("Нет текстовых сообщений с указанием отправителя.")
            else:
                sender_metrics = (
                    text_messages.groupby("sender")
                    .agg(
                        message_count=("text_length", "size"),
                        avg_length=("text_length", "mean"),
                        total_chars=("text_length", "sum"),
                    )
                    .reset_index()
                    .sort_values("message_count", ascending=False)
                )

                top10_metrics = sender_metrics.head(10)
                if not top10_metrics.empty:
                    sender_cols = st.columns((1.2, 1.1))
                    fig_top_counts = px.bar(
                        top10_metrics.sort_values("message_count"),
                        x="message_count",
                        y="sender",
                        orientation="h",
                        text="message_count",
                        color="avg_length",
                        color_continuous_scale="Blues",
                        labels={
                            "message_count": "Сообщений",
                            "sender": "Отправитель",
                            "avg_length": "Средняя длина",
                        },
                    )
                    fig_top_counts.update_layout(
                        template=plotly_template,
                        coloraxis_showscale=False,
                        margin=dict(l=0, r=20, t=40, b=0),
                    )
                    fig_top_counts.update_traces(textposition="outside")
                    render_plotly(fig_top_counts, sender_cols[0])

                    detail_metrics = top10_metrics.copy().sort_values("total_chars", ascending=False)
                    detail_metrics["total_chars_k"] = (detail_metrics["total_chars"] / 1000).round(1)
                    detail_metrics["avg_length_label"] = detail_metrics["avg_length"].map(
                        lambda value: f"{value:.0f} симв."
                    )
                    fig_sender_detail = px.bar(
                        detail_metrics,
                        x="sender",
                        y="total_chars_k",
                        color="avg_length",
                        color_continuous_scale="Plasma",
                        text="avg_length_label",
                        labels={
                            "sender": "Отправитель",
                            "total_chars_k": "Всего символов (тыс.)",
                            "avg_length": "Средняя длина",
                        },
                    )
                    fig_sender_detail.update_traces(textposition="outside")
                    fig_sender_detail.update_layout(
                        template=plotly_template,
                        coloraxis_colorbar=dict(title="Средняя длина"),
                        margin=dict(l=0, r=10, t=40, b=0),
                    )
                    render_plotly(fig_sender_detail, sender_cols[1])

                monthly_sender = (
                    text_messages.assign(month=text_messages["dt"].dt.to_period("M").dt.to_timestamp())
                    .groupby(["month", "sender"])
                    .size()
                    .reset_index(name="count")
                )
                top5_senders = sender_metrics.head(5)["sender"].tolist()
                monthly_top = monthly_sender[monthly_sender["sender"].isin(top5_senders)]
                if not monthly_top.empty:
                    fig_monthly_mix = px.area(
                        monthly_top.sort_values("month"),
                        x="month",
                        y="count",
                        color="sender",
                        labels={"month": "Месяц", "count": "Сообщений", "sender": "Отправитель"},
                    )
                    fig_monthly_mix.update_layout(
                        template=plotly_template,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center"),
                    )
                    render_plotly(fig_monthly_mix)

                max_length = int(text_messages["text_length"].max()) if not text_messages.empty else 0
                base_edges = [0, 50, 100, 200, 400, 800, 1600]
                if max_length > base_edges[-1]:
                    bin_edges = base_edges + [max_length + 1]
                else:
                    bin_edges = base_edges + [base_edges[-1] + 1]
                bucket_labels = []
                for start, end in zip(bin_edges[:-1], bin_edges[1:]):
                    if end >= max_length + 1:
                        bucket_labels.append(f"{start}+")
                    else:
                        bucket_labels.append(f"{start}–{end - 1}")

                length_buckets = pd.cut(
                    text_messages["text_length"],
                    bins=bin_edges,
                    labels=bucket_labels,
                    right=False,
                    include_lowest=True,
                )
                length_counts = (
                    length_buckets.value_counts(sort=False)
                    .rename_axis("length_bucket")
                    .reset_index(name="count")
                )
                length_counts = length_counts[length_counts["count"] > 0]
                if not length_counts.empty:
                    length_counts["length_bucket"] = length_counts["length_bucket"].astype(str)
                    fig_length_distribution = px.bar(
                        length_counts,
                        x="length_bucket",
                        y="count",
                        text="count",
                        labels={"length_bucket": "Диапазон длины", "count": "Сообщений"},
                        color="count",
                        color_continuous_scale="Blues",
                    )
                    fig_length_distribution.update_traces(textposition="outside")
                    fig_length_distribution.update_layout(
                        template=plotly_template,
                        margin=dict(t=40, b=0, l=0, r=0),
                        coloraxis_showscale=False,
                    )
                    render_plotly(fig_length_distribution)
                else:
                    st.info("Недостаточно данных для распределения по длине сообщений.")

                st.markdown("Топ-10 отправителей по текстовым сообщениям")
                st.dataframe(
                    top10_metrics[["sender", "message_count", "avg_length", "total_chars"]]
                    .rename(
                        columns={
                            "sender": "Отправитель",
                            "message_count": "Сообщений",
                            "avg_length": "Средняя длина",
                            "total_chars": "Всего символов",
                        }
                    ),
                    width="stretch",
                )

    with reactions_tab:
        st.markdown("<h3 class='section-title'><span>Реакции</span> сообщества</h3>", unsafe_allow_html=True)
        if total_reactions == 0:
            st.info("В данных нет реакций.")
        else:
            st.markdown(
                f"""
                <div class="metric-card" style="margin-bottom: 1rem;">
                    <div class="metric-icon">💟</div>
                    <div>
                        <p class="metric-subtitle">Всего реакций</p>
                        <h3>{total_reactions}</h3>
                        <p class="metric-subtitle">Кто чаще всех оставляет эмодзи и какие из них любимые.</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            reaction_cols = st.columns((1.1, 1))
            if reaction_emoji_counter:
                top_reaction_emojis = reaction_emoji_counter.most_common(12)
                df_reaction_emojis = pd.DataFrame(top_reaction_emojis, columns=["Эмодзи", "count"])
                fig_reaction = px.treemap(
                    df_reaction_emojis,
                    path=["Эмодзи"],
                    values="count",
                    color="count",
                    color_continuous_scale="Sunset",
                    hover_data={"count": True},
                )
                fig_reaction.update_layout(template=plotly_template, margin=dict(t=20, l=0, r=0, b=0))
                render_plotly(fig_reaction, reaction_cols[0])

            if reaction_list:
                df_reactions = pd.DataFrame(reaction_list)
                user_reaction_counts = (
                    df_reactions.groupby("user")
                    .size()
                    .reset_index(name="count")
                )
                if not user_reaction_counts.empty:
                    top_users = user_reaction_counts.sort_values("count", ascending=False).head(15)
                    fig_user_reactions = px.bar(
                        top_users,
                        x="count",
                        y="user",
                        orientation="h",
                        text="count",
                        color="count",
                        color_continuous_scale="Aggrnyl",
                        labels={"user": "Пользователь", "count": "Реакций"},
                    )
                    fig_user_reactions.update_layout(
                        template=plotly_template,
                        coloraxis_showscale=False,
                        margin=dict(l=0, r=20, t=40, b=0),
                    )
                    fig_user_reactions.update_traces(textposition="outside")
                    render_plotly(fig_user_reactions, reaction_cols[1])

    with extras_tab:
        st.markdown("<h3 class='section-title'><span>Дополнительные</span> инсайты</h3>", unsafe_allow_html=True)
        extras_cols = st.columns(2)

        with extras_cols[0]:
            st.markdown("#### Стикеры")
            if sticker_df.empty:
                st.info("Стикеры не найдены.")
            else:
                sticker_sender = sticker_df[sticker_df["sender"].notna()]
                if not sticker_sender.empty:
                    sticker_counts = (
                        sticker_sender.groupby("sender")
                        .size()
                        .reset_index(name="count")
                    )
                    sticker_top = sticker_counts.sort_values("count", ascending=False).head(15)
                    fig_sticker = px.bar(
                        sticker_top,
                        x="count",
                        y="sender",
                        orientation="h",
                        text="count",
                        color="sender",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        labels={"sender": "Отправитель", "count": "Стикеров"},
                    )
                    fig_sticker.update_layout(
                        template=plotly_template,
                        showlegend=False,
                        margin=dict(l=0, r=20, t=40, b=0),
                    )
                    render_plotly(fig_sticker)

                sticker_emojis = sticker_df["sticker_emoji"].dropna()
                if not sticker_emojis.empty:
                    emoji_counts = sticker_emojis.value_counts().reset_index()
                    emoji_counts.columns = ["sticker_emoji", "count"]
                    emoji_counts = emoji_counts.head(15)
                    fig_sticker_emoji = px.sunburst(
                        emoji_counts,
                        path=["sticker_emoji"],
                        values="count",
                        color="count",
                        color_continuous_scale="Plasma",
                    )
                    fig_sticker_emoji.update_layout(template=plotly_template, margin=dict(t=0, l=0, r=0, b=0))
                    render_plotly(fig_sticker_emoji)
                st.markdown(
                    f"<div class='tag-badge'>Всего стикеров: {len(sticker_df)}</div>",
                    unsafe_allow_html=True,
                )

        with extras_cols[1]:
            st.markdown("#### Эмодзи")
            if not emojis_list:
                st.info("Эмодзи в текстовых сообщениях не найдены.")
            else:
                top_emojis = emoji_counter.most_common(15)
                df_emoji = pd.DataFrame(top_emojis, columns=["Эмодзи", "count"])
                fig_emoji = px.treemap(
                    df_emoji,
                    path=["Эмодзи"],
                    values="count",
                    color="count",
                    color_continuous_scale="Viridis",
                )
                fig_emoji.update_layout(template=plotly_template, margin=dict(t=20, l=0, r=0, b=0))
                render_plotly(fig_emoji)
                st.markdown(
                    f"<div class='tag-badge'>Всего эмодзи: {total_emojis}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("#### Топ-20 самых частых слов")
        if corpus:
            stop_words = load_stopwords()
            stop_words.add("это")
            top_words = get_word_frequency(corpus, stop_words=stop_words, top_n=20)
            if top_words:
                df_words = pd.DataFrame(top_words, columns=["Слово", "count"])
                fig_words = px.treemap(
                    df_words,
                    path=["Слово"],
                    values="count",
                    color="count",
                    color_continuous_scale="Teal",
                )
                fig_words.update_layout(template=plotly_template, margin=dict(t=20, l=0, r=0, b=0))
                render_plotly(fig_words)

    with raw_tab:
        st.markdown("<h3 class='section-title'><span>Данные</span> набора</h3>", unsafe_allow_html=True)
        st.caption("Первые 100 строк обработанного датасета")
        st.dataframe(df.head(100), width="stretch")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Скачать CSV",
            csv,
            "telegram_data.csv",
            "text/csv",
        )

