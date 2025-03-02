import streamlit as st
import json
import pandas as pd
import plotly.express as px
from datetime import timedelta
from collections import Counter
from src.telegram_analysis import process_json, get_word_frequency
from src.utils import load_stopwords, center_text, format_russian_date, plot_media_stats


def run_app():
    """
    Запускает Streamlit-приложение для анализа экспорта переписки Telegram в формате JSON.
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

    # -----------------------------------------------
    # 1. Общая статистика: ежедневная активность, за неделю и по часам
    # -----------------------------------------------
    # Добавляем столбец с датой в нужном формате для подсказок
    daily_counts["date_str"] = daily_counts["date_dt"].apply(format_russian_date)

    center_text("Активность по дням", tag="h3")
    # Позволяем пользователю выбрать интервал подписей (в месяцах)
    tick_interval_months = st.slider(
        "Интервал подписей (в месяцах)", min_value=1, max_value=12, value=3, step=1
    )

    fig_daily = px.bar(
        daily_counts,
        x="date_dt",
        y="count",
        labels={"date_dt": "Дата", "count": "Количество сообщений"},
        custom_data=["date_str"],
    )
    # Переопределяем hover-подписи, чтобы отображать русские даты
    fig_daily.update_traces(
        hovertemplate="Дата: %{customdata[0]}<br>Количество сообщений: %{y}"
    )

    # Рассчитаем метки оси X с шагом, выбранным через слайдер
    min_date = daily_counts["date_dt"].min()
    max_date = daily_counts["date_dt"].max()
    ticks = []
    current_tick = pd.Timestamp(min_date).normalize()
    while current_tick <= max_date:
        ticks.append(current_tick)
        current_tick += pd.DateOffset(months=tick_interval_months)
    tick_texts = [format_russian_date(t) for t in ticks]
    fig_daily.update_xaxes(tickmode="array", tickvals=ticks, ticktext=tick_texts)
    st.plotly_chart(fig_daily, use_container_width=True)

    # Сообщения за последнюю неделю, отсчитывая от сегодняшнего дня.
    today = pd.Timestamp.today().normalize()
    last_week_start = today - timedelta(days=6)
    # Формируем полный диапазон дат за последние 7 дней
    last_week_dates = pd.date_range(last_week_start, today)
    last_week_df = pd.DataFrame({"date_dt": last_week_dates})
    # Объединяем с данными, заполняем пропуски нулями
    last_week_data = pd.merge(
        last_week_df, daily_counts[["date_dt", "count"]], on="date_dt", how="left"
    ).fillna(0)
    # Приводим count к целому типу
    last_week_data["count"] = last_week_data["count"].astype(int)

    if not last_week_data.empty:
        center_text("Детализация за неделю", tag="h3")
        fig_last_week = px.bar(
            last_week_data,
            x="date_dt",
            y="count",
            labels={"date_dt": "Дата", "count": "Количество сообщений"},
        )
        # Обновляем подписи по оси X для последней недели
        fig_last_week.update_xaxes(
            tickformat="%d %b",  # День и сокращённое название месяца
        )
        st.plotly_chart(fig_last_week, use_container_width=True)
    else:
        st.info("Нет данных за последние 7 дней.")

    center_text("Активность по часам", tag="h3")
    hourly_counts = df.groupby("hour").size().reset_index(name="count")
    all_hours = pd.DataFrame({"hour": list(range(24))})
    hourly_counts = pd.merge(all_hours, hourly_counts, on="hour", how="left").fillna(0)
    hourly_counts["count"] = hourly_counts["count"].astype(int)
    fig_hourly = px.bar(
        hourly_counts,
        x="hour",
        y="count",
        labels={"hour": "Час дня", "count": "Количество сообщений"},
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    # -----------------------------------------------
    # 2. Статистика по типам медиа
    # -----------------------------------------------
    st.markdown(
        "<h3 style='text-align: center;'>Стастика по медиа сообщениям</h3>",
        unsafe_allow_html=True,
    )
    media_df = df[df["type"].isin(["photo", "video", "sticker", "file"])]
    if not media_df.empty:
        media_counts = media_df["type"].value_counts().reset_index()
        media_counts.columns = ["type", "count"]
        fig_media = px.pie(
            media_counts,
            names="type",
            values="count",
        )
        st.plotly_chart(fig_media, use_container_width=True)
    else:
        st.info("Нет медиа сообщений для анализа.")

    # -----------------------------------------------
    # 3. Голосовые сообщения
    # -----------------------------------------------
    center_text("Статистика по голосовым сообщениям", tag="h3")
    voice_df = df[df["type"] == "audio/voice"]
    plot_media_stats(voice_df, "голосовых сообщений")

    # -----------------------------------------------
    # 4. Видеосообщения
    # -----------------------------------------------
    center_text("Статистика по видеосообщениям", tag="h3")
    video_df = df[df["type"] == "video"]
    plot_media_stats(video_df, "видеосообщений")

    # -----------------------------------------------
    # 5. Статистика по текстовым сообщениям (включая распределение по отправителям)
    # -----------------------------------------------
    center_text("Статистика по текстовым сообщениям", tag="h3")
    text_df = df[df["type"] == "text"]
    if not text_df.empty:
        overall_avg_length = text_df["text_length"].mean()
        center_text(
            f"Общая средняя длина текстового сообщения: {overall_avg_length:.1f} символов",
            tag="p",
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
    else:
        st.info("Нет текстовых сообщений для анализа.")

    # -----------------------------------------------
    # 6. Стикеры
    # -----------------------------------------------
    center_text("Статистика по стикерам", tag="h3")
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
        top_n = 10
        emoji_counts = emoji_counts.head(top_n)
        fig_sticker_emoji = px.bar(
            emoji_counts,
            x="count",
            y="sticker_emoji",
            orientation="h",
            title="Топ-10 самых популярных стикеров",
            labels={"count": "Количество", "sticker_emoji": "Стикер"},
            text_auto=True,
        )
        st.plotly_chart(fig_sticker_emoji, use_container_width=True)
        center_text(f"Общее количество стикеров: {len(sticker_df)}", tag="p")
    else:
        st.info("Стикеры не найдены в переписке.")

    # -----------------------------------------------
    # 7. Анализ эмодзи (в тексте)
    # -----------------------------------------------
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
        center_text(
            f"Всего эмодзи (в тексте) было использовано: {sum(emoji_counter.values())}",
            tag="p",
        )
    else:
        st.info("Эмодзи в тексте не найдены.")

    # -----------------------------------------------
    # 8. Анализ реакций (эмодзи в reactions)
    # -----------------------------------------------
    center_text("Статистика по реакциям (эмодзи)", tag="h3")

    reaction_emoji_counter = Counter()
    reaction_list = []
    for msg in data.get("messages", []):
        reactions = msg.get("reactions", [])
        for r in reactions:
            if r.get("type") == "emoji":
                emoji_used = r.get("emoji")
                count = r.get("count", 0)
                reaction_emoji_counter[emoji_used] += count
                for recent_info in r.get("recent", []):
                    user_from = recent_info.get("from")
                    if user_from:
                        reaction_list.append({"user": user_from, "emoji": emoji_used})
    # Суммарное количество эмоций в реакциях
    total_reactions = sum(reaction_emoji_counter.values())
    center_text(f"Всего эмоций поставлено: {total_reactions}", tag="p")

    if reaction_emoji_counter:
        top_reaction_emojis = reaction_emoji_counter.most_common(10)
        df_reaction_emojis = pd.DataFrame(
            top_reaction_emojis, columns=["Эмодзи", "count"]
        )
        fig_reaction = px.bar(
            df_reaction_emojis,
            x="Эмодзи",
            y="count",
            title="Топ-10 эмодзи в реакциях",
            labels={"Эмодзи": "Эмодзи", "count": "Количество"},
        )
        st.plotly_chart(fig_reaction, use_container_width=True)
    else:
        st.info("Реакций (эмодзи) в сообщениях не обнаружено.")

    if reaction_list:
        df_reactions = pd.DataFrame(reaction_list)
        user_reaction_counts = (
            df_reactions.groupby("user").size().reset_index(name="count")
        )
        fig_user_reactions = px.bar(
            user_reaction_counts,
            x="user",
            y="count",
            title="Количество использованных эмодзи по пользователям (recent)",
            labels={"user": "Пользователь", "count": "Количество эмодзи"},
        )
        st.plotly_chart(fig_user_reactions, use_container_width=True)

    # -----------------------------------------------
    # 9. Частота слов
    # -----------------------------------------------
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
