import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import timedelta
from collections import Counter
from src.telegram_analysis import process_json, get_word_frequency
from src.utils import load_stopwords


def run_app():
    """
    Запускает Streamlit-приложение для анализа экспорта перепискки Telegram в формате JSON.
    Приложение отображает статистику, графики и аналитические отчёты по сообщениям.
    """
    st.title("Анализ Telegram JSON экспорта")
    st.write("Загрузите JSON файл экспорта Telegram для анализа.")

    uploaded_file = st.file_uploader("Выберите JSON файл", type=["json"])
    if uploaded_file is None:
        return

    try:
        data = json.load(uploaded_file)
    except Exception:
        st.error("Неверный формат файла. Пожалуйста, загрузите корректный JSON файл.")
        return

    daily_counts, corpus, df, emojis_list = process_json(data)
    if daily_counts is None:
        return

    # График сообщений по дням (столбчатая диаграмма)
    st.subheader("Активность по дням")
    fig_daily = px.bar(
        daily_counts,
        x="date_dt",
        y="count",
        title="Количество сообщений по дням",
        labels={"date_dt": "Дата", "count": "Количество сообщений"},
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    # Сообщения за последнюю неделю
    end_date = daily_counts["date"].max()
    last_week_start = end_date - timedelta(days=6)
    last_week_data = daily_counts[daily_counts["date"] >= last_week_start]
    if not last_week_data.empty:
        st.subheader("Сообщения за последнюю неделю")
        fig_last_week = px.bar(
            last_week_data,
            x="date_dt",
            y="count",
            title="Количество сообщений за последнюю неделю",
            labels={"date_dt": "Дата", "count": "Количество сообщений"},
        )
        st.plotly_chart(fig_last_week, use_container_width=True)
    else:
        st.info("Нет данных за последнюю неделю.")

    # График активности по часам
    st.subheader("Активность по часам")
    hourly_counts = df.groupby("hour").size().reset_index(name="count")
    all_hours = pd.DataFrame({"hour": list(range(24))})
    hourly_counts = pd.merge(all_hours, hourly_counts, on="hour", how="left").fillna(0)
    hourly_counts["count"] = hourly_counts["count"].astype(int)
    fig_hourly = px.bar(
        hourly_counts,
        x="hour",
        y="count",
        title="Активность по часам",
        labels={"hour": "Час дня", "count": "Количество сообщений"},
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    # Статистика медиа сообщений (фото, видео, стикеры, файлы)
    st.subheader("Статистика медиа сообщений")
    media_df = df[df["type"].isin(["photo", "video", "sticker", "file"])]
    if not media_df.empty:
        media_counts = media_df["type"].value_counts().reset_index()
        media_counts.columns = ["type", "count"]
        fig_media = px.pie(
            media_counts,
            names="type",
            values="count",
            title="Распределение медиа сообщений",
        )
        st.plotly_chart(fig_media, use_container_width=True)
    else:
        st.info("Нет медиа сообщений для анализа.")

    # Общая статистика голосовых сообщений
    st.subheader("Голосовые сообщения")
    voice_df = df[df["type"] == "audio/voice"]
    if not voice_df.empty and voice_df["duration"].notna().any():
        avg_voice = voice_df["duration"].dropna().mean()
        st.write(f"Средняя длительность голосовых сообщений: {avg_voice:.1f} сек.")
        st.write(f"Количество голосовых сообщений: {len(voice_df)}")
    else:
        st.info(
            "Голосовые сообщения отсутствуют или не содержат информации о длительности."
        )

    # Статистика голосовых сообщений по отправителям
    st.subheader("Голосовые сообщения по отправителям")
    voice_sender_df = voice_df[
        voice_df["sender"].notna() & voice_df["duration"].notna()
    ]
    if not voice_sender_df.empty:
        voice_counts = (
            voice_sender_df.groupby("sender").size().reset_index(name="count")
        )
        fig_voice_count = px.bar(
            voice_counts,
            x="sender",
            y="count",
            title="Количество голосовых сообщений по отправителям",
            labels={"sender": "Отправитель", "count": "Количество сообщений"},
        )
        st.plotly_chart(fig_voice_count, use_container_width=True)
        voice_duration = (
            voice_sender_df.groupby("sender")["duration"].mean().reset_index()
        )
        voice_duration.columns = ["sender", "avg_duration"]
        fig_voice_duration = px.bar(
            voice_duration,
            x="sender",
            y="avg_duration",
            title="Средняя длительность голосовых сообщений по отправителям",
            labels={
                "sender": "Отправитель",
                "avg_duration": "Средняя длительность (сек)",
            },
        )
        st.plotly_chart(fig_voice_duration, use_container_width=True)
    else:
        st.info(
            "Нет достаточной информации для статистики голосовых сообщений по отправителям."
        )

    # Статистика видеосообщений
    st.subheader("Видеосообщения")
    video_df = df[df["type"] == "video"]
    if not video_df.empty and video_df["duration"].notna().any():
        avg_video = video_df["duration"].dropna().mean()
        st.write(f"Средняя длительность видеосообщений: {avg_video:.1f} сек.")
        st.write(f"Количество видеосообщений: {len(video_df)}")
    else:
        st.info("Видеосообщения отсутствуют или не содержат информации о длительности.")

    # Статистика по отправителям (исключая неизвестных)
    st.subheader("Статистика по отправителям")
    sender_df = df[df["sender"].notna()]
    if not sender_df.empty:
        sender_counts = sender_df["sender"].value_counts().reset_index()
        sender_counts.columns = ["sender", "count"]
        fig_sender = px.pie(
            sender_counts,
            names="sender",
            values="count",
            title="Распределение сообщений по отправителям",
        )
        st.plotly_chart(fig_sender, use_container_width=True)
    else:
        st.info("Нет информации об отправителях.")

    # Статистика по средней длине текстовых сообщений
    st.subheader("Средняя длина текстовых сообщений")
    text_df = df[df["type"] == "text"]
    if not text_df.empty:
        overall_avg_length = text_df["text_length"].mean()
        st.write(
            f"Общая средняя длина текстового сообщения: {overall_avg_length:.1f} символов"
        )
        sender_text = (
            text_df[text_df["sender"].notna()]
            .groupby("sender")["text_length"]
            .mean()
            .reset_index()
        )
        sender_text.columns = ["sender", "avg_length"]
        fig_text = px.bar(
            sender_text.sort_values("avg_length", ascending=True),
            x="avg_length",
            y="sender",
            orientation="h",
            title="Средняя длина текстовых сообщений по отправителям",
            labels={"sender": "Отправитель", "avg_length": "Средняя длина (символов)"},
        )
        st.plotly_chart(fig_text, use_container_width=True)
    else:
        st.info("Нет текстовых сообщений для анализа.")

    # Статистика стикеров
    st.subheader("Статистика стикеров")
    sticker_df = df[df["type"] == "sticker"]
    if not sticker_df.empty:
        sticker_sender = sticker_df[sticker_df["sender"].notna()]
        if not sticker_sender.empty:
            sticker_counts = (
                sticker_sender.groupby("sender").size().reset_index(name="count")
            )
            fig_sticker = px.bar(
                sticker_counts,
                x="count",
                y="sender",
                orientation="h",
                title="Количество стикеров по отправителям",
                labels={"sender": "Отправитель", "count": "Количество стикеров"},
            )
            st.plotly_chart(fig_sticker, use_container_width=True)
        sticker_emojis = sticker_df["sticker_emoji"].dropna()
        if not sticker_emojis.empty:
            emoji_counts = sticker_emojis.value_counts().reset_index()
            emoji_counts.columns = ["sticker_emoji", "count"]
            fig_sticker_emoji = px.pie(
                emoji_counts,
                names="sticker_emoji",
                values="count",
                title="Распределение стикеров по эмодзи",
            )
            st.plotly_chart(fig_sticker_emoji, use_container_width=True)
        st.write(f"Общее количество стикеров: {len(sticker_df)}")
    else:
        st.info("Стикеры не найдены в переписке.")

    # Анализ эмодзи
    st.subheader("Анализ эмодзи")
    if emojis_list:
        emoji_counter = Counter(emojis_list)
        top_emojis = emoji_counter.most_common(10)
        df_emoji = pd.DataFrame(top_emojis, columns=["Эмодзи", "count"])
        fig_emoji = px.bar(
            df_emoji,
            x="Эмодзи",
            y="count",
            title="Топ-10 эмодзи",
            labels={"Эмодзи": "Эмодзи", "count": "Количество"},
        )
        st.plotly_chart(fig_emoji, use_container_width=True)
    else:
        st.info("Эмодзи не найдены в переписке.")

    # Анализ частоты слов
    st.subheader("Самые частые слова в переписке")
    if corpus:
        stop_words = load_stopwords()
        top_words = get_word_frequency(corpus, stop_words=stop_words, top_n=20)
        if top_words:
            df_words = pd.DataFrame(top_words, columns=["Слово", "count"])
            fig_words = px.bar(
                df_words,
                x="Слово",
                y="count",
                title="Топ-20 самых частых слов",
                labels={"Слово": "Слово", "count": "Количество"},
            )
            st.plotly_chart(fig_words, use_container_width=True)
        else:
            st.info("Нет достаточного количества текста для анализа.")
    else:
        st.info("В загруженных сообщениях отсутствует текст для анализа.")
