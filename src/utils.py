import emoji
from nltk.corpus import stopwords
import nltk
import streamlit as st
import plotly.express as px


def load_stopwords():
    """
    Загружает и возвращает множество стоп-слов для русского и английского языков из файлов и с использованием NLTK.
    Если стоп-слова отсутствуют, происходит их загрузка.

    Returns:
        set: Множество стоп-слов.
    """

    try:
        with open("stopwords\\stopwords-ru.txt", "r", encoding="utf-8") as file:
            stopwords_ru = file.read().splitlines()

    except FileNotFoundError:
        stopwords_ru = []

    try:
        with open("stopwords\\stopwords_en.txt", "r", encoding="utf-8") as file:
            stopwords_en = file.read().splitlines()

    except FileNotFoundError:
        stopwords_en = []

    try:
        nltk_stopwords = stopwords.words("russian") + stopwords.words("english")
    except LookupError:
        nltk.download("stopwords")
        nltk_stopwords = stopwords.words("russian") + stopwords.words("english")

    return set(stopwords_ru + stopwords_en + nltk_stopwords)


def extract_emojis(text):
    """
    Извлекает эмодзи из переданного текста.

    Parameters:
        text (str): Текст для анализа.

    Returns:
        list: Список эмодзи, найденных в тексте.
    """
    return [char for char in text if char in emoji.EMOJI_DATA]


def center_text(text, tag="p"):
    """
    Отображает текст с заданным HTML-тегом и центровкой.
    """
    st.markdown(
        f"<{tag} style='text-align: center;'>{text}</{tag}>", unsafe_allow_html=True
    )


def format_russian_date(dt):
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
    formatted = dt.strftime("%d %b %Y")
    for eng, rus in month_names.items():
        formatted = formatted.replace(eng, rus)
    return formatted


def plot_media_stats(media_df, label):
    """
    Выводит статистику для заданного типа медиа.
    label: строка, описывающая тип сообщений, например:
           "голосовых сообщений" или "видеосообщений".
    """
    if not media_df.empty and media_df["duration"].notna().any():
        avg_duration = media_df["duration"].dropna().mean()
        center_text(f"Средняя длительность {label}: {avg_duration:.1f} сек.", tag="p")
        center_text(f"Количество {label}: {len(media_df)}", tag="p")

        # Группировка данных по отправителям, у которых есть информация о длительности
        media_sender_df = media_df[
            media_df["sender"].notna() & media_df["duration"].notna()
        ]
        if not media_sender_df.empty:
            media_counts = (
                media_sender_df.groupby("sender").size().reset_index(name="count")
            )
            fig_count = px.bar(
                media_counts,
                x="sender",
                y="count",
                title=f"Количество {label} по отправителям",
                labels={"sender": "Отправитель", "count": "Количество сообщений"},
            )
            st.plotly_chart(fig_count, use_container_width=True)

            media_duration = (
                media_sender_df.groupby("sender")["duration"].mean().reset_index()
            )
            media_duration.columns = ["sender", "avg_duration"]
            fig_duration = px.bar(
                media_duration,
                x="sender",
                y="avg_duration",
                title=f"Средняя длительность {label} по отправителям",
                labels={
                    "sender": "Отправитель",
                    "avg_duration": "Средняя длительность (сек)",
                },
            )
            st.plotly_chart(fig_duration, use_container_width=True)
        else:
            st.info(
                f"Нет достаточной информации для статистики {label} по отправителям."
            )
    else:
        st.info(
            f"{label.capitalize()} отсутствуют или не содержат информации о длительности."
        )
