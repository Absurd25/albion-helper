import os

# Основные директории и файлы
structure = {
    "": [
        "main.py",
    ],
    "config": [
        "__init__.py",
        "settings.json"
    ],
    "ui": [
        "__init__.py",
        "main_window.py",
        "template_creator_ui.py",
        "helper_controls.py"
    ],
    "modules": [
        "__init__.py",
        "screenshot_handler.py",
        "template_matcher.py",
        "image_comparer.py",
        "skill_monitor.py",
        "food_detector.py"
    ],
    "utils": [
        "__init__.py",
        "file_utils.py",
        "logger.py",
        "helpers.py"
    ],
    "data": [],
    "data/templates": [
        "__init__.py"
    ],
    "data/templates/effects": [],
    "data/templates/food": [],
    "data/templates/temp": [],
    "resources": []
}

def create_structure(base_path):
    for folder, files in structure.items():
        full_path = os.path.join(base_path, folder)
        os.makedirs(full_path, exist_ok=True)

        # Создаем файлы в папке
        for file in files:
            file_path = os.path.join(full_path, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file.endswith('.py') and file != "__init__.py":
                        f.write('"""\nModule description\n"""\n\n')
                    elif file == "settings.json":
                        f.write('{\n    "default_resolution": "1920x1080",\n    "language": "en"\n}')
                    # остальные файлы остаются пустыми или добавляй шаблоны по желанию

    print(f"✅ Структура проекта успешно создана в папке: {base_path}")

if __name__ == "__main__":
    project_name = "albion_helper"
    base_dir = os.path.join(os.getcwd(), project_name)
    create_structure(base_dir)