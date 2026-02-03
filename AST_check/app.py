import sys
import os
import ast
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QSplitter,
    QHeaderView,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from collections import defaultdict
from rules import EDUCATIONAL_RULES
from edu import apply_rule, ast_to_serializable, ASTJSONAnalyzer
from behoof import load_json, save_json

class CodeCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AST Educational Code Checker")
        self.resize(1400, 800)
        self.code_lines = []
        self.current_file = None
        self.analyzer = None
        self.errors_by_line = defaultdict(list)  
        self.init_ui()

    def clear_all(self): 
        """Очистка всех полей"""
        self.code_editor.clear()
        self.clear_results()
        self.current_file = None
        self.analyzer = None
        self.errors_by_line.clear()
        self.statusBar().showMessage("🧹 Очищено")

    def clear_results(self):  
        """Очистка таблицы результатов"""
        self.results_table.setRowCount(0)
        self.results_table.clearContents()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        buttons_layout = QHBoxLayout()
        self.load_btn = QPushButton("Открыть файл (Ctrl+O)")
        self.load_btn.setShortcut("Ctrl+O")
        self.load_btn.clicked.connect(self.load_file)

        self.analyze_btn = QPushButton("Анализировать (F5)")
        self.analyze_btn.setShortcut("F5")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_all)

        buttons_layout.addWidget(self.load_btn)
        buttons_layout.addWidget(self.analyze_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addStretch()

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.code_editor = QTextEdit()
        code_font = QFont("Consolas", 11)
        self.code_editor.setFont(code_font)
        self.code_editor.setPlaceholderText("Введите Python-код для анализа или загрузите файл (Ctrl+O)")
        left_layout.addWidget(self.code_editor)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)  # ✅ 3 колонки вместо 4
        self.results_table.setHorizontalHeaderLabels(["Код", "Строка кода", "Ошибка"])  # ✅ Убрана колонка №

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Код
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Строка кода
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Ошибка

        table_font = QFont("Consolas", 10)
        self.results_table.setFont(table_font)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.results_table)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(splitter)
        self.statusBar().showMessage("Готов к анализу кода")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть Python файл", "", "Python файлы (*.py);;Все файлы (*)")
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.code_editor.setPlainText(code)
        self.current_file = file_path
        self.code_lines = code.splitlines() 
        self.statusBar().showMessage(f"Загружен: {os.path.basename(file_path)}")
        self.clear_results()

    def run_analysis(self):
        code = self.code_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите код для анализа!")
            return

        try:
            self.statusBar().showMessage("🔍 Анализируем...")
            self.analyze_btn.setEnabled(False)

            tree = ast.parse(code)
            serialized = ast_to_serializable(tree)
            save_json("data", "temp_ast.json", serialized)

            self.analyzer = ASTJSONAnalyzer()
            ast_json = load_json("data", "temp_ast.json")
            self.analyzer.analyze(ast_json)

            all_errors = []
            for rule in EDUCATIONAL_RULES:
                rule_errors = apply_rule(self.analyzer.context, rule)
                all_errors.extend(rule_errors)

            self.errors_by_line = defaultdict(list)
            for error in all_errors:
                lines = error.get("lines", [])
                if lines:
                    for line_num in lines:
                        self.errors_by_line[line_num].append(error)

            self.display_all_lines()
            self.statusBar().showMessage(f"Найдено ошибок: {len(all_errors)}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка анализа", f"Ошибка при анализе:\n{str(e)}")
        finally:
            try:
                os.remove("data/temp_ast.json")
            except:
                pass
            self.analyze_btn.setEnabled(True)

    def display_all_lines(self):  
        """Отображает ВСЕ строки кода в таблице"""
        self.clear_results()
        self.code_lines = self.code_editor.toPlainText().splitlines()  
        
        if not self.code_lines:
            return
        
        self.results_table.setRowCount(len(self.code_lines))
        
        # ✅ Используем указанный словарь severity
        severity = {
            'error': (3, QColor(255, 100, 100)), 
            'warning': (2, QColor(255, 255, 150)), 
            'medium': (1, QColor(255, 200, 100)), 
            'info': (0, QColor(150, 255, 150)),
            'high': (4, QColor(255, 100, 200))
        }
        
        for row, line_text in enumerate(self.code_lines):
            line_num = row + 1
            
            # Колонка 0: Код ошибки (была 1)
            code_item = QTableWidgetItem("")
            self.results_table.setItem(row, 0, code_item)
            
            # Колонка 1: Строка кода (была 2)
            code_line_item = QTableWidgetItem(line_text or "")
            self.results_table.setItem(row, 1, code_line_item)
            
            # Колонка 2: Ошибка (была 3)
            errors = self.errors_by_line.get(line_num, [])
            if errors:
                codes = []
                error_texts = []
                
                for error in errors:
                    sev = error.get('severity', 'info')
                    code = error.get('code', 'N/A')
                    msg = error.get('message', '')
                    error_text = f"[{code}] {sev.upper()}: {msg}"
                    error_texts.append(error_text)
                    codes.append(code)
                
                # Максимальная серьезность из словаря severity
                max_severity = max((e.get('severity', 'info') for e in errors), 
                                 key=lambda s: severity.get(s, (0, QColor(200, 200, 200)))[0])
                error_color = severity.get(max_severity, (0, QColor(200, 200, 200)))[1]
                
                # Колонка 0: Код ошибки
                code_item.setText(", ".join(set(codes)))
                code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                code_item.setBackground(error_color)
                
                # Колонка 2: Текст ошибки
                error_item = QTableWidgetItem("\n".join(error_texts))
                error_item.setBackground(error_color)
                self.results_table.setItem(row, 2, error_item)
            else:
                # Пустая колонка ошибок для строк без ошибок
                self.results_table.setItem(row, 2, QTableWidgetItem(""))
        
        self.results_table.resizeColumnsToContents()
        self.results_table.resizeRowsToContents()
        self.results_table.scrollToTop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = CodeCheckerApp()
    window.show()
    sys.exit(app.exec())
