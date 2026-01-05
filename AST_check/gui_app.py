# gui_app.py - ПОЛНЫЙ КОД С ДВИЖУЩИМИСЯ РАЗДЕЛИТЕЛЯМИ
import sys
import ast
import json
import pprint

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QPushButton, QFileDialog, QTabWidget, QTableWidget, 
    QTableWidgetItem, QSplitter, QCheckBox, QMessageBox, QFontDialog
)
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import Qt
from feature import Feature, create_table

class ASTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AST Checker")
        self.resize(1600, 1000)
        self.code_lines = []
        self.current_font = QFont("Consolas", 10)
        self._feature_obj = None
        self.create_menu()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        left_layout = QVBoxLayout()
        self.code_editor = QTextEdit()
        self.code_editor.setFont(self.current_font)
        self.code_editor.setPlaceholderText("Введите Python-код или загрузите файл...")
        self.code_editor.textChanged.connect(self.update_all)
        self.load_button = QPushButton("Загрузить файл")
        self.load_button.clicked.connect(self.load_file)
        left_layout.addWidget(self.code_editor)
        left_layout.addWidget(self.load_button)
        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        checkboxes_widget = QWidget()
        checkboxes_layout = QVBoxLayout()
        checkboxes_layout.setSpacing(2)
        
        self.cb_imports = QCheckBox("Импорты")
        self.cb_calls = QCheckBox("Вызовы")
        self.cb_functions = QCheckBox("Функции")
        self.cb_loops = QCheckBox("Циклы")
        self.cb_comps = QCheckBox("Comprehensions")
        for cb in [self.cb_imports, self.cb_calls, self.cb_functions, self.cb_loops, self.cb_comps]:
            cb.setFont(self.current_font)
            cb.setChecked(True) 
            cb.stateChanged.connect(lambda checked, cbx=cb: print(f"Checkbox: {cbx.text()} = {cbx.isChecked()}"))
        checkboxes_layout.addWidget(self.cb_imports)
        checkboxes_layout.addWidget(self.cb_calls)
        checkboxes_layout.addWidget(self.cb_functions)
        checkboxes_layout.addWidget(self.cb_loops)
        checkboxes_layout.addWidget(self.cb_comps)
        checkboxes_layout.addStretch()
        checkboxes_widget.setLayout(checkboxes_layout)
        checkboxes_widget.setMaximumWidth(250)
        
        self.ast_table = QTableWidget()
        self.ast_table.setColumnCount(2)
        self.ast_table.setHorizontalHeaderLabels(["AST Feature", "Код"])
        self.ast_table.horizontalHeader().setStretchLastSection(True)
        self.ast_table.setFont(self.current_font)
        top_splitter.addWidget(left_panel)      
        top_splitter.addWidget(checkboxes_widget)
        top_splitter.addWidget(self.ast_table)    
        top_splitter.setStretchFactor(0, 1)  
        top_splitter.setStretchFactor(1, 0)  
        top_splitter.setStretchFactor(2, 2)  
        self.features_tabs = QTabWidget()
        self.features_tabs.setFont(self.current_font)
        main_splitter.addWidget(top_splitter)      
        main_splitter.addWidget(self.features_tabs)
        main_splitter.setStretchFactor(0, 4)  
        main_splitter.setStretchFactor(1, 1)  
        main_layout.addWidget(main_splitter)

    def create_menu(self):
        """Создание верхнего меню"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("Файл")
        open_action = QAction("Открыть...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_file)
        file_menu.addAction(open_action)
        
        # save_action = QAction("Сохранить features...", self)
        # save_action.setShortcut("Ctrl+S")
        # save_action.triggered.connect(self.save_features)
        # file_menu.addAction(save_action)

        file_menu.addSeparator()
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        font_menu = menubar.addMenu("Шрифт")
        font_dialog_action = QAction("Выбор шрифта...", self)
        font_dialog_action.setShortcut("Ctrl+F")
        font_dialog_action.triggered.connect(self.choose_font)
        font_menu.addAction(font_dialog_action)

    def choose_font(self):
        """
        Диалог выбора шрифта
        """
        font, ok = QFontDialog.getFont(self.current_font, self)
        if ok:
            self.current_font = font
            self.apply_font_to_all(font)

    def apply_font_to_all(self, font):
        """
        Применить шрифт ко всем виджетам
        """
        widgets = [
            self.code_editor, self.ast_table, self.features_tabs,
            self.cb_imports, self.cb_calls, self.cb_functions,
            self.cb_loops, self.cb_comps
        ]
        for widget in widgets:
            if widget:
                widget.setFont(font)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите Python файл", "", "Python files (*.py)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            self.code_editor.setPlainText(code)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки: {e}")

    def update_all(self):
        code = self.code_editor.toPlainText()
        self.clear_all()
        if not code.strip():
            self.features_tabs.addTab(QTextEdit("Пустой исходный код."), "Результат")
            return
        try:
            tree = ast.parse(code)
            self.code_lines = code.splitlines()
            self._feature_obj = Feature()
            self._feature_obj.visit(tree)
            if hasattr(self._feature_obj, 'read_rows'):
                self._feature_obj.read_rows(code)
            self.update_ast_table(self._feature_obj)
            self.update_features_tabs(self._feature_obj)
        except SyntaxError as e:
            self.features_tabs.addTab(QTextEdit(f"Синтаксическая ошибка: {e}"), "Ошибка")
        except Exception as e:
            self.features_tabs.addTab(QTextEdit(f"Ошибка анализа: {e}"), "Ошибка")

    def clear_all(self):
        self.ast_table.setRowCount(0)
        while self.features_tabs.count():
            self.features_tabs.removeTab(0)

    def update_ast_table(self, feature_obj):
        self.ast_table.setRowCount(0)
        try:
            code_table = create_table(feature_obj.features)
            self.ast_table.setRowCount(len(feature_obj.rows))
            for num, row in enumerate(feature_obj.rows):
                code_dct = code_table.get(num + 1, dict())
                code_line = ', '.join(list(code_dct.keys()))
                self.ast_table.setItem(num, 0, QTableWidgetItem(str(code_line)))      
                self.ast_table.setItem(num, 1, QTableWidgetItem(str(row)))      
        except:
            pass
        self.ast_table.resizeColumnsToContents()

    def update_features_tabs(self, feature_obj):
        for feature_name, feature_data in feature_obj.features.items():
            if not feature_data:
                continue
            if feature_name == "listcomp":
                text = "List Comprehensions:\n\n"
                for item in feature_data:
                    text += f"Строка {item['line']}:\n  Элемент: {item['elt']}\n"
                    text += f"  Генераторов: {item['generators']}\n"
                    text += f"  Условий if: {item['ifs_count']}\n\n"
            else:
                text = f"{feature_name.upper()}:\n\n"
                for item in feature_data:
                    text += f"{item}\n"
            tab = QTextEdit()
            tab.setPlainText(text)
            tab.setFont(self.current_font)
            tab.setReadOnly(True)
            self.features_tabs.addTab(tab, feature_name.replace("comp", "Comp"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ASTViewer()
    window.show()
    sys.exit(app.exec())
