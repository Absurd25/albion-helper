# albion_helper/ui/main_window.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QApplication, QMessageBox
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


# Импорт модулей
from modules.screenshot_handler import capture_screen, resize_image, save_effect_template, find_image_difference


def resource_path(relative_path):
    """ Для корректного поиска ресурсов внутри .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class AlbionHelperMainWindow(QWidget):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.getLogger(
            "AlbionHelperLogger")  # <-- Используем логгер по умолчанию, если не передан
        self.setWindowTitle("Albion Helper — Template Creator")
        self.resize(800, 600)

        # === Добавляем таймер для автообновления превью ===
        self.auto_update_timer = QTimer(self)
        self.auto_update_timer.timeout.connect(self.update_preview)
        self.auto_update_timer.start(500)  # Каждые 500 мс (0.5 секунд)

        self.init_ui()

        self.food_mode_active = False
        self.template_1_path = ""
        self.template_2_path = ""
        self.temp_dir = "data/templates/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def init_ui(self):
        self.settings_data = self.load_settings()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === Верхняя часть: контроль + превью ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        # --- Левая панель управления ---
        control_panel = QWidget()
        control_panel.setFixedSize(250, 300)
        control_layout = QVBoxLayout()

        self.region_label = QLabel("Выберите область:")
        self.region_combo = QComboBox()
        self.region_combo.addItems([
            "Область эффектов персонажа",
            "Слот еды",
            "Куртка (R)",
            "Шлем (D)"
        ])

        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.width_input = QLineEdit()
        self.height_input = QLineEdit()

        coords_group = QVBoxLayout()
        coords_group.addWidget(QLabel("Координаты и размеры"))
        coords_group.addLayout(self.create_row("X:", self.x_input))
        coords_group.addLayout(self.create_row("Y:", self.y_input))
        coords_group.addLayout(self.create_row("Ширина:", self.width_input))
        coords_group.addLayout(self.create_row("Высота:", self.height_input))

        # --- Новое поле ---
        coords_group.addWidget(QLabel("Имя темплейта:"))
        self.name_input = QLineEdit()
        coords_group.addLayout(self.create_row("", self.name_input))

        control_layout.addWidget(self.region_label)
        control_layout.addWidget(self.region_combo)

        self.region_combo.currentIndexChanged.connect(self.on_region_changed)

        control_layout.addLayout(coords_group)
        control_layout.addStretch()

        control_panel.setLayout(control_layout)

        # --- Превью справа (динамическое, но с фиксированной меткой) ---
        preview_box = QVBoxLayout()

        # Метка (заголовок превью)
        self.preview_label = QLabel("Превью области:")
        self.preview_label.setStyleSheet("font-weight: bold;")  # Можно сделать жирной для выделения

        # Область изображения (растягивается)
        self.image_preview = QLabel()
        self.image_preview.setStyleSheet("background-color: lightgray; border: 1px solid black;")
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(200, 100)
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px;
            }
        """)

        # Контейнер для метки и изображения
        preview_content_layout = QVBoxLayout()
        preview_content_layout.addWidget(self.preview_label)
        preview_content_layout.addWidget(self.image_preview, stretch=1)

        # Враппер с фиксированным верхним краем
        preview_container = QWidget()
        preview_container.setObjectName("preview-container")
        preview_container.setStyleSheet("""
            #preview-container {
                border: 1px solid #ccc;
                padding: 5px;
                background-color: #f9f9f9;
            }
        """)
        preview_container.setLayout(preview_content_layout)

        # --- Сборка верхней части ---
        top_layout.addWidget(control_panel, alignment=Qt.AlignTop)
        top_layout.addWidget(preview_container, stretch=1)  # Растягиваемый контейнер с превью
        top_widget.setLayout(top_layout)

        # === Панель с кнопками (статичная внизу) ===
        button_panel = QWidget()
        button_panel.setFixedHeight(60)
        button_layout = QHBoxLayout()

        self.save_region_button = QPushButton("✅ Сохранить область")
        self.save_template_button = QPushButton("💾 Сохранить как темплейт")
        self.auto_food_button = QPushButton("🍱 Авто-режим: Еда")
        self.auto_food_button.clicked.connect(self.start_auto_food_mode)

        self.add_food_template_button = QPushButton("💾 Добавить авто-темплейт еды")
        self.add_food_template_button.clicked.connect(self.add_last_food_template_to_db)

        # --- Добавляем все кнопки в layout ---
        button_layout.addWidget(self.save_region_button)
        button_layout.addWidget(self.save_template_button)
        button_layout.addWidget(self.auto_food_button)
        button_layout.addWidget(self.add_food_template_button)

        # --- Устанавливаем layout на панель ---
        button_panel.setLayout(button_layout)

        # === Статус режима еды ===
        self.food_mode_label = QLabel("🍱 Режим еды: выключен")
        self.food_mode_label.setStyleSheet("font-weight: bold; color: gray;")
        main_layout.addWidget(self.food_mode_label, alignment=Qt.AlignLeft)

        # === Статус ===
        self.status_label = QLabel("Готово.")
        self.status_label.setStyleSheet("font-size: 14px; padding: 10px;")

        # === Основной layout ===
        main_layout.addWidget(top_widget, stretch=1)  # Растягиваемый блок сверху
        main_layout.addWidget(button_panel)  # Фиксированный блок с кнопками
        main_layout.addWidget(self.status_label)  # Статус всегда внизу

        self.setLayout(main_layout)

        # Подключаем сигналы
        self.save_region_button.clicked.connect(self.save_region)
        self.save_template_button.clicked.connect(self.save_template)

    def create_row(self, label_text, widget):
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text), alignment=Qt.AlignRight)
        row.addWidget(widget)
        return row

    def update_preview(self):
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("Ошибка: все поля должны быть числами.")
            self.logger.warning("⚠️ Некорректные данные ввода: не числа")
            return

        self.logger.info(f"📸 Обновление превью: X={x}, Y={y}, W={width}, H={height}")
        image = capture_screen(x, y, width, height)
        if image is None:
            self.status_label.setText("Ошибка: не удалось сделать скриншот.")
            return

        # Получаем доступный размер для превью
        available_size = self.image_preview.size()

        # Ресайз с сохранением пропорций
        h, w = image.shape[:2]
        scaling_factor = min(available_size.width() / w, available_size.height() / h)
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        resized_image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

        # Преобразуем под QPixmap
        q_img = QImage(resized_image.data, resized_image.shape[1], resized_image.shape[0],
                       resized_image.strides[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)

        # Устанавливаем изображение
        self.image_preview.setPixmap(pixmap)
        self.status_label.setText("Превью обновлено.")

    def save_region(self):
        region_name = self.region_combo.currentText()
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("Ошибка: все поля должны быть числами.")
            return

        config_path = resource_path(os.path.join("config", "settings.json"))
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        data[region_name] = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": region_name
        }

        with open(config_path, "w") as f:
            json.dump(data, f, indent=4)

        self.status_label.setText(f"✅ Сохранено: {region_name}")

    def save_template(self):
        region_name = self.region_combo.currentText()
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("Ошибка: все поля должны быть числами.")
            return

        filename = save_effect_template(x, y, width, height, region_name)
        self.status_label.setText(f"💾 Темплейт сохранён: {filename}")

    def save_template_data(self, x, y, width, height, label):
        template_dir = "data/templates/effects"
        os.makedirs(template_dir, exist_ok=True)
        template_file = os.path.join(template_dir, "region_templates.json")

        # Получаем имя из поля ввода
        user_name = self.name_input.text().strip()
        if not user_name:
            user_name = label.lower().replace(" ", "_")

        new_data = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": label,
            "name": user_name
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
            self.status_label.setText("⚠️ Темплейт с таким именем уже существует.")
            return False

        data.append(new_data)
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        self.status_label.setText(f"✅ Темплейт '{user_name}' сохранён в region_templates.json")
        return True

    def save_food_template(self, x, y, width, height, label="Эффект еды"):
        """
        Сохраняет изображение эффекта еды и JSON с координатами
        """
        food_dir = "data/templates/food"
        os.makedirs(food_dir, exist_ok=True)

        filename = f"effect_{label.lower().replace(' ', '_')}_{width}x{height}.png"
        full_path = os.path.join(food_dir, filename)

        # Сохраняем изображение области
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
            "name": label.lower().replace(" ", "_"),
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

        exists = any(item["name"] == new_data["name"] for item in data)
        if not exists:
            data.append(new_data)
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        self.status_label.setText(f"🍱 Эффект еды '{label}' сохранён")

    def find_and_save_food_effect(self):
        from modules.screenshot_handler import find_image_difference

        boxes, result_img = find_image_difference(self.img1, self.img2)
        if not boxes:
            self.status_label.setText("❌ Не удалось обнаружить эффект от еды.")
            return

        # Сохраняем результат сравнения
        result_path = os.path.join(self.temp_dir, "food_diff.png")
        cv2.imwrite(result_path, result_img)

        # Отображаем изображение результата в превью (опционально)
        h, w = result_img.shape[:2]
        resized_result = resize_image(result_img, 400, 200)
        q_img = QImage(resized_result.data, resized_result.shape[1], resized_result.shape[0],
                       resized_result.strides[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)
        self.image_preview.setPixmap(pixmap)

        # Предлагаем пользователю сохранить
        reply = QMessageBox.question(
            self,
            "Сохранить эффект?",
            f"Обнаружена {len(boxes)} область(и) изменения. Сохранить как темплейт?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            x, y, w, h = boxes[0]
            food_x = self.x + x
            food_y = self.y + y
            food_w = w
            food_h = h

            self.save_food_template(food_x, food_y, food_w, food_h, label="Эффект еды")
            self.save_template_data(food_x, food_y, food_w, food_h, "Эффект еды")

            self.status_label.setText("✅ Эффект еды сохранён")

    def start_auto_food_mode(self):
        """
        Начинает автоматический режим поиска эффекта еды.
        """
        try:
            self.x = int(self.x_input.text())
            self.y = int(self.y_input.text())
            self.width = int(self.width_input.text())
            self.height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные значения X/Y/W/H")
            return

        # Подтверждение первого скриншота
        reply = QMessageBox.question(
            self,
            "Сделайте скриншот",
            "Сейчас будет сделан первый скриншот (без еды).\nУбедитесь, что еда не активна.\nНажмите 'OK', чтобы продолжить.",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            self.take_first_screenshot()

    def take_first_screenshot(self):
        self.status_label.setText("📸 Делаю первый скриншот (без еды)")
        self.img1 = capture_screen(self.x, self.y, self.width, self.height)

        if self.img1 is None:
            self.status_label.setText("❌ Не удалось сделать первый скриншот.")
            return

        cv2.imwrite(os.path.join(self.temp_dir, "before_food.png"), self.img1)

        # Сообщаем пользователю, что нужно съесть еду
        reply = QMessageBox.question(
            self,
            "Съешьте еду",
            "Теперь съешьте еду и нажмите OK, чтобы сделать второй скриншот.",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if reply == QMessageBox.Ok:
            self.take_second_screenshot()

    def take_second_screenshot(self):
        self.status_label.setText("⏳ Жду 5 секунд после еды...")
        time.sleep(5)  # Ждём 5 секунд

        self.status_label.setText("📸 Делаю второй скриншот (с едой)")
        self.img2 = capture_screen(self.x, self.y, self.width, self.height)

        if self.img2 is None:
            self.status_label.setText("❌ Не удалось сделать второй скриншот.")
            return

        cv2.imwrite(os.path.join(self.temp_dir, "after_food.png"), self.img2)

        self.find_and_save_food_effect()

    def disable_food_mode(self):
        self.food_mode_active = False
        self.food_mode_label.setText("🍱 Режим еды: выключен")
        self.food_mode_label.setStyleSheet("font-weight: bold; color: gray;")

    def load_settings(self):
        config_path = resource_path(os.path.join("config", "settings.json"))
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    self.status_label.setText("⚠️ Ошибка чтения settings.json")
                    return {}
        else:
            self.status_label.setText("⚠️ Файл settings.json не найден")
            return {}

    def apply_region_settings(self, region_name):
        data = self.settings_data.get(region_name, {})
        self.x_input.setText(str(data.get("x", "")))
        self.y_input.setText(str(data.get("y", "")))
        self.width_input.setText(str(data.get("width", "")))
        self.height_input.setText(str(data.get("height", "")))

    def on_region_changed(self):
        selected_region = self.region_combo.currentText()
        self.apply_region_settings(selected_region)


    def add_last_food_template_to_db(self):
        """
        Добавляет последний найденный эффект еды в БД (если был найден)
        """
        if self.last_food_effect is None:
            self.status_label.setText("⚠️ Нет последнего эффекта для сохранения")
            return

        x = self.last_food_effect["x"]
        y = self.last_food_effect["y"]
        width = self.last_food_effect["width"]
        height = self.last_food_effect["height"]
        label = self.last_food_effect["label"]

        # Сохраняем в базу данных (в region_templates.json)
        success = self.save_template_data(x, y, width, height, label)

        if success:
            self.status_label.setText(f"✅ Эффект '{label}' добавлен в базу данных")
        else:
            self.status_label.setText("⚠️ Эффект с таким именем уже существует")

