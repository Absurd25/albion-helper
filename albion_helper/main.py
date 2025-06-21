# mainn.py

import sys
from PyQt5.QtWidgets import QApplication

from ui.main_window import AlbionHelperMainWindow  # Здесь уже есть QWidget и UI
from utils.logger import setup_logger
from datetime import datetime
import atexit




def main():
    logger = setup_logger()
    logger.info("🚀 Программа запущена")

    app = QApplication(sys.argv)

    # Передаем логгер в существующий класс из main_window.py
    window = AlbionHelperMainWindow(logger=logger)
    window.show()

    logger.info("/mainwindow отображено")

    # Настройка завершения сессии
    def log_shutdown():
        end_time = datetime.now()
        duration = end_time - window.start_time
        minutes = divmod(duration.total_seconds(), 60)
        logger.info(f"🛑 Сессия завершена. Работала: {int(minutes[0])} мин {int(minutes[1])} сек")

    atexit.register(log_shutdown)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()