from behoof import load_json, calculate_md5, save_json
import ast
import subprocess
import json
import re
import pprint


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


class Checker:
    def __init__(self, filepath):
        self.filepath = filepath
        self.cmd = []
        self.errors = []

    def run(self):
        if not self.cmd:
            return list()
        result = subprocess.run(self.cmd, capture_output=True, text=True)
        return self.parse(result.stdout)

    def parse(self, result):
        return json.loads(result)

    def line(self, lines_dct):
        return lines_dct


class ASTChecker(Checker):
    name = "ast"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = []
        self.errors = self.errors or self.run()        

    def run(self):
        with open(self.filepath, "r") as f:
            code_str = f.read()
        tree = ast.parse(code_str)
        extractor = Feature()
        extractor.read_rows(code_str)
        extractor.visit(tree)
        return extractor.features

    def line(self, lines_dct):
        for key, value in self.errors.items():
            for name, line_no in value:
                this = {
                    "key": key,
                    "name": name.strip(),
                }
                lines_dct.setdefault(line_no, dict()).setdefault(self.name, list())
                lines_dct[line_no][self.name].append(this)
        return lines_dct

class MyPyChecker(Checker):
    name = "mypy"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["mypy", filepath, "--output=json"]
        self.errors = self.errors or self.run()

    def parse(self, result):
        self.errors = [json.loads(line) for line in result.split("\n") if line.strip()]
        return self.errors

    def line(self, lines_dct):
        for line in self.errors:
            this = {
                "hint": line["hint"],
                "severity": line["severity"],
                "message": line["message"],
                "code": line["code"],
                "column": line["column"],
            }
            lines_dct.setdefault(line["line"], dict()).setdefault(self.name, list())
            lines_dct[line["line"]][self.name].append(this)
        return lines_dct


class Flake8Checker(Checker):
    name = "flake8"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["flake8", filepath, "--format=json"]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for key in self.errors:
            for line in self.errors[key]:
                this = {
                    "message": line["text"],
                    "code": line["code"],
                    "column": line["column_number"],
                    "physical": line["physical_line"].rstrip(),
                }
                lines_dct.setdefault(line["line_number"], dict()).setdefault(
                    self.name, list()
                )
                lines_dct[line["line_number"]][self.name].append(this)
        return lines_dct


class PylintChecker(Checker):
    name = "pylint"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["pylint", filepath, "--output-format=json"]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for line in self.errors:
            this = {
                "message": line["message"],
                "code": line["message-id"],
                "symbol": line["symbol"],
                "type": line["type"],
                "column": line["column"],
                "obj": line["obj"],
                "endColumn": line["endColumn"],
                "endLine": line["endLine"],
            }
            lines_dct.setdefault(line["line"], dict()).setdefault(self.name, list())
            lines_dct[line["line"]][self.name].append(this)
        return lines_dct


class BanditChecker(Checker):
    name = "bandit"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["bandit", "-f", "json", "-r", filepath]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for line in self.errors.get("results", list()):
            this = {
                "message": line["issue_text"],
                "code": line["test_id"],
                "column": line["col_offset"],
                "issue_confidence": line["issue_confidence"],
                "end_col_offset": line["end_col_offset"],
                "physical": line["code"],
                "issue_cwe": line["issue_cwe"],
                "issue_severity": line["issue_severity"],
                "line_range": line["line_range"],
                "more_info": line["more_info"],
                "test_name": line["test_name"],
            }
            lines_dct.setdefault(line["line_number"], dict()).setdefault(
                self.name, list()
            )
            lines_dct[line["line_number"]][self.name].append(this)
        return lines_dct


class RadonChecker(Checker):
    name = "radon"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["radon", "cc", self.filepath, "-s", "-j"]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for key in self.errors:
            for line in self.errors[key]:
                this = {
                    "type": line["type"],
                    "rank": line["rank"],
                    "column": line["col_offset"],
                    "name": line["name"],
                    "end_col_offset": line.get("end_col_offset"),
                    "classname": line.get("classname"),
                    "closures": line.get("closures"),
                    "endline": line["endline"],
                    "complexity": line["complexity"],
                }
                lines_dct.setdefault(line["lineno"], dict()).setdefault(
                    self.name, list()
                )
                lines_dct[line["lineno"]][self.name].append(this)
        return lines_dct


class VultureChecker(Checker):
    name = "vulture"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["vulture", filepath, "--min-confidence", "0"]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for line in self.errors:
            this = {
                "message": line["message"],
                "confidence": line["confidence"],
            }
            lines_dct.setdefault(line["line"], dict()).setdefault(self.name, list())
            lines_dct[line["line"]][self.name].append(this)
        return lines_dct

    def parse(self, result):
        errors = []
        for line in result.strip().split("\n"):
            if not line:
                continue
            line = line.replace("'", ":")
            line = line.replace("(", ":")
            line = line.replace(")", ":")
            _, line_no, msg, name, _, confidence, _ = line.split(":")
            errors.append(
                {
                    "line": int(line_no),
                    "message": f"{msg.strip().capitalize()}: '{name}'",
                    "confidence": confidence,
                }
            )
        return errors


class PyCodeStyleChecker(Checker):
    name = "pycodestyle"

    def __init__(self, filepath):
        super().__init__(filepath)
        self.cmd = ["pycodestyle", filepath]
        self.errors = self.errors or self.run()

    def line(self, lines_dct):
        for line in self.errors:
            this = {
                "message": line["message"],
            }
            lines_dct.setdefault(line["line"], dict()).setdefault(self.name, list())
            lines_dct[line["line"]][self.name].append(this)
        return lines_dct

    def parse(self, result):
        errors = []
        for line in result.strip().split("\n"):
            if not line:
                continue
            match = re.match(r"^(.+?):(\d+):\s*(.*?)\s*(?:\(\d+% confidence\))?$", line)
            if match:
                _, line_no, message = match.groups()
                errors.append({"line": int(line_no), "message": message.strip()})
        return errors


if __name__ == "__main__":
    filename = "code_analyser_practice_job/my_script.py"

    md5_file = calculate_md5(filename)

    lines_dct = dict()
    radon = PyCodeStyleChecker(filename)
    lines_dct = radon.line(lines_dct)

    radon = VultureChecker(filename)
    lines_dct = radon.line(lines_dct)    

    radon = RadonChecker(filename)
    lines_dct = radon.line(lines_dct)    

    radon = BanditChecker(filename)
    lines_dct = radon.line(lines_dct)    

    radon = PylintChecker(filename)
    lines_dct = radon.line(lines_dct)    
    
    radon = Flake8Checker(filename)
    lines_dct = radon.line(lines_dct)   

    radon = MyPyChecker(filename)
    lines_dct = radon.line(lines_dct)  

    radon = ASTChecker(filename)
    lines_dct = radon.line(lines_dct)  

    save_json('data', 'lines.json', lines_dct)