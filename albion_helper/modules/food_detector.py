# albion_helper/modules/food_detector.py

import cv2
import numpy as np
import time
import pyautogui
import os
import json

from modules.screenshot_handler import capture_screen, find_image_difference


class FoodDetector:
    def __init__(self, logger=None):
        self.logger = logger or self._setup_fallback_logger()
        self.food_template = None
        self.auto_food_active = False
        self.temp_dir = "data/templates/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
    #
    def _setup_fallback_logger(self):
        """Если не передан логгер — создаём простой"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return logging.getLogger("FoodDetectorLogger")
    #
    def start_auto_food_mode(self, x, y, width, height):
        """
        Запуск режима авто-режима еды — делает 2 скриншота, находит эффект и предлагает сохранить
        """
        self.logger.info(f"📸 Делаем первый скриншот: X={x}, Y={y}, W={width}, H={height}")
        img1 = capture_screen(x, y, width, height)
        if img1 is None:
            self.logger.error("❌ Не удалось сделать первый скриншот")
            return None
        cv2.imwrite(os.path.join(self.temp_dir, "before_food.png"), img1)
        # Ждём подтверждения от пользователя, что он съел еду
        self.logger.info("⏳ Ожидание нажатия OK после употребления еды...")
        return {"img1": img1, "area": (x, y, width, height)}
    #
    def finish_auto_food_mode(self, data, x, y, width, height):
        """
        Второй скриншот + сравнение
        """
        self.logger.info("📸 Делаем второй скриншот (с едой)")
        img2 = capture_screen(x, y, width, height)
        if img2 is None:
            self.logger.error("❌ Не удалось сделать второй скриншот")
            return False
        #
        boxes, result_img = find_image_difference(data["img1"], img2)
        if not boxes:
            self.logger.warning("❌ Эффект от еды не найден")
            return False
        #
        food_x = data["area"][0] + boxes[0][0]
        food_y = data["area"][1] + boxes[0][1]
        food_w = boxes[0][2]
        food_h = boxes[0][3]
        #
        result_path = os.path.join(self.temp_dir, "food_diff.png")
        cv2.imwrite(result_path, result_img)
        #
        self.logger.info(f"🔍 Найдено {len(boxes)} изменений. Сохраняем первое")
        return {
            "x": food_x,
            "y": food_y,
            "width": food_w,
            "height": food_h,
            "label": "Эффект еды"
        }
        #
    def save_food_template(self, x, y, width, height, label="Эффект еды"):
        """
        Сохраняет темплейт еды в папку templates/food/
        """
        food_dir = "data/templates/food"
        os.makedirs(food_dir, exist_ok=True)
        #
        filename = f"effect_{label.lower().replace(' ', '_')}_{width}x{height}.png"
        full_path = os.path.join(food_dir, filename)
        #
        food_image = capture_screen(x, y, width, height)
        cv2.imwrite(full_path, food_image)
        #
        template_file = os.path.join(food_dir, "food_templates.json")
        new_data = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": label,
            "name": label.lower().replace(" ", "_"),
            "template": filename
        }
        #
        if os.path.exists(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []
        #
        exists = any(item["name"] == new_data["name"] for item in data)
        if not exists:
            data.append(new_data)
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        #
        self.logger.info(f"✅ Темплейт '{label}' сохранён как {filename}")
        self.food_template = {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        return True
    #
    def start_auto_eat_loop(self, interval_ms=5000):
        """
        Запускает цикл проверки наличия еды
        """
        self.auto_food_active = True
        self.logger.info(f"🍴 Авто-хавка запущено (проверка каждые {interval_ms // 1000} секунд)")
    #
    def stop_auto_eat_loop(self):
        self.auto_food_active = False
        self.logger.info("🛑 Авто-хавка остановлено")
    #
    def check_and_eat_if_needed(self):
        """
        Проверяет, активна ли еда → если нет → нажимает E
        """
        if not self.auto_food_active or self.food_template is None:
            return
        #
        x = self.food_template["x"]
        y = self.food_template["y"]
        w = self.food_template["width"]
        h = self.food_template["height"]
        # gegege
        current_img = capture_screen(x, y, w, h)
        if current_img is None:
            self.logger.warning("❌ Не удалось сделать скриншот для проверки еды")
            return
        #
        avg_color_per_row = np.average(current_img, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        avg_brightness = np.mean(avg_color)
        #
        if avg_brightness < 10:
            self.logger.info("🍽️ Еда закончилась. Нажимаю E, чтобы съесть снова...")
            pyautogui.press('e')
            time.sleep(5)  # ждём, пока эффект появится