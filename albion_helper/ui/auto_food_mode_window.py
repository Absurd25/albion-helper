# ui/auto_food_mode_window.py
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

from modules.screenshot_handler import capture_screen
from utils.logger import setup_logger
from utils.paths import TEMPLATES_DIR


class AutoFoodModeWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Albion Helper — Авто-режим: Еда")
        self.resize(600, 400)

        # Логгер
        self.logger = setup_logger()

        # Состояние режима
        self.running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)

        # Настройки
        self.settings = self.load_settings()
        self.effects_rect = self.settings.get("Область эффектов персонажа", {})
        self.food_slot_rect = self.settings.get("Слот еды", {})

        # Инициализация интерфейса
        self.init_ui()

        # Первое обновление превью
        self.update_preview()

        # Таймер обновления области
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(500)  # Каждые 500 мс

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

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === Заголовок: Область эффектов (на 10% больше и зафиксировано сверху) ===
        self.effects_label = QLabel("Область эффектов:")
        font = self.effects_label.font()
        font.setPointSize(int(font.pointSize() * 1.1))  # Увеличиваем на 10%
        font.setBold(True)
        self.effects_label.setFont(font)
        self.effects_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Зафиксировано сверху

        # === Превью областей (зафиксированные размеры) ===
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(20)

        # --- Область эффектов ---
        self.effects_preview = QLabel()
        self.effects_preview.setFixedSize(220, 120)  # Фиксированный размер
        self.effects_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.effects_preview.setAlignment(Qt.AlignCenter)

        # --- Область еды ---
        self.food_preview = QLabel()
        self.food_preview.setFixedSize(220, 120)  # Фиксированный размер
        self.food_preview.setStyleSheet("background-color: #f0f0f0; border: 1px solid black;")
        self.food_preview.setAlignment(Qt.AlignCenter)

        preview_layout.addWidget(self.effects_preview)
        preview_layout.addWidget(self.food_preview)

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

        # === Сборка основного layout ===
        main_layout.addWidget(self.effects_label)
        main_layout.addLayout(preview_layout)
        main_layout.addWidget(self.status_label)
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

        # Делаем скриншоты
        img_effects = capture_screen(x_e, y_e, w_e, h_e)
        img_food = capture_screen(x_f, y_f, w_f, h_f)

        if img_effects is None or img_food is None:
            self.logger.warning("⚠️ Не удалось сделать скриншот для превью")
            return

        # Превью эффектов
        effects_resized = cv2.resize(img_effects, (220, 120), interpolation=cv2.INTER_AREA)
        q_img_effects = QImage(effects_resized.data, effects_resized.shape[1], effects_resized.shape[0],
                               effects_resized.strides[0], QImage.Format_BGR888)
        self.effects_preview.setPixmap(QPixmap.fromImage(q_img_effects))

        # Превью слота еды
        food_resized = cv2.resize(img_food, (220, 120), interpolation=cv2.INTER_AREA)
        q_img_food = QImage(food_resized.data, food_resized.shape[1], food_resized.shape[0],
                            food_resized.strides[0], QImage.Format_BGR888)
        self.food_preview.setPixmap(QPixmap.fromImage(q_img_food))

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
        self.preview_timer.stop()
        self.logger.info("Окно 'Авто-режим: Еда' закрыто")
        event.accept()

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

        # Делаем скриншоты
        img_effects = capture_screen(x_e, y_e, w_e, h_e)
        img_food = capture_screen(x_f, y_f, w_f, h_f)

        if img_effects is None or img_food is None:
            self.logger.warning("⚠️ Не удалось сделать скриншот для превью")
            return

        # Превью эффектов
        effects_resized = cv2.resize(img_effects, (w_e, h_e), interpolation=cv2.INTER_AREA)
        q_img_effects = QImage(effects_resized.data, effects_resized.shape[1], effects_resized.shape[0],
                               effects_resized.strides[0], QImage.Format_BGR888)
        self.effects_preview.setPixmap(QPixmap.fromImage(q_img_effects))

        # Превью слота еды
        food_resized = cv2.resize(img_food, (w_f, h_f), interpolation=cv2.INTER_AREA)
        q_img_food = QImage(food_resized.data, food_resized.shape[1], food_resized.shape[0],
                            food_resized.strides[0], QImage.Format_BGR888)
        self.food_preview.setPixmap(QPixmap.fromImage(q_img_food))

