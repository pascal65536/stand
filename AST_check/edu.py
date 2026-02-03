import ast
import pprint
from behoof import load_json, save_json
from collections import defaultdict


def ast_to_serializable(node):
    """
    Рекурсивно преобразует AST в сериализуемую структуру с сохранением позиций
    """
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


def serializable_to_ast(data):
    """
    Рекурсивно преобразует сериализуемую структуру обратно в AST
    """
    if isinstance(data, dict) and "_type" in data:
        node_type = data["_type"]
        node_class = getattr(ast, node_type)
        kwargs = {}
        for field in node_class._fields:
            if field in data:
                kwargs[field] = serializable_to_ast(data[field])
        node = node_class(**kwargs)
        if "lineno" in data:
            node.lineno = data["lineno"]
        if "col_offset" in data:
            node.col_offset = data["col_offset"]
        return node
    elif isinstance(data, list):
        return [serializable_to_ast(item) for item in data]
    else:
        return data


class ProgrammingError:
    """
    Структура данных для представления ошибки
    """

    def __init__(
        self, rule_id, severity, lineno, message, pedagogical_note="", node=None
    ):
        self.rule_id = rule_id
        self.severity = severity
        self.lineno = lineno
        self.message = message
        self.pedagogical_note = pedagogical_note
        self.node = node

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "lineno": self.lineno,
            "message": self.message,
            "pedagogical_note": self.pedagogical_note,
        }

    def __repr__(self):
        icon = (
            "❌"
            if self.severity == "error"
            else "⚠️" if self.severity == "warning" else "💡"
        )
        return f"{icon} [{self.rule_id}] строка {self.lineno}: {self.message}"


class ASTJSONAnalyzer:
    """
    Анализатор ошибок на основе сериализованного AST
    """

    BUILTIN_NAMES = {
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
        "__import__",
    }
    DANGEROUS_FUNCTIONS = {"eval", "exec", "compile", "__import__"}
    FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "shutil", "pickle"}

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
        """
        Основной метод анализа
        """
        self.errors = []
        self.collect_context(ast_json)
        self.apply_rules(ast_json)
        return self.errors

    def collect_context(self, node):
        """
        Сбор контекстной информации для анализа
        """
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
                        module_key = f"{module}.{name['name']}"
                        module_lineno = name.get("lineno", 0)
                        module_asname = name.get("asname")
                        self.context["import_from"][module_key].add(module_lineno)
                        if module_asname:
                            mak = f"{module}.{name['name']} as {module_asname}"
                            self.context["import_asname"][mak].add(module_lineno)
                case "Import":
                    for alias in node.get("names", []):
                        module = alias.get("name")
                        if module:
                            self.context["imports"][module].add(lineno)
                case "Name":
                    var_name = node.get("id")
                    ctx = node.get("ctx", {}).get("_type")
                    if ctx:
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

    def apply_rules(self, node):
        """
        Применение правил анализа (заглушка - логика вынесена в отдельную функцию)
        """
        if isinstance(node, list):
            for item in node:
                self.apply_rules(item)
        elif isinstance(node, dict):
            pass  # Правила применяются через apply_rule к context


def apply_rule(analysis_dict, rule):
    """
    Применяет правило к словарю анализа
    """
    violations = []

    if rule["check"] == "absent":
        if rule["target"] not in analysis_dict:
            return []
        return [
            {
                "code": rule["code"],
                "lines": [],
                "message": rule["message"],
                "severity": rule.get("severity", "medium"),
            }
        ]

    collection = analysis_dict.get(rule["target"], {})
    if not collection:
        return []

    safe_context = {
        "len": len,
        "set": set,
        "any": any,
        "all": all,
        "range": range,
        "__builtins__": {},
    }

    for name, lines_set in collection.items():
        lines = sorted(lines_set)
        count = len(lines)

        context = {**safe_context, "name": name, "lines": lines, "count": count}

        try:
            if eval(rule["condition"], {"__builtins__": {}}, context):
                message = rule["message"].format(
                    name=name,
                    lines=lines,
                    count=count,
                    first_line=lines[0] if lines else None,
                )
                violations.append(
                    {
                        "code": rule["code"],
                        "lines": lines,
                        "name": name,
                        "message": message,
                        "severity": rule.get("severity", "medium"),
                    }
                )
        except Exception as e:
            violations.append(
                {
                    "code": "RULE_ERROR",
                    "message": f"Ошибка в правиле {rule['code']}: {e}",
                    "severity": "critical",
                }
            )

    return violations


if __name__ == "__main__":
    # Тестирование сериализации AST
    filepath = "ast_checker_sample.py"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            test_code = f.read()
        tree = ast.parse(test_code)
        serialized = ast_to_serializable(tree)
        save_json("data", "ast.json", serialized)

        loaded = load_json("data", "ast.json")
        restored_tree = serializable_to_ast(loaded)
        ast.fix_missing_locations(restored_tree)
        restored_code = ast.unparse(restored_tree)
        print("Восстановленный код:")
        print(restored_code)
        print("\n" + "=" * 50 + "\n")
    except FileNotFoundError:
        print("Файл ast_checker_sample.py не найден, пропускаем тест сериализации")

    # Тестирование анализатора
    try:
        sample_json = load_json("data", "ast.json")
        analyzer = ASTJSONAnalyzer()
        analyzer.analyze(sample_json)

        try:
            from rules import EDUCATIONAL_RULES as rules
        except ImportError:
            print("Файл rules.py не найден, пропускаем применение правил")
            rules = []

        print("Результаты анализа:")
        for rule in rules:
            errors = apply_rule(analyzer.context, rule)
            if errors:
                pprint.pprint(errors)
                print()
    except Exception as e:
        print(f"Ошибка при анализе: {e}")
