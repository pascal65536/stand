import ast


class ErrorFinder(ast.NodeVisitor):
    def __init__(self):
        self.errors = []

    def visit_Subscript(self, node):
        print("-" * 80)
        print(node.value)
        print(node.value.id)
        print(node.slice)
        print(node.__dict__)
        self.generic_visit(node)

    # def visit_Subscript(self, node):
    #     # Проверяем, что в обращении к словарю ключ — строка
    #     if isinstance(node.value, ast.Name) and node.value.id == "user_obj":
    #         if not isinstance(node.slice, ast.Constant):
    #             self.errors.append(
    #                 f"Ошибка: ключ user_obj должен быть строкой, строка {node.lineno}"
    #             )
    #     self.generic_visit(node)


if __name__ == "__main__":
    code = """
import string
user_obj = {'user': 'user1', 'password': 'password1'}
user = input()
password = input()
if user != user_obj['user']:
    exit()
if password != user_obj[password]:
    exit()
"""
    tree = ast.parse(code)
    ef = ErrorFinder()
    ef.visit(tree)
    for error in ef.errors:
        print(error)
