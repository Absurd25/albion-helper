# albion_helper/utils/logger.py

import os
from datetime import datetime
import logging


def setup_logger(base_log_dir="logs"):
    """
    Настраивает логгер, который пишет логи в папку по дате запуска
    Пример: logs/2025-06-15/app_12-30.log
    """
    # Получаем текущую дату и время
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")

    # Создаём путь к папке по дате
    date_dir = os.path.join(base_log_dir, date_str)
    os.makedirs(date_dir, exist_ok=True)

    # Путь к файлу лога
    log_filename = f"app_{time_str}.log"
    log_path = os.path.join(date_dir, log_filename)

    # Настройка логгера
    logger = logging.getLogger("AlbionHelperLogger")
    logger.setLevel(logging.INFO)

    # Очищаем старые хендлеры, чтобы не было дублирования
    if logger.handlers:
        logger.handlers.clear()

    # Форматтер
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Файловый хендлер
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger