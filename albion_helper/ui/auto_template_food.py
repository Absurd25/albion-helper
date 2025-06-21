from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QApplication, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QIcon
import os
import json
import sys
import cv2
import logging
import time
from PyQt5.QtCore import QTimer
from datetime import datetime
from utils.paths import TEMP_DIR, LOGS_DIR, TEMPLATES_DIR, EFFECT_TEMPLATES_JSON, FOOD_TEMPLATES_JSON

class FoodEffectPreviewWindow(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Albion Helper — Предпросмотр эффекта еды")
        self.image_path = image_path
        self.parent = parent  # Чтобы получить x, y области

        # Начальный размер окна
        self.resize(400, 300)

        # Минимальный размер окна
        self.setMinimumSize(300, 200)

        # Инициализация интерфейса
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Превью изображения
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addWidget(self.image_label, stretch=1)  # stretch=1 — занимает всё доступное пространство

        # Поле ввода имени
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите имя темплейта")
        layout.addWidget(QLabel("Имя темплейта:"))
        layout.addWidget(self.name_input)

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("✅ Сохранить")
        cancel_btn = QPushButton("❌ Не сохранять")

        save_btn.clicked.connect(self.save_effect)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # Загружаем изображение
        self.load_image()

    def load_image(self):
        """Загружает изображение и масштабирует его под размер QLabel"""
        img = cv2.imread(self.image_path)
        if img is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить изображение.")
            self.close()
            return

        h, w = img.shape[:2]
        available_size = self.image_label.size()
        scaling_factor = min(
            available_size.width() / w,
            available_size.height() / h
        )
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        resized_img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

        q_img = QImage(resized_img.data, resized_img.shape[1], resized_img.shape[0],
                       resized_img.strides[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)
        self.image_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        """Обновляем изображение при изменении размера окна"""
        self.load_image()
        super().resizeEvent(event)

    def reject(self):
        """Действие при нажатии 'Не сохранять'"""
        try:
            os.remove(self.image_path)
        except Exception as e:
            print(f"❌ Ошибка удаления файла: {e}")
        super().reject()

    def save_effect(self):
        """Действие при нажатии 'Сохранить'"""
        user_name = self.name_input.text().strip()
        if not user_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя для темплейта")
            return

        food_dir = "../data/data/templates/food"
        os.makedirs(food_dir, exist_ok=True)

        effect_filename = f"effect_{user_name}.png"
        full_path = os.path.join(food_dir, effect_filename)
        original_img = cv2.imread(self.image_path)

        if original_img is None:
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить изображение для сохранения.")
            self.reject()
            return

        cv2.imwrite(full_path, original_img)

        # Сохраняем данные в JSON
        template_file = os.path.join(food_dir, "food_templates.json")
        new_data = {
            "name": user_name,
            "label": user_name,
            "template": effect_filename,
            "x": self.parent.x if self.parent else 0,
            "y": self.parent.y if self.parent else 0,
            "width": original_img.shape[1],
            "height": original_img.shape[0]
        }

        if os.path.exists(template_file):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []
        else:
            data = []

        exists = any(item["name"] == user_name for item in data)
        if exists:
            QMessageBox.warning(self, "Ошибка", "Темплейт с таким именем уже существует")
            return

        data.append(new_data)
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        self.accept()