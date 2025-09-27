from typing import Tuple, Optional, List, Dict

import pandas as pd
import streamlit as st
from datetime import datetime
import re
from collections import Counter

from src.utils import extract_emojis


def process_json(
    data: dict,
) -> Tuple[
    Optional[pd.DataFrame], Optional[str], Optional[pd.DataFrame], Optional[List[str]]
]:
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
    messages: List[dict] = data.get("messages", [])
    rows: List[dict] = []
    text_corpus: List[str] = []
    emojis_list: List[str] = []
    total: int = len(messages)
    progress_bar = st.progress(0)

    for i, msg in enumerate(messages):
        progress_bar.progress((i + 1) / total)
        if "date" not in msg:
            continue
        if msg.get("type") and msg.get("type") != "message":
            # пропускаем сервисные события (например, смена фото, добавление участников)
            continue
        try:
            dt: datetime = datetime.fromisoformat(msg["date"])
        except Exception as e:
            st.write(f"Ошибка при обработке даты {msg.get('date')}: {e}")
            continue

        sender: Optional[str] = msg.get("from")
        if not sender or sender.strip() == "" or sender.lower() == "unknown":
            sender = None

        mtype: str = "text"
        duration: Optional[float] = None
        sticker_emoji: Optional[str] = msg.get("sticker_emoji")
        media_type: Optional[str] = msg.get("media_type")
        mime_type: str = (msg.get("mime_type") or "").lower()
        file_path = msg.get("file")

        if media_type == "voice_message" or "audio" in mime_type or mime_type.endswith("ogg"):
            mtype = "audio/voice"
            duration = msg.get("duration_seconds") or msg.get("duration")
        elif media_type == "video_message" or "video" in mime_type:
            mtype = "video"
            duration = msg.get("duration_seconds") or msg.get("duration")
        elif media_type == "sticker" or sticker_emoji:
            mtype = "sticker"
        elif media_type in {"animation", "gif"} or mime_type in {"image/gif", "video/mp4"}:
            mtype = "video"
        elif "photo" in msg and msg["photo"]:
            mtype = "photo"
        elif isinstance(file_path, str) and file_path:
            if mime_type.startswith("image/") and mime_type != "image/webp":
                mtype = "photo"
            elif mime_type.startswith("video/"):
                mtype = "video"
            elif mime_type in {"image/webp", "application/x-tgsticker"}:
                mtype = "sticker"
            else:
                mtype = "file"
        elif "document" in msg:
            mtype = "file"

        row: Dict = {
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

        if mtype == "text":
            text_content = msg.get("text", "")
            text: str = ""
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
            emojis_found: List[str] = extract_emojis(text)
            emojis_list.extend(emojis_found)

        rows.append(row)

    if not rows:
        st.error("Нет данных для обработки.")
        return None, None, None, None

    df = pd.DataFrame(rows)
    if "sticker_emoji" in df.columns:
        sticker_mask = df["sticker_emoji"].notna() & (df["sticker_emoji"] != "")
        df.loc[sticker_mask, "type"] = "sticker"

    daily_counts = df.groupby("date").size().reset_index(name="count")
    start_date = daily_counts["date"].min()
    end_date = daily_counts["date"].max()
    all_dates = pd.DataFrame({"date": pd.date_range(start_date, end_date)})
    all_dates["date"] = all_dates["date"].dt.date
    daily_counts = pd.merge(all_dates, daily_counts, on="date", how="left").fillna(0)
    daily_counts["count"] = daily_counts["count"].astype(int)
    daily_counts["date_dt"] = pd.to_datetime(daily_counts["date"])

    return daily_counts, " ".join(text_corpus), df, emojis_list


def get_word_frequency(
    text: str, stop_words: Optional[set] = None, top_n: int = 20
) -> List[Tuple[str, int]]:
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
    text = re.sub(r"[^а-яёa-z\s]", "", text)
    words: List[str] = text.split()
    if stop_words is None:
        stop_words = set()
    words = [w for w in words if w not in stop_words]
    counter: Counter = Counter(words)

    return counter.most_common(top_n)
