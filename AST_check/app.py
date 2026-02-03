import sys
import os
import ast
import pprint
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QTextEdit, QTableWidget, 
                           QTableWidgetItem, QFileDialog, QSplitter, 
                           QHeaderView, QAbstractItemView, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from collections import defaultdict

# ВСТРАИВАЕМ ВСЕ НЕОБХОДИМЫЕ ФУНКЦИИ И КЛАССЫ ИЗ edu.py
def ast_to_serializable(node):
    """Рекурсивно преобразует AST в сериализуемую структуру с сохранением позиций"""
    if isinstance(node, ast.AST):
        result = {"_type": type(node).__name__}
        if hasattr(node, "lineno"):
            result["lineno"] = node.lineno
        if hasattr(node, "col_offset"):
            result["col_offset"] = node.col_offset
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_serializable(value)
        return result
    elif isinstance(node, list):
        return [ast_to_serializable(item) for item in node]
    else:
        return node

def save_json(folder, filename, data):
    """Простая реализация save_json для совместимости"""
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(folder, filename):
    """Простая реализация load_json для совместимости"""
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

class ASTJSONAnalyzer:
    """Анализатор ошибок на основе сериализованного AST"""
    def __init__(self):
        self.errors = []
        self.context = {
            "store_vars": defaultdict(set),
            "load_vars": defaultdict(set),
            "imports": defaultdict(set),
            "import_from": defaultdict(set),
            "import_asname": defaultdict(set),
            "function_calls": defaultdict(set),
            "declared_vars": defaultdict(set),
            "class_names": defaultdict(set),
            "function_names": defaultdict(set),
            "current_scope": "global",
            "scope_stack": ["global"],
        }

    def analyze(self, ast_json):
        """Основной метод анализа"""
        self.errors = []
        self.collect_context(ast_json)
        return self.errors

    def collect_context(self, node):
        """Сбор контекстной информации для анализа"""
        if isinstance(node, list):
            for item in node:
                self.collect_context(item)
        elif isinstance(node, dict):
            node_type = node.get("_type")
            lineno = node.get("lineno", 0)
            
            match node_type:
                case "ImportFrom":
                    module = node.get("module")
                    if module:
                        self.context["imports"][module].add(lineno)
                    for name in node.get("names", []):
                        module_key = f"{module}.{name.get('name', '')}"
                        module_lineno = name.get("lineno", 0)
                        module_asname = name.get("asname")
                        self.context["import_from"][module_key].add(module_lineno)
                        if module_asname:
                            mak = f"{module}.{name.get('name', '')} as {module_asname}"
                            self.context["import_asname"][mak].add(module_lineno)
                case "Import":
                    for alias in node.get("names", []):
                        module = alias.get("name")
                        if module:
                            self.context["imports"][module].add(lineno)
                case "Name":
                    var_name = node.get("id")
                    ctx = node.get("ctx", {}).get("_type")
                    if ctx and var_name:
                        key = f"{ctx.lower()}_vars"
                        self.context[key][var_name].add(lineno)
                case "Call":
                    func_node = node.get("func", {})
                    if func_node.get("_type") == "Name":
                        func_name = func_node.get("id", "")
                    elif func_node.get("_type") == "Attribute":
                        func_name = func_node.get("attr", "")
                    if func_name:
                        self.context["function_calls"][func_name].add(lineno)
                case "Assign":
                    targets = node.get("targets", [])
                    for target in targets:
                        self.collect_context(target)
                case "FunctionDef":
                    func_name = node.get("name", "<anonymous>")
                    self.context["function_names"][func_name].add(lineno)
                    self.context["scope_stack"].append(f"function:{func_name}")
                    self.context["current_scope"] = f"function:{func_name}"
                    for item in node.get("body", []):
                        self.collect_context(item)
                    self.context["scope_stack"].pop()
                    cs = "global"
                    if self.context["scope_stack"]:
                        cs = self.context["scope_stack"][-1]
                    self.context["current_scope"] = cs
                case "ClassDef":
                    class_name = node.get("name", "<anonymous>")
                    self.context["class_names"][class_name].add(lineno)
                    self.context["scope_stack"].append(f"class:{class_name}")
                    self.context["current_scope"] = f"class:{class_name}"
                    for item in node.get("body", []):
                        self.collect_context(item)
                    self.context["scope_stack"].pop()
                    cs = "global"
                    if self.context["scope_stack"]:
                        cs = self.context["scope_stack"][-1]
                    self.context["current_scope"] = cs

            for value in node.values():
                if value is None:
                    continue
                self.collect_context(value)

