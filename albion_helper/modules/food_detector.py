# albion_helper/modules/food_detector.py

import os
import json
import cv2
import numpy as np
import pyautogui
import time
from modules.screenshot_handler import capture_screen, find_image_difference


class FoodDetector:
    def __init__(self, logger=None):
        self.logger = logger or self._setup_fallback_logger()
        self.food_area = None  # область эффекта еды
        self.auto_food_active = False
        self.temp_dir = "data/templates/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def _setup_fallback_logger(self):
        """Если не передан логгер — создаём простой"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return logging.getLogger("FoodDetectorLogger")

    def capture_first_screenshot(self, x, y, width, height):
        """
        Делает первый скриншот (без еды)
        """
        self.logger.info(f"📸 Первый скриншот: X={x}, Y={y}, W={width}, H={height}")
        self.first_screenshot = capture_screen(x, y, width, height)

        if self.first_screenshot is None:
            self.logger.error("❌ Не удалось сделать первый скриншот")
            return None

        cv2.imwrite(os.path.join(self.temp_dir, "before_food.png"), self.first_screenshot)
        self.logger.info("✅ Первый скриншот сохранён")
        return {"area": (x, y, width, height)}

    def capture_second_screenshot(self, data):
        """
        Делает второй скриншот и сравнивает с первым
        """
        x, y, w, h = data["area"]
        self.logger.info("📸 Второй скриншот: с едой")
        second_img = capture_screen(x, y, w, h)

        if second_img is None:
            self.logger.error("❌ Не удалось сделать второй скриншот")
            return None

        boxes, result_img = find_image_difference(data["first_img"], second_img)
        result_path = os.path.join(self.temp_dir, "food_diff.png")
        cv2.imwrite(result_path, result_img)

        if not boxes:
            self.logger.warning("❌ Эффект от еды не найден")
            return None

        self.logger.info(f"🔍 Найдено {len(boxes)} изменений. Сохраняем первое")
        food_x = x + boxes[0][0]
        food_y = y + boxes[0][1]
        food_w = boxes[0][2]
        food_h = boxes[0][3]

        return {
            "x": food_x,
            "y": food_y,
            "width": food_w,
            "height": food_h
        }

    def save_food_template(self, x, y, width, height, label="Эффект еды", user_name=None):
        """
        Сохраняет темплейт еды в папку и JSON
        """
        food_dir = "data/templates/food"
        os.makedirs(food_dir, exist_ok=True)

        # Получаем имя темплейта
        if not user_name:
            last_number = self.get_last_template_index()
            user_name = f"темплейт_еды_{last_number + 1}"

        filename = f"effect_{user_name}_{width}x{height}.png"
        full_path = os.path.join(food_dir, filename)

        # Делаем скриншот области и сохраняем
        food_image = capture_screen(x, y, width, height)
        cv2.imwrite(full_path, food_image)

        # Сохраняем данные в JSON
        template_file = os.path.join(food_dir, "food_templates.json")
        new_data = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": label,
            "name": user_name,
            "template": filename
        }

        if os.path.exists(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        exists = any(item["name"] == user_name for item in data)
        if exists:
            self.logger.warning(f"⚠️ Темплейт '{user_name}' уже существует")
            return False

        data.append(new_data)
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        self.logger.info(f"🍱 Темплейт '{user_name}' сохранён как {filename}")
        self.food_area = {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        return True

    def get_last_template_index(self):
        """
        Возвращает последний индекс 'темплейт_еды_X'
        """
        template_file = os.path.join("data/templates/food", "food_templates.json")
        max_index = 0

        if os.path.exists(template_file):
            with open(template_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    for item in data:
                        name = item.get("name", "")
                        if name.startswith("темплейт_еды_"):
                            suffix = name.replace("темплейт_еды_", "")
                            if suffix.isdigit():
                                max_index = max(int(suffix), max_index)
                except json.JSONDecodeError:
                    pass

        return max_index

    def check_food_status(self, area=None):
        """
        Проверяет, есть ли сейчас эффект еды на экране
        """
        area = area or self.food_area
        if not area:
            return False

        x, y, w, h = area["x"], area["y"], area["width"], area["height"]
        current_img = capture_screen(x, y, w, h)

        if current_img is None:
            self.logger.warning("❌ Не удалось захватить область еды")
            return False

        avg_color = np.mean(cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY))
        self.logger.info(f"🌙 Средняя яркость: {avg_color:.2f}")

        return avg_color < 10  # если яркость меньше 10 → нет еды

    def auto_eat_loop(self, interval_ms=10000):
        """
        Цикл автопрокрутки еды
        """
        while self.auto_food_active:
            if self.check_food_status():
                self.logger.info("🍽️ Еда закончилась. Нажимаю '2'...")
                pyautogui.press('2')
                time.sleep(5)  # ждём, пока появится эффект
            time.sleep(interval_ms / 1000)

    def toggle_auto_eat(self, active):
        self.auto_food_active = active
        if active:
            self.logger.info("🍴 Авто-хавка запущено")
        else:
            self.logger.info("🛑 Авто-хавка остановлено")
