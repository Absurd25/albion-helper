import mss
import numpy as np
import cv2
import os


def capture_screen(x=0, y=0, width=100, height=100):
    with mss.mss() as sct:
        monitor = {"top": y, "left": x, "width": width, "height": height}
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img


def resize_image(image, max_width=200, max_height=100):
    h, w = image.shape[:2]
    scaling_factor = min(max_width / w, max_height / h)
    new_size = (int(w * scaling_factor), int(h * scaling_factor))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def save_effect_template(x, y, width, height, label, output_dir="data/templates/effects"):
    """
    Делает скриншот указанной области и сохраняет как PNG в папку effects
    """
    os.makedirs(output_dir, exist_ok=True)

    # Получаем название файла
    safe_label = label.replace(" ", "_").lower()
    filename = f"effect_{safe_label}_{width}x{height}.png"
    filepath = os.path.join(output_dir, filename)

    # Делаем скриншот
    image = capture_screen(x, y, width, height)

    # Сохраняем изображение
    cv2.imwrite(filepath, image)
    return filename

def find_image_difference(img1, img2):
    """
    Сравнивает два изображения и находит изменённые области.
    Возвращает список координат изменений и результат с прямоугольниками.
    """
    if img1.shape != img2.shape:
        print("⚠️ Размеры изображений не совпадают")
        return [], None

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    result_img = img1.copy()
    bounding_boxes = []

    for contour in contours:
        if cv2.contourArea(contour) > 100:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            bounding_boxes.append((x, y, w, h))

    print(f"🔍 Найдено {len(bounding_boxes)} изменений")
    return bounding_boxes, result_img