from behoof import load_json, save_json
from types import NoneType



roll_body_lst = list()
def roll_body(body):
    if isinstance(body, list):
        for b in body:
            roll_body(b)
            roll_body_lst.append(b)
    elif isinstance(body, dict):
        for k, v in body.items():
            roll_body(v)
    else:
        if not isinstance(body, (str, int, NoneType, )):
            roll_body_lst.append(body)


def get_variables(res=roll_body_lst):
    var_name = list()
    for r in res:
        if 'id' in r:
            var_name.append(r.get('id'))
    return set(filter(None, var_name))


def get_imports(res=roll_body_lst):
    var_name = list()
    for r in res:
        if r.get('_type') in ['Import', 'ImportFrom']:
            var_name.append(r.get('module'))
            for name in r.get('names', list()):
                var_name.append(name.get('name'))
    return set(filter(None, var_name))



def get_functions(res=roll_body_lst):
    var_name = list()
    for r in res:
        if r.get('_type') not in ['Assign']:
            continue
        if r.get('value', dict()).get('_type') not in ['Call']:
            continue        
        if r.get('value', dict()).get('func', dict()).get('_type') not in ['Attribute']:        
            continue
        if r.get('value', dict()).get('func', dict()).get('value', dict()).get('_type') not in ['Name']:        
            continue
        res = list()
        res.append(r.get('value', dict()).get('func', dict()).get('value', dict()).get('id'))
        res.append(r.get('value', dict()).get('func', dict()).get('attr'))
        var_name.append('.'.join(res))
    return set(filter(None, var_name))



def check_code_custom(res=roll_body_lst):
    """
    Пользовательская функция анализа AST.
    Принимает сериализуемый словарь AST.
    Возвращает строку с результатом проверки.
    """
    errors_lst = list()

    # imports_lst = get_imports(res)
    # for ch in ['re']:
    #     if ch not in imports_lst:
    #         continue
    #     errors_lst.append(f'You cannot use the `{ch}` module.')

    # variables_lst = get_variables(res)
    # for ch in ['O', 'o', 'l']:
    #     if ch not in variables_lst:
    #         continue
    #     errors_lst.append(f'The name `{ch}` cannot be used as a variable name.')


    functions_lst = get_functions(res)
    print(functions_lst)

    return errors_lst


if __name__ == '__main__':
    ast_dct = load_json('data', 'ast.json')
    roll_body(ast_dct)
    res = check_code_custom(roll_body_lst)
    print(*res, sep='\n')
