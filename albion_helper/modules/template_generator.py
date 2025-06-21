# albion_helper/modules/template_generator.py

import os
import cv2
import json
import logging
from pathlib import Path

logger = logging.getLogger("AlbionHelperLogger")

def save_effect_template(x, y, width, height, label):
    """
    Делает скриншот области и сохраняет как PNG + JSON-данные.
    Возвращает имя сохранённого файла.
    """
    try:
        # Сделать скриншот
        from modules.screenshot_handler import capture_screen
        image = capture_screen(x, y, width, height)
        if image is None:
            logger.error("Не удалось сделать скриншот для сохранения темплейта")
            return None

        # Путь к папке с эффектами
        template_dir = Path("data/templates/effects")
        template_dir.mkdir(parents=True, exist_ok=True)

        # Имя файла
        safe_label = label.lower().replace(" ", "_")
        filename = f"{safe_label}_{width}x{height}.png"
        full_path = template_dir / filename

        # Сохранить изображение
        cv2.imwrite(str(full_path), image)
        logger.info(f"Темплейт сохранён: {full_path}")

        return str(full_path)

    except Exception as e:
        logger.error(f"Ошибка при сохранении темплейта: {e}")
        return None