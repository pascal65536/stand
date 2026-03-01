import ast
import textwrap
import json


class Visitor(ast.NodeVisitor):
    """
    AST-анализатор с Flake8-интеграцией
    Этап 1: Сбор features
    Этап 2: Анализ features → генерация ошибок
    Унифицированные кортежи: (значение, строка, тип)
    """

    def __init__(self):
        self.rows = []
        self.assignments = []
        self.usages = []
        self.all_vars = []
        self.errors = []  # Заполняется ТОЛЬКО на этапе 2
        self.context_stack = []

        self.features = {
            "if": [],
            "name": [],
            "for": [],
            "else": [],
            "constant": [],
            "try": [],
            "while": [],
            "imports": [],
            "calls": [],
            "functions": [],
            "listcomp": [],
            "setcomp": [],
            "dictcomp": [],
            "genexp": [],
        }

    def push_context(self, ctx_type: str, name: str = ""):
        """Вход в новый контекст"""
        self.context_stack.append(f"{ctx_type}:{name}")

    def pop_context(self):
        """Выход из контекста"""
        if self.context_stack:
            self.context_stack.pop()

    def current_context(self) -> str:
        """Текущий контекст"""
        return self.context_stack[-1] if self.context_stack else "global"

    def read_rows(self, code_str: str):
        """Читает строки исходного кода"""
        self.rows = [row for row in code_str.splitlines()]

    # ========== IMPORTS ==========
    def visit_ImportFrom(self, node):
        module = node.module or "unknown"
        for alias in node.names:
            import_name = f"{alias.name}"
            if alias.asname:
                import_name += f" as {alias.asname}"
            self.features["imports"].append(
                (f"{module}: {import_name}", node.lineno, "import")
            )
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.features["imports"].append((alias.name, node.lineno, "import"))
        self.generic_visit(node)

    # ========== CALLS ==========
    def visit_Call(self, node):
        name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr if isinstance(node.func, ast.Attribute) else "unknown"
        )
        self.features["calls"].append((name, node.lineno, "call"))
        self.generic_visit(node)

    def visit_Exec(self, node):
        self.features["calls"].append(("exec", node.lineno, "exec"))
        self.generic_visit(node)

    def visit_Eval(self, node):
        self.features["calls"].append(("eval", node.lineno, "eval"))
        self.generic_visit(node)

    # ========== FUNCTIONS ==========
    def visit_FunctionDef(self, node):
        self.features["functions"].append((node.name, node.lineno, "function"))
        self.push_context("function", node.name)

        for arg in getattr(node.args, "args", []):
            if isinstance(arg, ast.arg):
                self.features["name"].append((arg.arg, arg.lineno, "arg"))

        for stmt in node.body:
            if not isinstance(
                stmt, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)
            ):
                self.visit(stmt)

        self.pop_context()

    def visit_AsyncFunctionDef(self, node):
        self.features["functions"].append(
            (f"async {node.name}", node.lineno, "async_function")
        )
        self.generic_visit(node)

    # ========== CONTROL FLOW ==========
    def visit_If(self, node):
        ctx = self.current_context()
        self.features["if"].append(("if", node.lineno, f"in {ctx}"))
        if node.orelse:
            self.features["else"].append(("else", node.lineno, "block"))
        self.generic_visit(node)

    def visit_For(self, node):
        ctx = self.current_context()
        self.features["for"].append(("for", node.lineno, f"in {ctx}"))
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        ctx = self.current_context()
        self.features["for"].append(("async_for", node.lineno, f"in {ctx}"))
        self.generic_visit(node)

    def visit_While(self, node):
        ctx = self.current_context()
        self.features["while"].append(("while", node.lineno, f"in {ctx}"))
        self.generic_visit(node)

    def visit_Try(self, node):
        ctx = self.current_context()
        self.features["try"].append(("try", node.lineno, f"in {ctx}"))
        self.generic_visit(node)

    def visit_TryStar(self, node):
        ctx = self.current_context()
        self.features["try"].append(("try_star", node.lineno, f"in {ctx}"))
        self.generic_visit(node)

    # ========== COMPREHENSIONS ==========
    def visit_ListComp(self, node):
        elt_str = (
            node.elt.id
            if isinstance(node.elt, ast.Name)
            else (
                str(ast.unparse(node.elt)) if hasattr(ast, "unparse") else str(node.elt)
            )
        )
        comp_info = (
            f"g={len(node.generators)},ifs={sum(len(g.ifs) for g in node.generators)}"
        )
        self.features["listcomp"].append((elt_str, node.lineno, comp_info))
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.features["setcomp"].append(("set", node.lineno, "comprehension"))
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.features["dictcomp"].append(("dict", node.lineno, "comprehension"))
        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        self.features["genexp"].append(("generator", node.lineno, "expression"))
        self.generic_visit(node)

    # ========== VARIABLES & CONSTANTS ==========
    def visit_Name(self, node):
        ctx = self.current_context()
        node_type = (
            "assign"
            if isinstance(node.ctx, ast.Store)
            else (
                "usage"
                if isinstance(node.ctx, ast.Load)
                else "delete" if isinstance(node.ctx, ast.Del) else "name"
            )
        )
        self.features["name"].append((node.id, node.lineno, node_type))

        if isinstance(node.ctx, ast.Store):
            self.assignments.append(node.id)
            self.all_vars.append(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.usages.append(node.id)
            self.all_vars.append(node.id)
        elif isinstance(node.ctx, ast.Del):
            self.all_vars.append(node.id)
        self.generic_visit(node)

    def visit_Constant(self, node):
        value = node.value if isinstance(node.value, str) else str(node.value)
        self.features["constant"].append((value, node.lineno, "constant"))
        self.generic_visit(node)

    # ========== CLASSES ==========
    def visit_ClassDef(self, node):
        ctx = self.current_context()
        self.features["functions"].append((node.name, node.lineno, f"class in {ctx}"))
        self.push_context("class", node.name)

        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.features["functions"].append((stmt.name, stmt.lineno, "method"))

        self.pop_context()

    # ========== ASSIGNMENTS ==========
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.features["name"].append((target.id, node.lineno, "assign"))
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.features["name"].append((node.target.id, node.lineno, "ann_assign"))
        self.generic_visit(node)

    # def analyze_features(self):
    #     """
    #     Создание ошибок
    #     """
    #     self.errors = []

    #     RULES = {
    #         "calls": {
    #             "exec": {"error": "SEC001"},
    #             "eval": {"error": "SEC002"},
    #             "input": {"error": "SEC003"},
    #             "raw_input": {"error": "SEC004"},
    #             "open": {"error": "SEC005"},
    #             "__import__": {"error": "SEC005"},
    #         },
    #         "for": {
    #             None: {"error": "FOR002"},
    #         },
    #         "if": {
    #             None: {"error": "CA001"},
    #         },
    #         "try": {
    #             None: {"error": "CA002"},
    #         },
    #         "while": {
    #             None: {"error": "CA003"},
    #         },
    #         "constant": {
    #             None: {"error": "SEC003"},
    #         },
    #         "name": {
    #             None: {"error": "W001"},
    #         },
    #     }

    #     for key, variables_lst in self.features.items():
    #         if not variables_lst:
    #             continue
    #         for name, lineno, call_type in variables_lst:
    #             rules_dct = RULES.get(key, {})

    #             error_dct = rules_dct.get(None) or rules_dct.get(name)
    #             if not error_dct:
    #                 continue

    #             print(error_dct, name, lineno, call_type)
    #             # error = rules_dct["error"]
    #             # error = '123'
    #             # self.errors.append(
    #             #     (lineno, error, f"{name.capitalize()} in {call_type} prohibited")
    #             # )

    #             # if key == 'calls':
    #             #     if name in ["exec", "eval"]:
    #             #         self.errors.append((lineno, 0, "SEC001", f"{call_type.capitalize()} prohibited"))
    #             #     if name in ["input", "raw_input", "open", "__import__"]:
    #             #         self.errors.append((lineno, 0, "SEC002", f"dangerous call '{name}' prohibited"))
    #             # if key == 'for':
    #             #     self.errors.append((lineno, 0, "FOR002", f"{name.capitalize()} in {call_type} prohibited"))
    #             # if key == 'if':
    #             #     self.errors.append((lineno, 0, "CA001", f"{name.capitalize()} in {call_type} prohibited"))
    #             # if key == 'while':
    #             #     self.errors.append((lineno, 0, "CA003", f"{name.capitalize()} in {call_type} prohibited"))
    #             # if key == 'try':
    #             #     self.errors.append((lineno, 0, "CA002", f"{name.capitalize()} in {call_type} prohibited"))
    #             # if key == 'constant':
    #             #     if isinstance(name, str) and len(name) > 100:
    #             #         self.errors.append((lineno, 0, "SEC003", "suspicious long string"))
    #             # if key == 'name':
    #             #     if name in self.assignments and name not in self.usages:
    #             #         self.errors.append((lineno, 0, "W001", f"unused variable '{name}'"))

    RULES_JSON = {
        "calls": {
            "specific": {
                "exec": {"code": "SEC001", "message": "exec prohibited"},
                "eval": {"code": "SEC002", "message": "eval prohibited"},
                "input": {"code": "SEC003", "message": "input prohibited"},
            },
            "any": {"code": "SEC999", "message": "unknown call '{name}'",},
        },
        "if": {
            "any": {"code": "CA001", "message": "if prohibited"},
        },
        "for": {
            "any": {"code": "FOR001", "message": "for prohibited"},
        },
        "constant": {
            "conditions": [
                {
                    "check": "len(name) > 100", 
                    "code": "SEC004", 
                    "message": "long string",
                }
            ],
            "any": {"code": "SEC005", "message": "suspicious constant"},
        },
        "name": {
            "conditions": [
                {
                    "check": "name in self.assignments and name not in self.usages",
                    "code": "W001",
                    "message": "unused variable '{name}'",
                }
            ]
        },
    }

    def _check_condition(self, check_str, name, lineno, call_type):
        """
        Расширенные проверки
        """
        if check_str == "len(name) > 100":
            return isinstance(name, str) and len(name) > 100
        elif check_str == "name in self.assignments and name not in self.usages":
            return name in self.assignments and name not in self.usages
        elif check_str == "len(name) < 2":
            return len(str(name)) < 2
        elif check_str == "name.startswith('__') and name.endswith('__')":
            return str(name).startswith('__') and str(name).endswith('__')
        elif check_str == "name.isupper()":
            return str(name).isupper()
        elif check_str == "'print' in name":
            return 'print' in str(name)
        elif check_str == "lineno > 100":
            return lineno > 100
        elif check_str == "call_type == 'call'":
            return call_type == 'call'
        elif check_str == "isinstance(name, str)":
            return isinstance(name, str)
        elif check_str == "name.count('_') > 2":
            return str(name).count('_') > 2
        elif check_str == "'test' in name":
            return 'test' in str(name)
        elif check_str == "len(name.split('.')) > 1":
            return len(str(name).split('.')) > 1 
        elif check_str == "name[0].islower()":
            return str(name) and str(name)[0].islower()
        elif check_str == "'lambda' in call_type":
            return 'lambda' in str(call_type)
        return False

        
    def analyze_features(self):
        self.errors = []
        for feature_key, items in self.features.items():
            if not items:
                continue

            rules = self.RULES_JSON.get(feature_key, {})

            for name, lineno, call_type in items:
                error_found = False

                if "specific" in rules:
                    specific_rule = rules["specific"].get(name)
                    if specific_rule:
                        msg = specific_rule["message"].format(name=name, lineno=lineno, call_type=call_type)
                        self.errors.append((lineno, 0, specific_rule["code"], msg))
                        error_found = True

                if "conditions" in rules and not error_found:
                    for cond in rules["conditions"]:
                        if self._check_condition(cond["check"], name, lineno, call_type):
                            msg = cond["message"].format(name=name, lineno=lineno, call_type=call_type)
                            self.errors.append((lineno, 0, cond["code"], msg))
                            error_found = True
                            break

                if not error_found and "any" in rules:
                    any_rule = rules["any"]
                    msg = any_rule["message"].format(name=name, lineno=lineno, call_type=call_type)
                    self.errors.append((lineno, 0, any_rule["code"], msg))


def safe_parse(code: str) -> ast.AST:
    """
    Безопасный парсинг любого кода
    """
    dedented = textwrap.dedent(code)
    return ast.parse(dedented)


if __name__ == "__main__":
    filename = "study_6.py"
    with open(filename, "r", encoding="utf-8") as f:
        user_code = f.read()

    tree = safe_parse(user_code)
    visitor = Visitor()
    visitor.read_rows(user_code)
    visitor.visit(tree)
    visitor.analyze_features()

    if visitor.errors:
        print("ОШИБКИ")
        for lineno, col, code_msg, visitor_cls in visitor.errors:
            print(f"  {lineno}:{col} {code_msg} / {visitor_cls}")
        print()
    exit()

    print("FEATURES")
    for k, variables_lst in visitor.features.items():
        if not variables_lst:
            continue
        print()
        print(f"{k.upper()}:")
        for v in variables_lst:
            print(f"  {v}")
        print()
