import cv2
import numpy as np

MATCH_THRESHOLD = 0.85

def find_template_in_image(screen_img, template_img):
    """
    Ищет шаблон на изображении экрана.
    Возвращает True, если найдено совпадение.
    """
    if screen_img.shape[0] < template_img.shape[0] or screen_img.shape[1] < template_img.shape[1]:
        return False

    result = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    if max_val >= MATCH_THRESHOLD:
        return True
    return False