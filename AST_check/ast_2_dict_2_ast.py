import ast
from behoof import load_json, save_json


def ast_to_serializable(node):
    """
    Рекурсивно преобразует AST в сериализуемую структуру с сохранением позиций
    """
    if isinstance(node, ast.AST):
        result = {"_type": type(node).__name__}
        if hasattr(node, "lineno"):
            result["lineno"] = node.lineno
        if hasattr(node, "col_offset"):
            result["col_offset"] = node.col_offset
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_serializable(value)
        return result
    elif isinstance(node, list):
        return [ast_to_serializable(item) for item in node]
    else:
        return node


def serializable_to_ast(data):
    """
    Рекурсивно преобразует сериализуемую структуру обратно в AST
    """
    if isinstance(data, dict) and "_type" in data:
        node_type = data["_type"]
        node_class = getattr(ast, node_type)
        kwargs = {}
        for field in node_class._fields:
            if field in data:
                kwargs[field] = serializable_to_ast(data[field])
        node = node_class(**kwargs)
        if "lineno" in data:
            node.lineno = data["lineno"]
        if "col_offset" in data:
            node.col_offset = data["col_offset"]
        return node
    elif isinstance(data, list):
        return [serializable_to_ast(item) for item in data]
    else:
        return data


if __name__ == "__main__":
    filepath = "ast_checker_sample.py"
    with open(filepath, "r", encoding="utf-8") as f:
        test_code = f.read()
    tree = ast.parse(test_code)
    serialized = ast_to_serializable(tree)
    save_json("data", "ast.json", serialized)

    loaded = load_json("data", "ast.json")
    restored_tree = serializable_to_ast(loaded)
    ast.fix_missing_locations(restored_tree)
    restored_code = ast.unparse(restored_tree)
    print(restored_code)