def apply_rule(analysis_dict, rule):
    """Применяет правило к словарю анализа"""
    violations = []
    
    if rule.get("check") == "absent":
        if rule["target"] not in analysis_dict:
            return []
        return [{
            "code": rule["code"],
            "lines": [],
            "message": rule["message"],
            "severity": rule.get("severity", "medium"),
        }]

    collection = analysis_dict.get(rule["target"], {})
    if not collection:
        return []

    safe_context = {
        "len": len, "set": set, "any": any, "all": all, "range": range,
        "__builtins__": {},
    }

    for name, lines_set in collection.items():
        lines = sorted(lines_set)
        count = len(lines)
        context = {**safe_context, "name": name, "lines": lines, "count": count}

        try:
            if eval(rule["condition"], {"__builtins__": {}}, context):
                message = rule["message"].format(
                    name=name, lines=lines, count=count,
                    first_line=lines[0] if lines else None,
                )
                violations.append({
                    "code": rule["code"],
                    "lines": lines,
                    "name": name,
                    "message": message,
                    "severity": rule.get("severity", "medium"),
                })
        except Exception:
            pass

    return violations

# БАЗОВЫЕ ПРАВИЛА ДЛЯ ТЕСТИРОВАНИЯ
EDUCATIONAL_RULES = [
    {
        "code": "EDU-VAR-001",
        "target": "store_vars",
        "condition": "len(name) == 1 and name.islower()",
        "message": "Односимвольное имя переменной '{name}'",
        "severity": "warning"
    },
    {
        "code": "EDU-FUNC-001", 
        "target": "function_calls",
        "condition": "name in ['eval', 'exec', 'compile']",
        "message": "Опасная функция '{name}'",
        "severity": "error"
    },
    {
        "code": "EDU-IMP-001",
        "target": "imports", 
        "condition": "name in ['os', 'sys', 'subprocess']",
        "message": "Запрещенный импорт '{name}'",
        "severity": "error"
    }
]

