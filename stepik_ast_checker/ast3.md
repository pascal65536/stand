import ast


with open("solution.py", "r") as f:
    user_code = f.read()


class Visitor(ast.NodeVisitor):
    def __init__(self):
        self.no_problems_cell = False
        self.no_problems_checkers = False
        self.has_problems = False

    # def visit(self, node: ast.AST):
    #     print(node.__class__, node.__dict__)
    #     return super().visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        print(node.name)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        for nb in node.body:
            print(node.name)
            self.visit(nb)
        print()
            
        if node.name == "Checkers":
            self.no_problems_checkers = True
        if node.name == "Cell":
            self.no_problems_cell = True

    # def visit_FunctionDef(self, node: ast.FunctionDef):
    #     if node.name == 'fib':
    #         self.has_problems = True
    #     self.generic_visit(node)

    # def visit_If(self, node: ast.If):
    #     self.has_problems = True
    #     self.generic_visit(node)


tree = ast.parse(user_code)

visitor = Visitor()
visitor.visit(tree)

if visitor.has_problems:
    raise Exception("Оператор if нельзя использовать в коде.")
if visitor.no_problems_checkers is False:
    raise Exception("Нужно реализовать класс Checkers.")
if visitor.no_problems_cell is False:
    raise Exception("Нужно реализовать класс Cell.")

# print(user_code)

# exec(user_code)
