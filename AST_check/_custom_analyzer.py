"""
Кастомный статический анализатор уязвимостей для Django-проектов.
Находит уязвимости, которые пропускает bandit: XSS, Open Redirect, 
Broken Access Control, CSRF и др.
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional


class DjangoJSONVulnerabilityAnalyzer:
    """
    Анализатор, работающий с JSON-представлением AST.
    """

    def __init__(self, file_path: str, json_ast: Dict[str, Any]):
        self.file_path = file_path
        self.json_ast = json_ast
        self.vulnerabilities = []
        self.current_function_name = None
        self.inside_csrf_exempt = False

    def report(self, node: Dict[str, Any], vulnerability_type: str, description: str):
        """Добавляет найденную уязвимость в отчет."""
        line_no = node.get("lineno", 0)
        self.vulnerabilities.append(
            {
                "file": self.file_path,
                "line": line_no,
                "type": vulnerability_type,
                "description": description,
            }
        )

    def analyze(self):
        """Запускает анализ, начиная с корневого узла AST."""
        self._visit(self.json_ast)

    def _visit(self, node: Any):
        """
        Универсальный метод для обхода узлов.
        Если узел — словарь с ключом '_type', вызываем соответствующий обработчик.
        Если узел — список, обходим каждый элемент.
        """
        if isinstance(node, dict):
            node_type = node.get("_type")
            # Вызываем специфичный обработчик, если он есть
            handler_name = f"_visit_{node_type}"
            handler = getattr(self, handler_name, None)
            if handler:
                handler(node)
            else:
                # Обходим все дочерние узлы
                for key, value in node.items():
                    self._visit(value)
        elif isinstance(node, list):
            for item in node:
                self._visit(item)

    # --- Обработчик для FunctionDef (определение функции) ---
    def _visit_FunctionDef(self, node: Dict[str, Any]):
        """Анализирует определения функций и их декораторы."""
        self.current_function_name = node["name"]

        # Проверяем наличие декоратора @csrf_exempt
        self.inside_csrf_exempt = False
        for decorator in node.get("decorator_list", []):
            if (
                decorator.get("_type") == "Name"
                and decorator.get("id") == "csrf_exempt"
            ):
                self.inside_csrf_exempt = True
                # Проверяем, изменяет ли функция состояние (ищем .save(), .delete() и т.д.)
                if self._function_modifies_state(node):
                    self.report(
                        node,
                        "CSRF_PROTECTION_DISABLED",
                        f"Декоратор @csrf_exempt применен к функции '{node['name']}', которая изменяет состояние. Высокий риск CSRF-атаки.",
                    )

        # Рекурсивно обходим тело функции
        for body_item in node.get("body", []):
            self._visit(body_item)

        self.current_function_name = None
        self.inside_csrf_exempt = False

    # --- Обработчик для Call (вызов функции) ---
    def _visit_Call(self, node: Dict[str, Any]):
        """Анализирует все вызовы функций."""
        func = node.get("func", {})

        # Проверка на engines['django'].from_string(...) для XSS
        if self._is_django_template_from_string(node):
            self._check_xss_in_template_string(node)

        # Проверка на redirect(...) для Open Redirect
        if func.get("_type") == "Name" and func.get("id") == "redirect":
            self._check_open_redirect(node)

        # Проверка на опасные операции с моделями (delete, save) для Broken Access Control
        if self._is_dangerous_model_operation(node):
            self._check_access_control(node)

        # Проверка на request.GET.get('password') для чувствительных данных в GET
        if self._is_get_password_in_get(node):
            self.report(
                node,
                "SENSITIVE_DATA_IN_GET",
                "Чувствительные данные (пароль, токен) передаются через GET-параметр.",
            )

    def _is_django_template_from_string(self, node: Dict[str, Any]) -> bool:
        """Проверяет, является ли вызов `engines['django'].from_string(...)`."""
        func = node.get("func", {})
        if func.get("_type") != "Attribute" or func.get("attr") != "from_string":
            return False

        value = func.get("value", {})
        if value.get("_type") != "Call":
            return False

        inner_func = value.get("func", {})
        if (
            inner_func.get("_type") != "Attribute"
            or inner_func.get("attr") != "from_string"
        ):
            # Проверяем цепочку: engines['django'].from_string
            if value.get("_type") == "Attribute":
                attr_value = value.get("value", {})
                if attr_value.get("_type") == "Subscript":
                    sub_value = attr_value.get("value", {})
                    if (
                        sub_value.get("_type") == "Name"
                        and sub_value.get("id") == "engines"
                    ):
                        slice_ = attr_value.get("slice", {})
                        if (
                            slice_.get("_type") == "Constant"
                            and slice_.get("value") == "django"
                        ):
                            return True
        return False

    def _check_xss_in_template_string(self, node: Dict[str, Any]):
        """Проверяет, первый аргумент — это f-строка (JoinedStr)."""
        args = node.get("args", [])
        if len(args) > 0:
            first_arg = args[0]
            if first_arg.get("_type") == "JoinedStr":
                self.report(
                    node,
                    "XSS_VIA_TEMPLATE",
                    "Обнаружена f-строка в шаблоне Django. Возможна XSS-уязвимость.",
                )

    def _check_open_redirect(self, node: Dict[str, Any]):
        """Проверяет, является ли аргумент redirect() результатом request.GET.get()."""
        args = node.get("args", [])
        if len(args) > 0:
            arg = args[0]
            if arg.get("_type") == "Call":
                func = arg.get("func", {})
                if func.get("_type") == "Attribute" and func.get("attr") == "get":
                    value = func.get("value", {})
                    if value.get("_type") == "Attribute" and value.get("attr") == "GET":
                        request_value = value.get("value", {})
                        if (
                            request_value.get("_type") == "Name"
                            and request_value.get("id") == "request"
                        ):
                            self.report(
                                node,
                                "OPEN_REDIRECT",
                                "Обнаружен Open Redirect: перенаправление на URL из request.GET.",
                            )

    def _is_dangerous_model_operation(self, node: Dict[str, Any]) -> bool:
        """Определяет, является ли вызов опасной операцией над моделью (delete, save)."""
        func = node.get("func", {})
        if func.get("_type") == "Attribute":
            attr = func.get("attr")
            if attr in ["delete", "save", "update", "create"]:
                return True
        return False

    def _check_access_control(self, node: Dict[str, Any]):
        """Упрощенная проверка: просто предупреждаем о наличии опасной операции."""
        func = node.get("func", {})
        attr = func.get("attr", "unknown")
        self.report(
            node,
            "POTENTIAL_BROKEN_ACCESS_CONTROL",
            f"Обнаружена опасная операция '{attr}' без явной проверки прав доступа.",
        )

    def _is_get_password_in_get(self, node: Dict[str, Any]) -> bool:
        """Проверяет вызов request.GET.get() с чувствительными ключами."""
        func = node.get("func", {})
        if func.get("_type") == "Attribute" and func.get("attr") == "get":
            value = func.get("value", {})
            if value.get("_type") == "Attribute" and value.get("attr") == "GET":
                request_value = value.get("value", {})
                if (
                    request_value.get("_type") == "Name"
                    and request_value.get("id") == "request"
                ):
                    args = node.get("args", [])
                    if len(args) > 0:
                        first_arg = args[0]
                        if first_arg.get("_type") == "Constant":
                            key = first_arg.get("value", "")
                            sensitive_keywords = {
                                "pass",
                                "pwd",
                                "secret",
                                "token",
                                "key",
                            }
                            if any(kw in key.lower() for kw in sensitive_keywords):
                                return True
        return False

    def _function_modifies_state(self, node: Dict[str, Any]) -> bool:
        """Определяет, изменяет ли функция состояние (ищет .save(), .delete() в теле функции)."""

        class StateChangeVisitor:
            def __init__(self):
                self.has_state_change = False

            def visit(self, n):
                if isinstance(n, dict):
                    if n.get("_type") == "Call":
                        func = n.get("func", {})
                        if func.get("_type") == "Attribute":
                            if func.get("attr") in [
                                "save",
                                "delete",
                                "update",
                                "create",
                            ]:
                                self.has_state_change = True
                    for value in n.values():
                        self.visit(value)
                elif isinstance(n, list):
                    for item in n:
                        self.visit(item)

        visitor = StateChangeVisitor()
        visitor.visit(node)
        return visitor.has_state_change


def analyze_json_file(file_path: str, json_ast_path: str) -> List[Dict[str, Any]]:
    """Анализирует один файл, используя предварительно сгенерированный JSON AST."""
    try:
        with open(json_ast_path, "r", encoding="utf-8") as f:
            json_ast = json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке JSON AST из {json_ast_path}: {e}")
        return []

    analyzer = DjangoJSONVulnerabilityAnalyzer(file_path, json_ast)
    analyzer.analyze()
    return analyzer.vulnerabilities


def print_report(vulnerabilities: List[Dict[str, Any]]):
    """Выводит отчет об уязвимостях в консоль."""
    if not vulnerabilities:
        print(
            "\n✅ Поздравляем! Кастомный анализатор не обнаружил известных уязвимостей."
        )
        return

    print(f"\n🚨 Обнаружено {len(vulnerabilities)} потенциальных уязвимостей:\n")
    for vuln in vulnerabilities:
        print(f"Файл:     {vuln['file']}")
        print(f"Строка:   {vuln['line']}")
        print(f"Тип:      {vuln['type']}")
        print(f"Описание: {vuln['description']}")
        print("-" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Использование: python custom_analyzer.py <путь_к_исходнику.py> <путь_к_ast.json>"
        )
        print(
            "Пример: python custom_analyzer.py ./insecure_app/views.py ./Pasted_Text_1758296001917.txt"
        )
        sys.exit(1)

    source_file_path = sys.argv[1]
    json_ast_path = sys.argv[2]

    if not os.path.exists(json_ast_path):
        print(f"Ошибка: JSON-файл AST '{json_ast_path}' не существует.")
        sys.exit(1)

    print(f"Запуск кастомного статического анализатора для файла: {source_file_path}")
    print(f"Используется AST из: {json_ast_path}")

    results = analyze_json_file(source_file_path, json_ast_path)
    print_report(results)

    # Возвращаем ненулевой код, если найдены уязвимости (для интеграции с CI/CD)
    sys.exit(1 if results else 0)
