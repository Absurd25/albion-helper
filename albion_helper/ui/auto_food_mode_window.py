from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QApplication, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
import cv2
import json
import pyautogui
import os
import numpy as np
import sys

from paths import ROOT_DIR
#
from utils.paths import DATA_DIR, TEMPLATES_DIR
#
from modules.screenshot_handler import capture_screen
from modules.template_matcher import find_template_in_image
from utils.logger import setup_logger



class AutoFoodModeWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle("Albion Helper — Авто-режим: Еда")
        self.resize(600, 600)
        self.setFixedSize(1300, 400)  # Фиксированный размер окна

        # Логгер
        self.logger = setup_logger()

        # Состояние режима
        self.running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_food_check)

        # Настройки
        self.settings = self.load_settings()
        self.effects_rect = self.settings.get("Область эффектов персонажа", {})
        self.food_slot_rect = self.settings.get("Слот еды", {})

        # Путь к шаблонам еды
        self.food_templates_dir = os.path.join(TEMPLATES_DIR, "food")

        # Инициализация интерфейса
        self.init_ui()

        # Первое обновление превью
        self.update_preview()

        # Таймер обновления области
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(500)  # Каждые 500 мс

    def load_settings(self):
        config_path = os.path.join(ROOT_DIR, "config", "settings.json")
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка чтения settings.json: {e}")
            return {}

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === Статус режима (вверху по центру) ===
        self.status_label = QLabel("Авто-прохватка: ❌ Выключен")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # === Заголовки областей ===
        effects_title = QLabel("Область эффектов персонажа:")
        effects_title.setFont(QFont("Arial", 12, QFont.Bold))
        food_title = QLabel("Слот еды:")
        food_title.setFont(QFont("Arial", 12, QFont.Bold))

        # === Превью области ===
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)

        # --- Область эффектов ---
        effects_layout = QVBoxLayout()
        effects_layout.addWidget(effects_title)
        self.effects_preview = QLabel()
        self.effects_preview.setFixedHeight(250)
        self.effects_preview.setFixedWidth(916)
        self.effects_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.effects_preview.setAlignment(Qt.AlignCenter)
        effects_layout.addWidget(self.effects_preview)

        # --- Область еды ---
        food_layout = QVBoxLayout()
        food_layout.addWidget(food_title)
        self.food_preview = QLabel()
        self.food_preview.setFixedHeight(250)
        self.food_preview.setFixedWidth(250)
        self.food_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.food_preview.setAlignment(Qt.AlignCenter)
        food_layout.addWidget(self.food_preview)

        # Добавляем обе области рядом
        preview_layout.addLayout(effects_layout)
        preview_layout.addLayout(food_layout)

        # === Кнопки управления ===
        control_layout = QHBoxLayout()
        self.toggle_button = QPushButton("🟢 Включить авто-режим")
        self.toggle_button.clicked.connect(self.toggle_auto_mode)
        close_button = QPushButton("❌ Закрыть")
        close_button.clicked.connect(self.close)
        control_layout.addWidget(self.toggle_button)
        control_layout.addWidget(close_button)

        # === Сборка основного layout ===
        main_layout.addLayout(preview_layout)
        main_layout.addLayout(control_layout)
        self.setLayout(main_layout)

    def update_preview(self):
        if not self.effects_rect or not self.food_slot_rect:
            return

        try:
            x_e = int(self.effects_rect.get("x", 0))
            y_e = int(self.effects_rect.get("y", 0))
            w_e = int(self.effects_rect.get("width", 100))
            h_e = int(self.effects_rect.get("height", 100))

            x_f = int(self.food_slot_rect.get("x", 0))
            y_f = int(self.food_slot_rect.get("y", 0))
            w_f = int(self.food_slot_rect.get("width", 100))
            h_f = int(self.food_slot_rect.get("height", 100))
        except (ValueError, TypeError) as e:
            self.logger.error(f"❌ Ошибка значений: {e}")
            return

        img_effects = capture_screen(x_e, y_e, w_e, h_e)
        img_food = capture_screen(x_f, y_f, w_f, h_f)

        if img_effects is None or img_food is None:
            self.logger.warning("⚠️ Не удалось сделать скриншот для превью")
            return

        def scale_image(img, target_width, target_height):
            h, w = img.shape[:2]
            scaling_factor = min(target_width / w, target_height / h)
            new_size = (int(w * scaling_factor), int(h * scaling_factor))
            return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

        effects_scaled = scale_image(img_effects, self.effects_preview.width(), self.effects_preview.height())
        q_img_effects = QImage(effects_scaled.data, effects_scaled.shape[1], effects_scaled.shape[0],
                               effects_scaled.strides[0], QImage.Format_BGR888)
        self.effects_preview.setPixmap(QPixmap.fromImage(q_img_effects))

        food_scaled = scale_image(img_food, self.food_preview.width(), self.food_preview.height())
        q_img_food = QImage(food_scaled.data, food_scaled.shape[1], food_scaled.shape[0],
                            food_scaled.strides[0], QImage.Format_BGR888)
        self.food_preview.setPixmap(QPixmap.fromImage(q_img_food))

    def auto_food_check(self):
        """
        Основной цикл проверки наличия еды и её употребления
        """
        if not self.effects_rect or not self.food_slot_rect:
            return

        try:
            x_e = int(self.effects_rect.get("x", 0))
            y_e = int(self.effects_rect.get("y", 0))
            w_e = int(self.effects_rect.get("width", 100))
            h_e = int(self.effects_rect.get("height", 100))

            x_f = int(self.food_slot_rect.get("x", 0))
            y_f = int(self.food_slot_rect.get("y", 0))
            w_f = int(self.food_slot_rect.get("width", 100))
            h_f = int(self.food_slot_rect.get("height", 100))
        except (ValueError, TypeError) as e:
            self.logger.error(f"❌ Ошибка значений: {e}")
            return

        img_effects = capture_screen(x_e, y_e, w_e, h_e)
        if img_effects is None:
            self.logger.warning("⚠️ Не удалось сделать скриншот области эффектов")
            return

        found_food = False
        for template_file in os.listdir(self.food_templates_dir):
            if not template_file.lower().endswith((".png", ".jpg")):
                continue

            template_path = os.path.join(self.food_templates_dir, template_file)
            template = cv2.imread(template_path)

            if template is None:
                self.logger.warning(f"⚠️ Не удалось загрузить шаблон: {template_path}")
                continue

            match_result = find_template_in_image(img_effects, template)
            if match_result:
                self.logger.info(f"✅ Еда найдена: {template_file}")
                found_food = True
                break

        if not found_food:
            self.logger.info("🍽️ Еда не найдена. Проверяю слот еды...")

            img_food_slot = capture_screen(x_f, y_f, w_f, h_f)
            if img_food_slot is None:
                self.logger.warning("⚠️ Не удалось сделать скриншот слота еды")
                return

            empty_food_path = os.path.join(TEMPLATES_DIR,"slots", "empty_food_slot.png")
            if not os.path.exists(empty_food_path):
                self.logger.warning("⚠️ Шаблон empty_food_slot.png не найден")
                return

            empty_food_template = cv2.imread(empty_food_path)
            if empty_food_template is None:
                self.logger.warning("⚠️ Не удалось загрузить шаблон empty_food_slot.png")
                return

            match_result = find_template_in_image(img_food_slot, empty_food_template)
            if match_result:
                self.logger.info("❌ Слот еды пуст")
            else:
                self.logger.info("🟢 Еда найдена в слоте. Нажимаем '2'")
                pyautogui.press('2')

    def toggle_auto_mode(self):
        self.running = not self.running
        if self.running:
            self.timer.start(10000)
            self.status_label.setText("Авто-прохватка: ✅ Активен")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: green;")
            self.toggle_button.setText("🔴 Выключить авто-режим")

            if self.main_window:
                self.main_window.update_food_mode_status(True)

        else:
            self.timer.stop()
            self.status_label.setText("Авто-прохватка: ❌ Выключен")
            self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: red;")
            self.toggle_button.setText("🟢 Включить авто-режим")

            if self.main_window:
                self.main_window.update_food_mode_status(False)


    def resizeEvent(self, event):
        self.update_preview()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        self.preview_timer.stop()
        self.logger.info("Окно 'Авто-режим: Еда' закрыто")
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = AutoFoodModeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()