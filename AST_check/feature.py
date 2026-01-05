# feature.py

import ast
import pprint


class Feature(ast.NodeVisitor):
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
        elt_str = (
            node.elt.id
            if isinstance(node.elt, ast.Name)
            else (
                str(ast.unparse(node.elt)) if hasattr(ast, "unparse") else str(node.elt)
            )
        )

        info = {
            "line": getattr(node, "lineno", "unknown"),
            "elt": elt_str,
            "generators": len(node.generators),
            "ifs_count": sum(len(gen.ifs) for gen in node.generators),
        }
        self.features["listcomp"].append(info)
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

    def read_rows(self, code_str):
        self.rows = [row for row in code_str.splitlines()]

def create_table(extractor_features):
    code_table = dict()

    for feature_name, feature_list in extractor_features.items():
        for item in feature_list:
            result = dict()
            if isinstance(item, dict):
                result.update(item)
                result.update({"name": feature_name})
            elif isinstance(item, tuple):
                result.update({"name": feature_name})
                result.update({"subname": item[0]})
                result.update({"line": item[1]})
            else:
                continue

            line_num = result.get("line", 0)
            line_name = result.get("name", "unknown")

            code_table.setdefault(line_num, dict()).setdefault(line_name, list())
            code_table[line_num][line_name].append(result)

    return code_table

if __name__ == "__main__":
    with open("AST_check/user_fld.py", "r") as f:
        code_str = f.read()
    tree = ast.parse(code_str)
    extractor = Feature()
    extractor.read_rows(code_str)
    extractor.visit(tree)

    code_table = create_table(extractor.features)
    pprint.pprint(code_table)
    
