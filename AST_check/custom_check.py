from behoof import load_json, save_json
from types import NoneType



def get_variables(ast_dict):
    res = list()
    def roll_body(body):
        if isinstance(body, list):
            for b in body:
                roll_body(b)
                res.append(b)
        elif isinstance(body, dict):
            for k, v in body.items():
                roll_body(v)
        else:
            if not isinstance(body, (str, int, NoneType, )):
                res.append(body)

    roll_body(ast_dict) 
    var_name = list()
    for r in res:
        if 'id' in r:
            var_name.append(r.get('id'))
    return var_name

def check_code_custom(ast_dict):
    """
    Пользовательская функция анализа AST.
    Принимает сериализуемый словарь AST.
    Возвращает строку с результатом проверки.
    """
    errors_lst = list()
    variables_lst = get_variables(ast_dict)
    for ch in 'O, o, l':
        if ch not in set(variables_lst):
            continue
        errors_lst.append(f'The name `{ch}` cannot be used as a variable name.')
    return errors_lst




ast_dct = load_json('data', 'ast.json')


res = check_code_custom(ast_dct)
print(*res, sep='\n')
