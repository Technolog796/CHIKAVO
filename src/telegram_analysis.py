import pandas as pd
import streamlit as st
from datetime import datetime
import re
from collections import Counter
from src.utils import extract_emojis


def process_json(data):
    """
    Обрабатывает JSON-данные экспорта из Telegram и извлекает информацию по сообщениям.

    Parameters:
        data (dict): Словарь с данными экспорта Telegram.

    Returns:
        tuple: Кортеж из:
            - daily_counts (DataFrame): Данные с агрегированным количеством сообщений по датам.
            - corpus (str): Объединённый текст всех сообщений.
            - df (DataFrame): Подробная таблица с информацией по каждому сообщению.
            - emojis_list (list): Список эмодзи, извлечённых из текстовых сообщений.
    """
    messages = data.get("messages", [])
    rows = []
    text_corpus = []
    emojis_list = []
    total = len(messages)
    progress_bar = st.progress(0)

    for i, msg in enumerate(messages):
        progress_bar.progress((i + 1) / total)
        if "date" not in msg:
            continue
        try:
            dt = datetime.fromisoformat(msg["date"])
        except Exception as e:
            st.write(f"Ошибка при обработке даты {msg.get('date')}: {e}")
            continue

        # Получаем отправителя; если отсутствует или равен "Unknown", оставляем как None
        sender = msg.get("from")
        if not sender or sender.strip() == "" or sender.lower() == "unknown":
            sender = None

        # Инициализация полей по умолчанию
        mtype = "text"
        duration = None
        sticker_emoji = None

        media_type = msg.get("media_type")
        if media_type == "voice_message":
            mtype = "audio/voice"
            duration = msg.get("duration_seconds")
        elif media_type == "video_message":
            mtype = "video"
            duration = msg.get("duration_seconds")
        elif media_type == "sticker":
            mtype = "sticker"
            sticker_emoji = msg.get("sticker_emoji")
        elif "photo" in msg:
            mtype = "photo"
        elif "document" in msg:
            mtype = "file"
        else:
            mtype = "text"

        row = {
            "dt": dt,
            "date": dt.date(),
            "hour": dt.hour,
            "type": mtype,
            "sender": sender,
            "duration": duration,
            "sticker_emoji": sticker_emoji,
            "text": "",
            "text_length": 0,
        }

        # Обработка текстовых сообщений
        if mtype == "text":
            text_content = msg.get("text", "")
            text = ""
            if isinstance(text_content, list):
                for item in text_content:
                    if isinstance(item, dict) and "text" in item:
                        text += item["text"] + " "
                    elif isinstance(item, str):
                        text += item + " "
                text = text.strip()
            elif isinstance(text_content, str):
                text = text_content
            row["text"] = text
            row["text_length"] = len(text)
            if text:
                text_corpus.append(text)
            # Извлечение эмодзи из текста
            emojis_found = extract_emojis(text)
            emojis_list.extend(emojis_found)

        rows.append(row)

    if not rows:
        st.error("Нет данных для обработки.")
        return None, None, None, None

    df = pd.DataFrame(rows)

    # Группировка сообщений по датам для построения временного ряда
    daily_counts = df.groupby("date").size().reset_index(name="count")
    start_date = daily_counts["date"].min()
    end_date = daily_counts["date"].max()
    all_dates = pd.DataFrame({"date": pd.date_range(start_date, end_date)})
    all_dates["date"] = all_dates["date"].dt.date
    daily_counts = pd.merge(all_dates, daily_counts, on="date", how="left").fillna(0)
    daily_counts["count"] = daily_counts["count"].astype(int)
    daily_counts["date_dt"] = pd.to_datetime(daily_counts["date"])

    return daily_counts, " ".join(text_corpus), df, emojis_list


def get_word_frequency(text, stop_words=None, top_n=20):
    """
    Определяет частотность слов в переданном тексте с исключением стоп-слов.

    Parameters:
        text (str): Текст для анализа.
        stop_words (set, optional): Множество стоп-слов для исключения. Если None, стоп-слова не исключаются.
        top_n (int, optional): Количество наиболее часто встречающихся слов для возврата.

    Returns:
        list: Список кортежей (слово, частота) для top_n слов.
    """
    text = text.lower()
    text = re.sub(r"[^а-яa-z\s]", "", text)
    words = text.split()
    if stop_words is None:
        stop_words = set()
    words = [w for w in words if w not in stop_words]
    counter = Counter(words)
    return counter.most_common(top_n)
