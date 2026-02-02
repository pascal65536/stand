import string
import pprint
import ast
import subprocess
import json
import re


class Checker:
    def __init__(self, filepath):
        self.filepath = filepath
        self.cmd = []
        self.errors = []

    def run(self):
        if not self.cmd:
            return {}
        result = subprocess.run(self.cmd, capture_output=True, text=True)
        return self.parse(result.stdout)

    def parse(self, result):
        return json.loads(result)

    def line(self, lines_dct):
        return lines_dct


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.rows = []
        self.assignments = []
        self.usages = []
        self.all_vars = []
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
            "classes": [],
        }

    def visit_ImportFrom(self, node):
        module = node.module
        for alias in node.names:
            import_name = f"{alias.name}"
            if alias.asname:
                import_name += f" as {alias.asname}"
            self.features["imports"].append((f"{module}: {import_name}", node.lineno))
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.features["imports"].append((alias.name, node.lineno))
        self.generic_visit(node)

    def visit_Call(self, node):
        name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr if isinstance(node.func, ast.Attribute) else "unknown"
        )
        self.features["calls"].append((name, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.features["functions"].append((node.name, node.lineno))
        self.generic_visit(node)

    def visit_If(self, node):
        self.features["if"].append(("if_statement", node.lineno))
        if node.orelse:
            self.features["else"].append(("else_block", node.lineno))
        self.generic_visit(node)

    def visit_For(self, node):
        self.features["for"].append(("for_statement", node.lineno))
        self.generic_visit(node)

    def visit_While(self, node):
        self.features["while"].append(("while_statement", node.lineno))
        self.generic_visit(node)

    def visit_Try(self, node):
        self.features["try"].append(("try_statement", node.lineno))
        self.generic_visit(node)

    def visit_Constant(self, node):
        value = node.value if isinstance(node.value, str) else str(node.value)
        self.features["constant"].append((value, node.lineno))
        self.generic_visit(node)

    def visit_Name(self, node):
        self.features["name"].append((node.id, node.lineno))
        if isinstance(node.ctx, ast.Store):
            self.assignments.append(node.id)
            self.all_vars.append(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.usages.append(node.id)
            self.all_vars.append(node.id)
        elif isinstance(node.ctx, ast.Del):
            self.all_vars.append(node.id)
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.features["listcomp"].append(("list_comprehension", node.lineno))
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.features["setcomp"].append(("set_comprehension", node.lineno))
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.features["dictcomp"].append(("dict_comprehension", node.lineno))
        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        self.features["genexp"].append(("generator_expression", node.lineno))
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_info = {
            "name": node.name,
            "line": node.lineno,
            "bases": [],
            "methods": [],
            "attributes": [],
            "decorators": [],
        }

        # Базовые классы
        for base in node.bases:
            res = base.id if isinstance(base, ast.Name) else str(base)
            class_info["bases"].append(res)

        # Декораторы
        for decorator in node.decorator_list:
            dec_name = "unknown"
            if isinstance(decorator, ast.Name):
                dec_name = decorator.id
            elif isinstance(decorator, ast.Attribute):
                dec_name = decorator.attr
            class_info["decorators"].append(dec_name)

        # Методы и атрибуты
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                class_info["methods"].append(stmt.name)
            elif isinstance(stmt, (ast.AnnAssign, ast.Assign)):
                targets = []
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        targets.append(t.id if isinstance(t, ast.Name) else str(t))
                elif hasattr(stmt, "target") and isinstance(stmt.target, ast.Name):
                    targets.append(stmt.target.id)
                else:
                    targets.append(
                        str(stmt.target) if hasattr(stmt, "target") else "unknown"
                    )
                class_info["attributes"].extend(targets)

        self.features["classes"].append(class_info)
        self.generic_visit(node)

    def read_rows(self, code_str):
        self.rows = [row for row in code_str.splitlines()]


class ASTChecker(Checker):
    name = "ast"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = []
        self.errors = self.run()
        self.rules = [
            {
                "key": "name",
                "rule": "len(x) == 1",
                "msg": "Короткое имя переменной",
                "error": "R001",
            },
            {
                "key": "name",
                "rule": "len(set(x) - set(string.ascii_lowercase + '_' + string.digits)) > 0",
                "msg": "Имя переменной содержит запрещенные символы",
                "error": "R002",
            },
            {
                "key": "name",
                "rule": "len(x) == 1 and x in 'loO'",
                "msg": "Имя переменной похоже на цифру",
                "error": "R003",
            },
            {
                "key": "classes",
                "rule": "not x['name'][0].isupper()",
                "msg": "Имя класса начинается со строчной буквы",
                "error": "R011",
            },
            {
                "key": "imports",
                "rule": "'re' in x[0]",
                "msg": "Нельзя импортировать модуль `re`",
                "error": "R021",
            },
            {
                "key": "genexp",
                "rule": "True",
                "msg": "Нельзя использовать генераторные выражения",
                "error": "R031",
            },
            {
                "key": "calls",
                "rule": "x in ['eval', 'exec']",
                "msg": "Нельзя использовать опасные функции",
                "error": "R032",
            },
        ]

    def run(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                code_str = f.read()
        except FileNotFoundError:
            print(f"Файл {self.filepath} не найден!")
            return {}

        tree = ast.parse(code_str)
        visitor = Visitor()
        visitor.read_rows(code_str)
        visitor.visit(tree)
        return visitor.features

    def line(self, lines_dct):
        features = self.errors

        for rule in self.rules:
            key = rule["key"]
            if key not in features or not features[key]:
                continue

            for item in features[key]:
                if key == "classes":
                    x = item["name"]
                    line = item["line"]
                else:
                    x = item[0]
                    line = item[1]

                if not eval(rule["rule"], {"x": x}):
                    continue

                msg = f'{rule["error"]} `{x}` в строке {line}. {rule["msg"]}'
                error_info = {
                    "key": key,
                    "name": x,
                    "error": rule["error"],
                    "message": msg,
                }

                if line not in lines_dct:
                    lines_dct[line] = {}
                if self.name not in lines_dct[line]:
                    lines_dct[line][self.name] = []
                lines_dct[line][self.name].append(error_info)

        return lines_dct


if __name__ == "__main__":
    filename = "ast_checker_sample.py"
    lines_dct = dict()
    radon = ASTChecker(filename)
    pprint.pprint(radon.errors)

    print(60 * "-")

    lines_dct = radon.line(lines_dct)
    pprint.pprint(lines_dct)
    # save_json("data", "lines.json", lines_dct)
