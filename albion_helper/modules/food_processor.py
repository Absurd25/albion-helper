import os
import cv2
from modules.image_comparer import find_image_difference
from utils.logger import setup_logger

logger = setup_logger()

def process_food_difference(before_image_path, after_image_path, output_dir=None):
    """
    Сравнивает два изображения (до и после еды), находит изменения,
    сохраняет food_diff и обрезанные изображения изменений.
    :param before_image_path: str — путь к скриншоту до еды
    :param after_image_path: str — путь к скриншоту после еды
    :param output_dir: str — папка для сохранения результатов
    :return: list[str] — список путей к обрезанным изображениям
    """
    if output_dir is None:
        output_dir = os.path.join("data", "templates", "temp", "diff")

    os.makedirs(output_dir, exist_ok=True)

    # Очищаем папку перед новым сохранением
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))

    # Загружаем изображения
    img_before = cv2.imread(before_image_path)
    img_after = cv2.imread(after_image_path)

    if img_before is None or img_after is None:
        logger.error("❌ Не удалось загрузить одно или оба изображения")
        return []

    # Используем готовую функцию для поиска различий
    bounding_boxes, result_img = find_image_difference(img_before, img_after)

    if not bounding_boxes:
        logger.info("🔍 Изменений не найдено")
        return []

    # 1. Сохраняем изображение с разницей (food_diff)
    food_diff_path = os.path.join(output_dir, "food_diff.png")
    cv2.imwrite(food_diff_path, result_img)
    logger.info(f"✅ Изображение разницы сохранено: {food_diff_path}")

    # 2. Обрезаем и сохраняем каждую найденную область
    saved_paths = []
    for idx, (x, y, w, h) in enumerate(bounding_boxes):
        cropped = img_after[y:y + h, x:x + w]
        cropped_path = os.path.join(output_dir, f"change_{idx}.png")
        cv2.imwrite(cropped_path, cropped)
        logger.info(f"✅ Область изменения [{idx}] сохранена: {cropped_path}")
        saved_paths.append(cropped_path)

    return saved_paths