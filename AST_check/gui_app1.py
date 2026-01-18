import sys
import ast
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt6.QtCore import Qt
from feature import Feature, create_table


class ASTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AST Checker")
        self.resize(1400, 900)
        self.code_lines = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        top_layout = QHBoxLayout()

        self.code_editor = QTextEdit()
        self.code_editor.setPlaceholderText("Введите Python-код или загрузите файл...")
        self.code_editor.textChanged.connect(self.update_all)

        self.load_button = QPushButton("📁 Загрузить файл")
        self.load_button.clicked.connect(self.load_file)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.code_editor)
        left_layout.addWidget(self.load_button)
        left_panel = QWidget()
        left_panel.setLayout(left_layout)

        self.ast_table = QTableWidget()
        self.ast_table.setColumnCount(2)
        self.ast_table.setHorizontalHeaderLabels(["AST Feature", "Код"])
        self.ast_table.horizontalHeader().setStretchLastSection(True)

        top_layout.addWidget(left_panel, 1)
        top_layout.addWidget(self.ast_table, 2)

        self.features_tabs = QTabWidget()
        self.features_tabs.setTabPosition(QTabWidget.TabPosition.North)

        main_layout.addLayout(top_layout, 4)
        main_layout.addWidget(self.features_tabs, 1)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Python files (*.py)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            self.code_editor.setPlainText(code)
        except Exception as e:
            self.features_tabs.addTab(QTextEdit(f"Ошибка загрузки: {e}"), "Ошибка")

    def update_all(self):
        code = self.code_editor.toPlainText()
        self.clear_all()
        if not code.strip():
            self.features_tabs.addTab(QTextEdit("Пустой исходный код."), "Результат")
            return
        try:
            tree = ast.parse(code)
            self.code_lines = code.splitlines()
            feature_obj = Feature()
            feature_obj.visit(tree)
            feature_obj.read_rows(code)
            self.update_ast_table(feature_obj)
            self.update_features_tabs(feature_obj)
        except SyntaxError as e:
            self.features_tabs.addTab(
                QTextEdit(f"Синтаксическая ошибка: {e}"), "Ошибка"
            )
        except Exception as e:
            self.features_tabs.addTab(QTextEdit(f"Ошибка анализа: {e}"), "Ошибка")

    def clear_all(self):
        """
        Очищаем все панели
        """
        self.ast_table.setRowCount(0)
        while self.features_tabs.count():
            self.features_tabs.removeTab(0)

    def update_ast_table(self, feature_obj):
        """
        Таблица: AST элемент | Код строки
        """
        self.ast_table.setRowCount(0)
        code_table = create_table(feature_obj.features)
        self.ast_table.setRowCount(len(feature_obj.rows))
        for num, row in enumerate(feature_obj.rows):
            code_dct = code_table.get(num + 1, dict())
            code_line = ", ".join(list(code_dct.keys()))
            self.ast_table.setItem(num, 0, QTableWidgetItem(code_line))
            self.ast_table.setItem(num, 1, QTableWidgetItem(row))
        self.ast_table.resizeColumnsToContents()

    def update_features_tabs(self, feature_obj):
        """
        Создаем вкладки для каждого типа features
        """
        for feature_name, feature_data in feature_obj.features.items():
            if not feature_data:
                continue
            if feature_name == "listcomp":
                text = "List Comprehensions:\n\n"
                for item in feature_data:
                    text += f"Строка {item['line']}:\n"
                    text += f"  Элемент: {item['elt']}\n"
                    text += f"  Генераторов: {item['generators']}\n"
                    text += f"  Условий if: {item['ifs_count']}\n\n"
            else:
                text = f"{feature_name.upper()}:\n\n"
                for item in feature_data:
                    text += f"{item}\n"

            tab = QTextEdit()
            tab.setPlainText(text)
            tab.setReadOnly(True)
            self.features_tabs.addTab(tab, feature_name.replace("comp", "Comp"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ASTViewer()
    window.show()
    sys.exit(app.exec())
