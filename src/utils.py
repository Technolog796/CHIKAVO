import nltk
from nltk.corpus import stopwords
import emoji


def load_stopwords():
    """
    Загружает и возвращает множество стоп-слов для русского языка с использованием NLTK.
    Если стоп-слова отсутствуют, происходит их загрузка.

    Returns:
        set: Множество стоп-слов.
    """
    try:
        return set(stopwords.words("russian"))
    except LookupError:
        nltk.download("stopwords")
        return set(stopwords.words("russian"))


def extract_emojis(text):
    """
    Извлекает эмодзи из переданного текста.

    Parameters:
        text (str): Текст для анализа.

    Returns:
        list: Список эмодзи, найденных в тексте.
    """
    return [char for char in text if char in emoji.EMOJI_DATA]
