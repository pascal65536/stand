import ast
import textwrap
import re


class Visitor(ast.NodeVisitor):
    """
    AST-анализатор с Flake8-интеграцией и защитой от опасного кода
    Унифицированные кортежи: (значение, строка, тип)
    """

    DANGEROUS_NODES = {
        "exec",
        "eval",
        "__import__",
        "compile",
        "open",
        "file",
        "input",
        "raw_input",
    }

    def __init__(self):
        self.rows = []
        self.assignments = []
        self.usages = []
        self.all_vars = []
        self.errors = []
        self.context_stack = []
        self.dangerous_calls = [] 

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

    def error(self, lineno: int, col_offset: int, code: str, message: str):
        """Добавляет Flake8-ошибку"""
        self.errors.append((lineno, col_offset, f"{code} {message}", Visitor))

    def dangerous_error(self, lineno: int, col_offset: int, node_name: str):
        """Ошибка для опасных конструкций"""
        self.dangerous_calls.append((node_name, lineno, "dangerous"))
        self.error(
            lineno, col_offset, "SEC001", f"Dangerous call '{node_name}' prohibited"
        )

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

    # ========== EXEC/EVAL CHECK ==========
    def visit_Exec(self, node):
        """Блокируем exec полностью"""
        self.dangerous_error(node.lineno, node.col_offset, "exec")

    def visit_Eval(self, node):
        """Блокируем eval"""
        self.dangerous_error(node.lineno, node.col_offset, "eval")

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

    # ========== CALLS & DANGEROUS CHECKS ==========
    def visit_Call(self, node):
        name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr if isinstance(node.func, ast.Attribute) else "unknown"
        )

        if name in self.DANGEROUS_NODES:
            self.dangerous_error(node.lineno, node.col_offset, name)
        else:
            self.features["calls"].append((name, node.lineno, "call"))

        self.generic_visit(node)

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
        self.error(node.lineno, node.col_offset, "CA001", "if statement detected")
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
        self.error(node.lineno, node.col_offset, "CA003", "while loop detected")
        self.generic_visit(node)

    def visit_Try(self, node):
        ctx = self.current_context()
        self.features["try"].append(("try", node.lineno, f"in {ctx}"))
        self.error(node.lineno, node.col_offset, "CA002", "try statement detected")
        self.generic_visit(node)

    def visit_TryStar(self, node):
        ctx = self.current_context()
        self.features["try"].append(("try_star", node.lineno, f"in {ctx}"))
        self.error(node.lineno, node.col_offset, "CA002", "try* statement detected")
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
        value = node.value
        if isinstance(value, str) and len(value) > 100:
            value = f"<STRING_TOO_LONG_{len(value)}>"
            self.error(
                node.lineno,
                node.col_offset,
                "SEC002",
                "Suspicious long string constant",
            )
        else:
            value = value if isinstance(value, str) else str(value)

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
                self.features["name"].append((target.id, target.lineno, "assign"))
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.features["name"].append((node.target.id, node.lineno, "ann_assign"))
        self.generic_visit(node)


def safe_parse(code: str) -> ast.AST:
    """
    Безопасный парсинг любого кода (даже с отступами)
    """
    dedented = textwrap.dedent(code)
    return ast.parse(dedented)


if __name__ == "__main__":
    filename = "study_3.py"
    with open(filename, "r", encoding="utf-8") as f:
        user_code = f.read()

    tree = safe_parse(user_code)
    if tree is None:
        print("❌ Код не парсится!")
        exit(1)

    visitor = Visitor()
    visitor.read_rows(user_code)
    visitor.visit(tree)

    if visitor.errors:
        print("🚨 ОШИБКИ БЕЗОПАСНОСТИ".upper())
        for error in visitor.errors:
            print(f"  {error}")
        print()

    if visitor.dangerous_calls:
        print("🚨 ОПАСНЫЕ ВЫЗОВЫ".upper())
        for call, lineno, _ in visitor.dangerous_calls:
            print(f"  ({call}, {lineno}, 'dangerous')")
        print()

    if visitor.features:
        print("✅ FEATURES".upper())
        for k, variables_lst in visitor.features.items():
            if not variables_lst:
                continue
            print(f"\n{k.upper()}:")
            for value, lineno, node_type in variables_lst:
                line_content = (
                    visitor.rows[lineno - 1].strip()
                    if lineno <= len(visitor.rows)
                    else "N/A"
                )
                print(f"  ('{value}', {lineno}, '{node_type}')  # {line_content}")
            print()
