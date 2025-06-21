import json
import os

DEFAULT_SETTINGS = {
    "default_resolution": "3440x1440",
    "language": "ru"
}


def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")

    if not os.path.exists(settings_path):
        save_settings(DEFAULT_SETTINGS, path=settings_path)
        return DEFAULT_SETTINGS

    with open(settings_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # На случай повреждённого файла
            save_settings(DEFAULT_SETTINGS, path=settings_path)
            return DEFAULT_SETTINGS


def save_settings(data, path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "settings.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)