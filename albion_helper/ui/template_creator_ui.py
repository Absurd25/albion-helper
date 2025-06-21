# albion_helper/ui/template_creator_ui.py

from PyQt5.QtWidgets import QWidget, QLabel

class TemplateCreatorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        label = QLabel("Режим: Создание темплейтов", self)