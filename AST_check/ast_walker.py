import ast
from collections import defaultdict


class VariableUsageAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.assignments = set()
        self.usages = set()
        self.all_vars = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.assignments.add(node.id)
            self.all_vars.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.usages.add(node.id)
            self.all_vars.add(node.id)
        elif isinstance(node.ctx, ast.Del):
            # Можно отследить удаление переменной
            self.all_vars.add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        # Аргументы функции тоже считаем переменными с присваиванием
        self.assignments.add(node.arg)
        self.all_vars.add(node.arg)
        self.generic_visit(node)

    def analyze(self, code_str):
        tree = ast.parse(code_str)
        self.visit(tree)
        return {
            "all_variables": self.all_vars,
            "assigned_variables": self.assignments,
            "used_variables": self.usages,
        }


if __name__ == "__main__":
    code = """
def check_folder(root):
    files_lst = list()
    for root, dirs, files in os.walk(root):
        for ignored in ignore_paths:
            if ignored in root:
                break

        for filename in files:
            if not set(filename) <= set(legal_chars):
                files_lst.append(filename)
    return files_lst
"""
    analyzer = VariableUsageAnalyzer()
    result = analyzer.analyze(code)
    print("Все найденные переменные:", result["all_variables"])
    print("Переменные с присваиванием:", result["assigned_variables"])
    print("Переменные, которые используются:", result["used_variables"])
