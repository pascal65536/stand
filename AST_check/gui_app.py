import sys
import ast
import json
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QFileDialog,
)
from feature import Feature


class ASTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AST Checker")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Верхняя панель: редактор + AST
        top_layout = QHBoxLayout()

        # Левая панель: редактор кода
        self.code_editor = QTextEdit()
        self.code_editor.setPlaceholderText("Введите Python-код или загрузите файл...")
        self.code_editor.textChanged.connect(self.update_all)

        self.load_button = QPushButton("Загрузить файл...")
        self.load_button.clicked.connect(self.load_file)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.code_editor)
        left_layout.addWidget(self.load_button)
        left_panel = QWidget()
        left_panel.setLayout(left_layout)

        # Правая панель: AST вывод
        self.ast_edit = QTextEdit()
        self.ast_edit.setPlaceholderText("AST вывод")
        self.ast_edit.setReadOnly(True)

        top_layout.addWidget(left_panel, 1)
        top_layout.addWidget(self.ast_edit, 2)

        # Нижнее поле: результат проверки
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setMaximumHeight(120)
        self.result_output.setPlaceholderText("Результат проверки AST")

        main_layout.addLayout(top_layout, 4)
        main_layout.addWidget(self.result_output, 1)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Files (*.py)")
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.code_editor.setPlainText(code)

    def update_all(self):
        code = self.code_editor.toPlainText()
        self.ast_edit.clear()
        self.result_output.clear()

        if not code.strip():
            self.result_output.setPlainText("Пустой исходный код.")
            return

        tree = ast.parse(code)
        feature_obj = Feature()
        feature_obj.visit(tree)
        # for kv in feature_obj.features:
        #     print(kv)
        #     print(feature_obj.features[kv])

        #     self.ast_edit.insertPlainText(kv)
        #     self.ast_edit.insertPlainText('\n')

        self.result_output.setPlainText("Result")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ASTViewer()
    window.show()
    sys.exit(app.exec())
