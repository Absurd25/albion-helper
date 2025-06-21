import cv2



def find_image_difference(img1, img2):
    """
    Сравнивает два изображения и находит изменённые области.
    Возвращает список координат изменений и результат с прямоугольниками.
    """
    if img1.shape != img2.shape:
        print("⚠️ Размеры изображений не совпадают")
        return [], None

    # Переводим в оттенки серого
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Найдём разницу
    diff = cv2.absdiff(gray1, gray2)
    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    result_img = img1.copy()
    bounding_boxes = []

    for contour in contours:
        if cv2.contourArea(contour) > 100:  # Игнорируем мелкие изменения
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            bounding_boxes.append((x, y, w, h))

    print(f"🔍 Найдено {len(bounding_boxes)} изменений")
    return bounding_boxes, result_img