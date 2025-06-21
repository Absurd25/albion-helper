# albion_helper/ui/main_window.py

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

# Импорт модулей
from modules.screenshot_handler import capture_screen, resize_image, save_effect_template, find_image_difference
from modules.food_processor import process_food_difference

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
        self.logger = logger or logging.getLogger("AlbionHelperLogger")
        self.setWindowTitle("Albion Helper — Template Creator")
        self.start_time = datetime.now()
        self.template_1_path = ""
        self.template_2_path = ""
        self.temp_dir = "data/templates/temp"
        self.last_food_effect = None
        self.resize(800, 600)

        self.auto_update_timer = QTimer(self)
        self.auto_update_timer.timeout.connect(self.update_preview)
        self.auto_update_timer.start(200)

        self.init_ui()

        self.food_mode_active = False
        self.template_1_path = ""
        self.template_2_path = ""
        self.found_changes = []
        self.change_index = 0
        self.temp_dir = "data/templates/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

        # Загрузка настроек
        self.settings_data = self.load_settings()
        self.apply_region_settings(self.region_combo.currentText())

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

        self.add_food_template_button = QPushButton("💾 Добавить авто-темплейт еды")
        self.add_food_template_button.clicked.connect(self.start_auto_food_mode)

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
        if not hasattr(self, 'img1') or not hasattr(self, 'img2'):
            self.status_label.setText("❌ Не все скриншоты загружены")
            return

        if self.img1 is None or self.img2 is None:
            self.status_label.setText("❌ Один из скриншотов пуст")
            return

        from modules.image_comparer import find_image_difference
        boxes, result_img = find_image_difference(self.img1, self.img2)

        if not boxes:
            self.status_label.setText("❌ Не удалось обнаружить эффект от еды.")
            return

        # Сохраняем результат сравнения
        result_path = os.path.join(self.temp_dir, "food_diff.png")
        cv2.imwrite(result_path, result_img)

        output_dir = os.path.join(self.temp_dir, "diff")
        os.makedirs(output_dir, exist_ok=True)

        # Обрезаем и сохраняем каждую найденную область
        self.found_changes = []
        for idx, (x, y, w, h) in enumerate(boxes):
            cropped = self.img2[y:y + h, x:x + w]
            cropped_path = os.path.join(output_dir, f"change_{idx}.png")
            cv2.imwrite(cropped_path, cropped)
            self.found_changes.append(cropped_path)

        # Запускаем показ изменений через таймер
        self.change_index = 0
        QTimer.singleShot(500, self.show_next_change)

    def start_auto_food_mode(self):
        try:
            self.x = int(self.x_input.text())
            self.y = int(self.y_input.text())
            self.width = int(self.width_input.text())
            self.height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные числа")
            return

        # Проверка: не нулевые ли значения
        if self.width <= 0 or self.height <= 0:
            self.status_label.setText("⚠️ Ширина и высота должны быть больше 0")
            return

        # Проверка: не выходят ли за пределы экрана
        from mss import mss
        with mss() as sct:
            monitor = sct.monitors[0]  # главный монитор
            if self.x + self.width > monitor["width"] or self.y + self.height > monitor["height"]:
                self.status_label.setText("❌ Область выходит за пределы экрана")
                return

        reply = QMessageBox.information(
            self,
            "Первый скриншот",
            "Нажмите OK, чтобы сделать первый скриншот (без еды)",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply == QMessageBox.Ok:
            self.take_first_screenshot()

    def take_first_screenshot(self):
        self.status_label.setText("📸 Первый скриншот (без еды)")
        self.logger.info("📸 Первый скриншот (без еды)")

        self.img1 = capture_screen(self.x, self.y, self.width, self.height)
        cv2.imwrite(os.path.join(self.temp_dir, "before_food.png"), self.img1)

        reply = QMessageBox.information(
            self,
            "Второй скриншот",
            "Съешьте еду и нажмите OK для второго скриншота",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply == QMessageBox.Ok:
            QTimer.singleShot(5000, self.take_second_screenshot)  # Ждём 5 секунд

    def take_second_screenshot(self):
        self.status_label.setText("📸 Второй скриншот (с едой)")
        self.logger.info("📸 Второй скриншот (с едой)")

        self.img2 = capture_screen(self.x, self.y, self.width, self.height)
        if self.img2 is None:
            self.status_label.setText("❌ Не удалось сделать второй скриншот")
            self.logger.error("❌ Не удалось сделать второй скриншот")
            return

        cv2.imwrite(os.path.join(self.temp_dir, "after_food.png"), self.img2)
        self.find_and_save_food_effect()

    def process_food_effect(self):
        before_img = os.path.join(self.temp_dir, "before_food.png")
        after_img = os.path.join(self.temp_dir, "after_food.png")
        output_dir = os.path.join(self.temp_dir, "diff")

        changes = process_food_difference(before_img, after_img, output_dir)

        if changes:
            self.status_label.setText("✅ Эффект от еды обнаружен")
            reply = QMessageBox.question(
                self,
                "Сохранить эффект?",
                f"Найдено {len(changes)} изменений. Сохранить как темплейт?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # Сохраняем первое найденное изменение как шаблон
                effect_img = cv2.imread(changes[0])
                x, y, w, h = self.get_coords_from_filename(changes[0])
                self.save_food_template(x, y, w, h, label="Эффект еды")
                self.save_template_data(x, y, w, h, "Эффект еды")
                self.last_food_effect = {
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "label": "Эффект еды"
                }
                self.status_label.setText("✅ Эффект еды сохранён как авто-темплейт")
        else:
            self.status_label.setText("❌ Не удалось обнаружить эффект от еды.")

    def get_coords_from_filename(self, path):
        """Вспомогательная функция для получения координат из имени файла"""
        filename = os.path.basename(path)
        if "change_" in filename:
            return 0, 0, 80, 80  # Пример, замени на реальные данные при необходимости
        return 0, 0, 80, 80

    def add_last_food_template_to_db(self):
        if self.last_food_effect is None:
            self.status_label.setText("⚠️ Нет последнего эффекта для сохранения")
            return

        x = self.last_food_effect["x"]
        y = self.last_food_effect["y"]
        width = self.last_food_effect["width"]
        height = self.last_food_effect["height"]
        label = self.last_food_effect["label"]

        success = self.save_template_data(x, y, width, height, label)
        if success:
            self.status_label.setText(f"✅ Эффект '{label}' добавлен в базу данных")
        else:
            self.status_label.setText("⚠️ Эффект с таким именем уже существует")

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

    def start_manual_auto_food_mode(self):
        try:
            self.x = int(self.x_input.text())
            self.y = int(self.y_input.text())
            self.width = int(self.width_input.text())
            self.height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные числа")
            return

        # Проверка: не нулевые ли значения
        if self.width <= 0 or self.height <= 0:
            self.status_label.setText("⚠️ Ширина и высота должны быть больше 0")
            return

        # Проверка: не выходят ли за пределы экрана
        from mss import mss
        with mss() as sct:
            monitor = sct.monitors[0]  # главный монитор
            if self.x + self.width > monitor["width"] or self.y + self.height > monitor["height"]:
                self.status_label.setText("❌ Область выходит за пределы экрана")
                return

        reply = QMessageBox.information(
            self,
            "Первый скриншот",
            "Нажмите OK, чтобы сделать первый скриншот (без еды)",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply == QMessageBox.Ok:
            self.take_first_screenshot()

    def show_next_change(self):
        if not self.found_changes:
            self.status_label.setText("❌ Нет изменений для просмотра")
            return

        change_path = self.found_changes[self.change_index]

        # Правильный вызов с parent=self
        preview_window = FoodEffectPreviewWindow(image_path=change_path, parent=self)

        result = preview_window.exec_()  # Модальное окно

        if result == QDialog.Accepted:
            self.status_label.setText("✅ Эффект сохранён")
        else:
            self.status_label.setText("🗑️ Эффект удалён")

        if self.change_index < len(self.found_changes) - 1:
            self.change_index += 1
            QTimer.singleShot(500, self.show_next_change)
        else:
            self.status_label.setText("✅ Все изменения просмотрены")

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
import cv2
import os
import json


class FoodEffectPreviewWindow(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предпросмотр эффекта еды")
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

        food_dir = "data/templates/food"
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