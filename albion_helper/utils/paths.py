import os

# Корневая директория проекта
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Пути к данным
DATA_DIR = os.path.join(ROOT_DIR, "data")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
TEMP_DIR = os.path.join(TEMPLATES_DIR, "temp")

# Логи
LOGS_DIR = os.path.join(ROOT_DIR, "logs")

# Базы данных темплейтов
EFFECT_TEMPLATES_JSON = os.path.join(TEMPLATES_DIR, "effects", "region_templates.json")
FOOD_TEMPLATES_JSON = os.path.join(TEMPLATES_DIR, "food", "food_templates.json")

def ensure_directories():
    """Создаёт все нужные папки, если их нет"""
    for path in [DATA_DIR, TEMPLATES_DIR, TEMP_DIR, LOGS_DIR]:
        os.makedirs(path, exist_ok=True)