from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage
import cv2
import os
import numpy as np
import json
import pyautogui

from modules.screenshot_handler import capture_screen
from utils.logger import setup_logger

class AutoFoodModeWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авто-режим: Еда")
        self.resize(600, 400)

        self.logger = setup_logger()
        self.running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)

        # Пути
        self.food_templates = self.load_food_templates()

        # Получаем координаты из settings.json
        self.settings = self.load_settings()
        self.effects_rect = self.settings.get("Область эффектов персонажа", {})
        self.helmet_slot_rect = self.settings.get("Шлем (D)", {})

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === Превью области ===
        preview_layout = QHBoxLayout()

        self.effects_label = QLabel("Область эффектов:")
        self.effects_preview = QLabel()
        self.effects_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.effects_preview.setAlignment(Qt.AlignCenter)

        self.helmet_label = QLabel("Слот шлема (D):")
        self.helmet_preview = QLabel()
        self.helmet_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.helmet_preview.setAlignment(Qt.AlignCenter)

        preview_layout.addWidget(self.effects_preview, stretch=1)
        preview_layout.addWidget(self.helmet_preview, stretch=1)

        # === Статус режима ===
        self.status_label = QLabel("Авто-прохватка: ❌ Выключен")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
        self.status_label.setAlignment(Qt.AlignCenter)

        # === Кнопки управления ===
        control_layout = QHBoxLayout()
        self.toggle_button = QPushButton("🟢 Включить авто-режим")
        self.toggle_button.clicked.connect(self.toggle_auto_mode)

        close_button = QPushButton("❌ Закрыть")
        close_button.clicked.connect(self.close)

        control_layout.addWidget(self.toggle_button)
        control_layout.addWidget(close_button)

        # === Сборка ===
        main_layout.addWidget(self.effects_label)
        main_layout.addLayout(preview_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

    def load_settings(self):
        config_path = os.path.join("config", "settings.json")
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка чтения settings.json: {e}")
            return {}

    def load_food_templates(self):
        food_dir = os.path.join("../data/data", "templates", "food")
        template_file = os.path.join(food_dir, "food_templates.json")

        if not os.path.exists(template_file):
            return []

        try:
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [os.path.join(food_dir, item["template"]) for item in data]
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шаблонов еды: {e}")
            return []

    def update_preview(self):
        if not self.effects_rect or not self.helmet_slot_rect:
            return

        # === Скриншоты ===
        x_e, y_e, w_e, h_e = self.effects_rect.values()
        x_h, y_h, w_h, h_h = self.helmet_slot_rect.values()

        img_effects = capture_screen(x_e, y_e, w_e, h_e)
        img_helmet = capture_screen(x_h, y_h, w_h, h_h)

        # === Превью эффектов ===
        effects_resized = cv2.resize(img_effects, (200, 100), interpolation=cv2.INTER_AREA)
        q_img_effects = QImage(effects_resized.data, effects_resized.shape[1], effects_resized.shape[0],
                               effects_resized.strides[0], QImage.Format_BGR888)
        self.effects_preview.setPixmap(QPixmap.fromImage(q_img_effects))

        # === Превью шлема ===
        helmet_resized = cv2.resize(img_helmet, (200, 100), interpolation=cv2.INTER_AREA)
        q_img_helmet = QImage(helmet_resized.data, helmet_resized.shape[1], helmet_resized.shape[0],
                              helmet_resized.strides[0], QImage.Format_BGR888)
        self.helmet_preview.setPixmap(QPixmap.fromImage(q_img_helmet))

        # === Логика авто-режима ===
        if self.running:
            found_food = False
            for template_path in self.food_templates:
                if not os.path.exists(template_path):
                    continue

                template = cv2.imread(template_path)
                result = cv2.matchTemplate(img_effects, template, cv2.TM_CCOEFF_NORMED)
                threshold = 0.8
                loc = np.where(result >= threshold)
                if len(loc[0]) > 0:
                    found_food = True
                    break

            if not found_food:
                # Проверяем наличие еды в слоте шлема
                empty_template = cv2.imread(os.path.join("resources", "empty_helmet_slot.png"))
                if empty_template is None:
                    self.logger.warning("Не найден шаблон empty_helmet_slot.png")
                    return

                result = cv2.matchTemplate(img_helmet, empty_template, cv2.TM_CCOEFF_NORMED)
                if result.max() < 0.7:  # Не пустой слот
                    self.logger.info("Еда найдена в слоте шлема. Нажимаем 'D'")
                    pyautogui.press('d')

    def toggle_auto_mode(self):
        self.running = not self.running
        if self.running:
            self.timer.start(200)  # 5 раз в секунду
            self.status_label.setText("Авто-прохватка: ✅ Активен")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            self.toggle_button.setText("🔴 Выключить авто-режим")
        else:
            self.timer.stop()
            self.status_label.setText("Авто-прохватка: ❌ Выключен")
            self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            self.toggle_button.setText("🟢 Включить авто-режим")

    def closeEvent(self, event):
        self.timer.stop()
        self.parent().disable_food_mode()
        event.accept()