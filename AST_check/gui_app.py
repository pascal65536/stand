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
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QFileDialog,
)
from PyQt6.QtCore import Qt


def check_code_custom(ast_dict):
    """
    Пользовательская функция анализа AST.
    Принимает сериализуемый словарь AST.
    Возвращает строку с результатом проверки.
    Идёт отладка в custom_check.py
    """
    return 1


def ast_to_serializable(node):
    """Рекурсивно преобразует AST в сериализуемую структуру"""
    if isinstance(node, ast.AST):
        result = {"_type": type(node).__name__}
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_serializable(value)
        return result
    elif isinstance(node, list):
        return [ast_to_serializable(item) for item in node]
    else:
        return node


def serializable_to_ast(data):
    """Рекурсивно преобразует сериализуемую структуру обратно в AST"""
    if isinstance(data, dict) and "_type" in data:
        node_type = data["_type"]
        node_class = getattr(ast, node_type)
        kwargs = {}
        for field in node_class._fields:
            if field in data:
                kwargs[field] = serializable_to_ast(data[field])
        return node_class(**kwargs)
    elif isinstance(data, list):
        return [serializable_to_ast(item) for item in [item for item in data]]
    else:
        return data


class ASTViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python AST Viewer с проверкой JSON")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Верхняя панель: редактор + дерево
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

        # Правая панель: AST дерево
        self.ast_tree = QTreeWidget()
        self.ast_tree.setHeaderLabel("AST")

        top_layout.addWidget(left_panel, 1)
        top_layout.addWidget(self.ast_tree, 2)

        # Нижнее текстовое поле: результат проверки
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setMaximumHeight(120)
        self.result_output.setPlaceholderText(
            "Результат проверки AST → JSON → AST появится здесь..."
        )

        # Сборка макета
        main_layout.addLayout(top_layout, 4)
        main_layout.addWidget(self.result_output, 1)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Python-файл", "", "Python Files (*.py)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                self.code_editor.setPlainText(code)
            except Exception as e:
                self.code_editor.setPlainText(f"# Ошибка загрузки файла:\n{e}")

    def save_json_ast(self):
        code = self.code_editor.toPlainText()
        if not code.strip():
            return
        try:
            tree = ast.parse(code)
            serializable = ast_to_serializable(tree)
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить AST как JSON", "", "JSON Files (*.json)"
            )
            if file_path:
                if not file_path.endswith(".json"):
                    file_path += ".json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(serializable, f, indent=2, ensure_ascii=False)
                self.result_output.append(f"\n✅ JSON сохранён: {file_path}")
        except Exception as e:
            self.result_output.append(f"\n❌ Ошибка сохранения JSON: {e}")

    def _ast_to_tree_item(self, node):
        if isinstance(node, ast.AST):
            label = type(node).__name__
            extra = []
            if hasattr(node, "name"):
                extra.append(f"name='{node.name}'")
            elif hasattr(node, "id"):
                extra.append(f"id='{node.id}'")
            elif hasattr(node, "value"):
                val = repr(node.value)
                if len(val) > 30:
                    val = val[:27] + "..."
                extra.append(f"value={val}")
            if extra:
                label += f" ({', '.join(extra)})"

            item = QTreeWidgetItem([label])
            for field, value in ast.iter_fields(node):
                if value is None:
                    continue
                child = QTreeWidgetItem([f"{field}:"])
                item.addChild(child)
                if isinstance(value, list):
                    for elem in value:
                        child.addChild(self._ast_to_tree_item(elem))
                else:
                    child.addChild(self._ast_to_tree_item(value))
            return item
        else:
            return QTreeWidgetItem([repr(node)])

    def update_all(self):
        code = self.code_editor.toPlainText()
        self.ast_tree.clear()
        self.result_output.clear()

        if not code.strip():
            self.result_output.setPlainText("Пустой исходный код.")
            return

        # 1. Парсим AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            error_msg = f"Ошибка синтаксиса при парсинге AST:\n{e}"
            self.result_output.setPlainText(error_msg)
            error_item = QTreeWidgetItem([error_msg])
            self.ast_tree.addTopLevelItem(error_item)
            return
        except Exception as e:
            error_msg = f"Неожиданная ошибка при парсинге AST:\n{e}"
            self.result_output.setPlainText(error_msg)
            return

        # 2. Отображаем AST дерево
        try:
            root_item = self._ast_to_tree_item(tree)
            self.ast_tree.addTopLevelItem(root_item)
            self.ast_tree.expandAll()
        except Exception as e:
            self.result_output.append(f"Ошибка отображения AST: {e}")

        # 3. Конвертируем AST → сериализуемый словарь (для JSON и анализа)
        try:
            serializable = ast_to_serializable(tree)
        except Exception as e:
            self.result_output.setPlainText(
                f"Ошибка преобразования AST в сериализуемый формат:\n{e}"
            )
            return

        # 4. Вызываем пользовательскую проверку
        check_result = check_code_custom(serializable)

        # 5. Выводим результат проверки
        self.result_output.setPlainText(str(check_result))


def main():
    app = QApplication(sys.argv)
    window = ASTViewer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
