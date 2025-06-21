# utils/__init__.py
from .file_utils import *
from .logger import setup_logger

import os


def ensure_dir_exists(path):
    """
    Проверяет, существует ли папка, и создаёт её, если нет
    """
    if path:
        os.makedirs(path, exist_ok=True)
        return True
    return False