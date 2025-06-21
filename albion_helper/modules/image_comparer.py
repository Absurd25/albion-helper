# albion_helper/modules/image_comparer.py

import cv2
import numpy as np


def find_image_difference(img1, img2):
    """Сравнивает два изображения и возвращает координаты изменённых областей."""
    if img1 is None or img2 is None:
        print("⚠️ Одно из изображений равно None")
        return [], None

    if img1.shape != img2.shape:
        print("⚠️ Размеры изображений не совпадают")
        return [], None

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result_img = img2.copy()  # Рисуем изменения на after_food.png
    bounding_boxes = []

    for contour in contours:
        if cv2.contourArea(contour) > 100:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            bounding_boxes.append((x, y, w, h))

    return bounding_boxes, result_img


def compare_images_brightness(img1, img2, threshold=10):
    """
    Проверяет, есть ли заметное отличие в яркости между изображениями
    """
    avg1 = np.mean(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY))
    avg2 = np.mean(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY))
    return abs(avg1 - avg2) > threshold


def get_image_brightness(img):
    """
    Возвращает среднюю яркость изображения
    """
    return np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))