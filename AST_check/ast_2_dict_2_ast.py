import ast
import json
import sys
from behoof import load_json, save_json


def ast_to_serializable(node):
    """Рекурсивно преобразует AST в сериализуемую структуру"""
    if isinstance(node, ast.AST):
        result = {'_type': type(node).__name__}
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_serializable(value)
        return result
    elif isinstance(node, list):
        return [ast_to_serializable(item) for item in node]
    else:
        return node

def serializable_to_ast(data):
    """Рекурсивно преобразует сериализуемую структуру обратно в AST"""
    if isinstance(data, dict) and '_type' in data:
        node_type = data['_type']
        node_class = getattr(ast, node_type)
        
        kwargs = {}
        for field in node_class._fields:
            if field in data:
                kwargs[field] = serializable_to_ast(data[field])
        
        return node_class(**kwargs)
    elif isinstance(data, list):
        return [serializable_to_ast(item) for item in data]
    else:
        return data

with open('utils.py') as f:
    source_code = f.read()

tree = ast.parse(source_code)
serialized = ast_to_serializable(tree)

save_json('data', 'ast.json', serialized)

loaded = load_json('data', 'ast.json')

restored_tree = serializable_to_ast(loaded)
ast.fix_missing_locations(restored_tree)
restored_code = ast.unparse(restored_tree)

print(restored_code)