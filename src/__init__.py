from typing import List, Tuple, Optional, Dict

from src.app import run_app
from src.telegram_analysis import process_json, get_word_frequency
from src.utils import load_stopwords, extract_emojis

__version__ = "2.0.0"