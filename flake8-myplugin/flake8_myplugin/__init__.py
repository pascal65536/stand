import ast
import re


class MyPlugin:
    name = "flake8-myplugin"
    version = "0.1.0"

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        visitor = MyVisitor()
        visitor.visit(self.tree)
        for line, col, msg, _ in visitor.violations:
            yield line, col, msg, type(self)


class MyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.snake_case_pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        self.allowed_single_letter = {
            "x"
        }  # set()  # или {'i', 'j', 'k'} если нужно разрешить

        print(self.snake_case_pattern)
        print(self.allowed_single_letter)

    def _check_name(self, name, lineno, col_offset):
        if not name or not isinstance(name, str):
            return

        if len(name) == 1:
            if name not in self.allowed_single_letter:
                self.violations.append(
                    (
                        lineno,
                        col_offset,
                        "MP002 single-letter variable names are not allowed",
                        self.__class__,
                    )
                )
                return

        if name.isupper() and self.snake_case_pattern.match(name.lower()):
            return

        if not self.snake_case_pattern.match(name):
            self.violations.append(
                (
                    lineno,
                    col_offset,
                    "MP003 variable name must be in snake_case (not camelCase or other)",
                    self.__class__,
                )
            )

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self._check_name(node.id, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_arg(self, node):
        self._check_name(node.arg, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_For(self, node):
        self._visit_target(node.target)
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self._visit_target(node.target)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self._visit_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self._check_name(node.target.id, node.target.lineno, node.target.col_offset)
        self.generic_visit(node)

    def visit_NamedExpr(self, node):
        if isinstance(node.target, ast.Name):
            self._check_name(node.target.id, node.target.lineno, node.target.col_offset)
        self.generic_visit(node)

    def _visit_target(self, target):
        """
        Рекурсивно обходит цели присваивания (включая распаковку: a, b = ...)
        """
        if isinstance(target, ast.Name):
            self._check_name(target.id, target.lineno, target.col_offset)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._visit_target(elt)
