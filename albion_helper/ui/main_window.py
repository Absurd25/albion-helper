# albion_helper/ui/main_window.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QIcon
import os
import sys
import json
import cv2
import numpy as np
import logging

# Импорт модулей
from modules.screenshot_handler import capture_screen
from modules.image_comparer import find_image_difference
from modules.template_generator import save_effect_template

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
        self.setWindowIcon(QIcon(resource_path("resources/icon.ico")))
        self.resize(800, 600)

        self.name_input = None

        # === Переменные для авто-хавки ===
        self.auto_food_active = False
        self.food_area = None  # область эффекта еды
        self.food_check_timer = QTimer()
        self.food_check_timer.timeout.connect(self.check_food_status)

        # === Переменные для создания темплейта ===
        self.auto_food_data = {}  # данные первого скриншота
        self.temp_dir = "data/templates/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

        # === Загрузка настроек ===
        self.settings_data = self.load_settings()

        # === Инициализация UI ===
        self.init_ui()

        # === Подгрузка координат текущего региона ===
        self.apply_region_settings(self.region_combo.currentText())

    def init_ui(self):
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

        self.region_combo.currentIndexChanged.connect(self.on_region_changed)

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

        coords_group.addWidget(QLabel("Имя темплейта:"))
        self.name_input = QLineEdit()
        coords_group.addLayout(self.create_row("", self.name_input))

        control_layout.addWidget(self.region_label)
        control_layout.addWidget(self.region_combo)
        control_layout.addLayout(coords_group)
        control_layout.addStretch()  # Растяжка внизу
        control_panel.setLayout(control_layout)

        # --- Превью справа (динамическое) ---
        preview_box = QVBoxLayout()
        self.preview_label = QLabel("Превью области:")
        self.preview_label.setStyleSheet("font-weight: bold;")
        self.image_preview = QLabel()
        self.image_preview.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 5px;
            }
        """)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumSize(200, 100)

        preview_content_layout = QVBoxLayout()
        preview_content_layout.addWidget(self.preview_label)
        preview_content_layout.addWidget(self.image_preview, stretch=1)

        preview_container = QWidget()
        preview_container.setObjectName("preview-container")
        preview_container.setLayout(preview_content_layout)

        # --- Сборка верхней части ---
        top_layout.addWidget(control_panel, alignment=Qt.AlignTop)
        top_layout.addWidget(preview_container, stretch=1)
        top_widget = QWidget()
        top_widget.setLayout(top_layout)

        # === Панель с кнопками (статичная внизу) ===
        button_panel = QWidget()
        button_panel.setFixedHeight(60)
        button_layout = QHBoxLayout()

        self.save_region_button = QPushButton("✅ Сохранить область")
        self.save_template_button = QPushButton("💾 Сохранить как темплейт")

        self.auto_food_button = QPushButton("🍱 Авто-хавка")
        self.auto_food_button.clicked.connect(self.toggle_auto_eat)

        self.add_food_template_button = QPushButton("💾 Добавить авто-темплейт еды")
        self.add_food_template_button.clicked.connect(self.start_add_food_template_mode)
        self.save_template_button.clicked.connect(self.save_template)

        button_layout.addWidget(self.save_region_button)
        button_layout.addWidget(self.save_template_button)
        button_layout.addWidget(self.auto_food_button)
        button_layout.addWidget(self.add_food_template_button)
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

        # === Таймер автообновления превью ===
        self.auto_update_timer = QTimer(self)
        self.auto_update_timer.timeout.connect(self.update_preview)
        self.auto_update_timer.start(250)  # Обновление 4 раза в секунду

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
            return

        image = capture_screen(x, y, width, height)
        if image is None:
            self.status_label.setText("❌ Не удалось сделать скриншот.")
            return

        available_size = self.image_preview.size()
        h, w = image.shape[:2]
        scaling_factor = min(available_size.width() / w, available_size.height() / h)
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        resized_image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

        q_img = QImage(resized_image.data, resized_image.shape[1], resized_image.shape[0],
                       resized_image.strides[0], QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)
        self.image_preview.setPixmap(pixmap)

    def start_add_food_template_mode(self):
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные значения X/Y/W/H")
            return

        reply = QMessageBox.question(
            self,
            "Добавить авто-темплейт еды",
            "Убедитесь, что еда ещё не активна.\nНажмите OK, чтобы сделать первый скриншот.",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply != QMessageBox.Ok:
            return

        # Первый скриншот
        self.first_screenshot = capture_screen(x, y, width, height)
        if self.first_screenshot is None:
            self.status_label.setText("❌ Не удалось сделать первый скриншот")
            return

        reply = QMessageBox.information(
            self,
            "Съешьте еду",
            "Теперь съешьте еду и нажмите OK,\nчтобы сделать второй скриншот через 5 секунд.",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply != QMessageBox.Ok:
            return

        # Таймер для второго скриншота
        self.status_label.setText("⏳ Ожидание 5 секунд перед вторым скриншотом...")
        QTimer.singleShot(5000, lambda: self.make_second_screenshot(x, y, width, height))

    def make_second_screenshot(self, x, y, width, height):
        self.status_label.setText("📸 Делаю второй скриншот...")
        second_img = capture_screen(x, y, width, height)

        if second_img is None:
            self.status_label.setText("❌ Не удалось сделать второй скриншот")
            return

        self.status_label.setText("🔍 Сравниваю изображения...")

        try:
            boxes, result_img = find_image_difference(self.first_screenshot, second_img)
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка сравнения изображений: {e}")
            logging.error(f"Ошибка при сравнении изображений: {e}")
            return

        if not boxes:
            self.status_label.setText("❌ Эффект от еды не найден")
            return

        # Предложить пользователю сохранить
        reply = QMessageBox.question(
            self,
            "Сохранить темплейт?",
            f"Обнаружено {len(boxes)} изменений. Сохранить как темплейт?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            food_x = x + boxes[0][0]
            food_y = y + boxes[0][1]
            food_w = boxes[0][2]
            food_h = boxes[0][3]

            self.save_food_template(food_x, food_y, food_w, food_h, label="Эффект еды")
            self.status_label.setText("✅ Темплейт еды создан")
        else:
            self.status_label.setText("🚫 Темплейт не сохранён")

    def save_food_template(self, x, y, width, height, label="Эффект еды"):
        food_dir = os.path.join("data", "templates", "food")
        os.makedirs(food_dir, exist_ok=True)

        filename = f"effect_{label.lower().replace(' ', '_')}_{width}x{height}.png"
        full_path = os.path.join(food_dir, filename)

        food_image = capture_screen(x, y, width, height)
        if food_image is None:
            self.status_label.setText("❌ Не удалось захватить область еды для сохранения")
            return

        cv2.imwrite(full_path, food_image)

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

        self.status_label.setText(f"🍱 Темплейт '{label}' сохранён в {template_file}")
        self.food_area = {"x": x, "y": y, "width": width, "height": height}

    def toggle_auto_eat(self):
        if self.food_area is None:
            self.status_label.setText("❌ Нет загруженного темплейта еды. Сначала создайте его.")
            return

        if self.auto_food_active:
            self.auto_food_active = False
            self.food_check_timer.stop()
            self.auto_food_button.setText("🍴 Авто-хавка: выкл")
            self.status_label.setText("🛑 Авто-хавка остановлено")
        else:
            interval = 10000  # 10 секунд
            self.food_check_timer.start(interval)
            self.auto_food_active = True
            self.auto_food_button.setText("🍴 Авто-хавка: вкл")
            self.status_label.setText("🟢 Авто-хавка запущено (проверка каждые 10 секунд)")

    def check_food_status(self):
        x = self.food_area["x"]
        y = self.food_area["y"]
        w = self.food_area["width"]
        h = self.food_area["height"]

        current_img = capture_screen(x, y, w, h)
        if current_img is None:
            self.status_label.setText("❌ Не удалось захватить область еды")
            return

        avg_color = np.mean(cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY))
        if avg_color < 10:
            self.status_label.setText("🍽️ Еда закончилась. Нажимаю '2'...")
            from pyautogui import press
            press('2')
            time.sleep(5)
            self.status_label.setText("✅ Еда снова активна")

    def save_region(self):
        region_name = self.region_combo.currentText()
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные значения X/Y/W/H")
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
            json.dump(data, f, indent=4, ensure_ascii=False)

        self.status_label.setText(f"✅ Сохранено: {region_name}")

    def load_settings(self):
        config_path = resource_path(os.path.join("config", "settings.json"))
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
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

    def save_template(self):
        region_name = self.region_combo.currentText()
        try:
            x = int(self.x_input.text())
            y = int(self.y_input.text())
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            self.status_label.setText("⚠️ Введите корректные числовые значения")
            return

        filename = save_effect_template(x, y, width, height, region_name)
        self.status_label.setText(f"💾 Темплейт сохранён: {filename}")
        self.save_template_data(x, y, width, height, region_name)

    def save_template_data(self, x, y, width, height, label):
        template_dir = "data/templates/effects"
        os.makedirs(template_dir, exist_ok=True)
        template_file = os.path.join(template_dir, "region_templates.json")

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
        if not exists:
            data.append(new_data)
            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        self.status_label.setText(f"✅ Темплейт '{label}' сохранён в region_templates.json")