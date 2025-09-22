import ast
import pprint


class Feature(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
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
        }

    def visit_Import(self, node):
        for alias in node.names:
            self.features["imports"].append(alias.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Имя вызываемой функции может быть как Name, так и Attribute"""
        if isinstance(node.func, ast.Name):
            self.features["calls"].append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.features["calls"].append(node.func.attr)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.features["functions"].append(node.name)
        self.generic_visit(node)

    def visit_If(self, node):
        self.features["if"].append(node.__dict__)
        self.generic_visit(node)

    def visit_For(self, node):
        self.features["for"].append(node.__dict__)
        self.generic_visit(node)

    def visit_Else(self, node):
        self.features["else"].append(node)
        self.generic_visit(node)

    def visit_While(self, node):
        self.features["while"].append(node)
        self.generic_visit(node)

    def visit_Try(self, node):
        self.features["try"].append(node)
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.features["constant"].append(node.value)
        else:
            self.features["constant"].append(node.__dict__)
        self.generic_visit(node)

    def visit_Name(self, node):
        # import ipdb; ipdb.sset_trace()
        if isinstance(node.id, str):
            self.features["name"].append(node.id)
        else:
            self.features["name"].append(node)
        self.generic_visit(node)

    # def visit_Subscript(self, node):
    #     print("-" * 80)
    #     print(node.value)
    #     print(node.value.id)
    #     print(node.slice)
    #     print(node.__dict__)
    #     self.generic_visit(node)

    def visit_Subscript(self, node):
        # Проверяем, что в обращении к словарю ключ — строка
        if isinstance(node.value, ast.Name) and node.value.id == "user_obj":
            if not isinstance(node.slice, ast.Constant):
                self.errors.append(
                    f"Ошибка: ключ user_obj должен быть строкой, строка {node.lineno}"
                )
        self.generic_visit(node)

if __name__ == "__main__":
    with open("sample.py") as f:
        code_str = f.read()
    tree = ast.parse(code_str)
    feature_obj = Feature()
    feature_obj.visit(tree)
    pprint.pprint(feature_obj.features)