# ОСНОВНОЕ ПРИЛОЖЕНИЕ
class CodeCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AST Educational Code Checker")
        self.resize(1400, 800)
        self.code_lines = []
        self.current_file = None
        self.analyzer = None
        self.errors_by_line = {}  # Словарь ошибок по строкам
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        buttons_layout = QHBoxLayout()
        self.load_btn = QPushButton("📂 Открыть файл (Ctrl+O)")
        self.load_btn.setShortcut("Ctrl+O")
        self.load_btn.clicked.connect(self.load_file)
        
        self.analyze_btn = QPushButton("🚀 Анализировать (F5)")
        self.analyze_btn.setShortcut("F5")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        self.clear_btn = QPushButton("🧹 Очистить")
        self.clear_btn.clicked.connect(self.clear_all)
        
        buttons_layout.addWidget(self.load_btn)
        buttons_layout.addWidget(self.analyze_btn)
        buttons_layout.addWidget(self.clear_btn)
        buttons_layout.addStretch()
        
        # Левая панель - редактор кода
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.code_editor = QTextEdit()
        code_font = QFont("Consolas", 11)
        self.code_editor.setFont(code_font)
        self.code_editor.setPlaceholderText(
            "Введите Python-код для анализа или загрузите файл (Ctrl+O)...\n"
            "Примеры проблем:\n"
            "• Односимвольные переменные (a, x, i)\n"
            "• eval(), exec(), compile()\n"
            "• Импорты os, sys, subprocess"
        )
        left_layout.addWidget(self.code_editor)
        
        # Правая панель - таблица со ВСЕМИ строками
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["№", "Код", "Строка кода", "Ошибка"])
        
        # Настройка колонок таблицы
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # №
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Код
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Строка
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # Ошибка
        
        table_font = QFont("Consolas", 10)
        self.results_table.setFont(table_font)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.results_table)
        
        # Сплиттер
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(splitter)
        self.statusBar().showMessage("Готов к анализу кода ✅")

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть Python файл", "", 
            "Python файлы (*.py);;Все файлы (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.code_editor.setPlainText(code)
                self.current_file = file_path
                self.code_lines = code.split('\n')
                self.statusBar().showMessage(f"Загружен: {os.path.basename(file_path)}")
                self.clear_results()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{str(e)}")

    def run_analysis(self):
        code = self.code_editor.toPlainText()
        if not code.strip():
            QMessageBox.warning(self, "Предупреждение", "Введите код для анализа!")
            return
        
        try:
            self.statusBar().showMessage("🔍 Анализируем...")
            self.analyze_btn.setEnabled(False)
            
            # Парсим и анализируем
            tree = ast.parse(code)
            serialized = ast_to_serializable(tree)
            save_json("data", "temp_ast.json", serialized)
            
            self.analyzer = ASTJSONAnalyzer()
            ast_json = load_json("data", "temp_ast.json")
            self.analyzer.analyze(ast_json)
            
            # Собираем все ошибки
            all_errors = []
            for rule in EDUCATIONAL_RULES:
                rule_errors = apply_rule(self.analyzer.context, rule)
                all_errors.extend(rule_errors)
            
            # Группируем ошибки по строкам
            self.errors_by_line = defaultdict(list)
            for error in all_errors:
                lines = error.get('lines', [])
                if lines:
                    for line_num in lines:
                        self.errors_by_line[line_num].append(error)
            
            # Показываем ВСЕ строки с ошибками в соответствующих строках
            self.display_all_lines()
            self.statusBar().showMessage(f"✅ Найдено ошибок: {len(all_errors)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка анализа:\n{str(e)}")
        finally:
            try:
                os.remove("data/temp_ast.json")
            except:
                pass
            self.analyze_btn.setEnabled(True)

    def display_all_lines(self):
        """Отображает ВСЕ строки кода в таблице"""
        self.clear_results()
        self.code_lines = self.code_editor.toPlainText().split('\n')
        
        if not self.code_lines:
            return
        
        # Устанавливаем количество строк = количество строк кода
        self.results_table.setRowCount(len(self.code_lines))
        
        for row, line_text in enumerate(self.code_lines):
            line_num = row + 1
            
            # Колонка 1: Номер строки
            num_item = QTableWidgetItem(str(line_num))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 0, num_item)
            
            # Колонка 2: Код ошибки (пусто если нет ошибок)
            code_item = QTableWidgetItem("")
            self.results_table.setItem(row, 1, code_item)
            
            # Колонка 3: Строка кода
            code_line_item = QTableWidgetItem(line_text or "")
            self.results_table.setItem(row, 2, code_line_item)
            
            # Колонка 4: Ошибки (если есть)
            errors = self.errors_by_line.get(line_num, [])
            if errors:
                # Собираем все ошибки для этой строки
                error_texts = []
                for error in errors:
                    severity = error.get('severity', 'info')
                    code = error.get('code', 'N/A')
                    msg = error.get('message', '')
                    error_text = f"[{code}] {severity.upper()}: {msg}"
                    error_texts.append(error_text)
                
                error_item = QTableWidgetItem("\n".join(error_texts))
                # Цвет фона по уровню самой серьезной ошибки
                severity_colors = {
                    'error': QColor(255, 100, 100),
                    'warning': QColor(255, 255, 150),
                    'medium': QColor(255, 200, 100),
                }
                max_severity = max((e.get('severity', 'info') for e in errors), 
                                 key=lambda s: {'error': 3, 'warning': 2, 'medium': 1, 'info': 0}[s])
                error_item.setBackground(severity_colors.get(max_severity, QColor(200, 200, 200)))
                self.results_table.setItem(row, 3, error_item)
                
                # Подсвечиваем код ошибки
                code_item.setText(", ".join(e.get('code', 'N/A') for e in errors))
                code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                code_item.setBackground(severity_colors[max_severity])
            else:
                # Пустая строка без ошибок
                error_item = QTableWidgetItem("")
                self.results_table.setItem(row, 3, error_item)
        
        self.results_table.resizeColumnsToContents()
        self.results_table.resizeRowsToContents()
        self.results_table.scrollToTop()

    def get_severity_color(self, severity):
        """Возвращает цвет для уровня серьезности"""
        colors = {
            'error': QColor(255, 100, 100),
            'warning': QColor(255, 255, 150),
            'medium': QColor(255, 200, 100),
            'info': QColor(150, 255, 150)
        }
        return colors.get(severity, QColor(200, 200, 200))

    def clear_all(self):
        self.code_editor.clear()
        self.clear_results()
        self.current_file = None
        self.analyzer = None
        self.errors_by_line = {}
        self.statusBar().showMessage("🧹 Очищено")

    def clear_results(self):
        self.results_table.setRowCount(0)
        self.results_table.clearContents()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CodeCheckerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
