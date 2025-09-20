import ast
import json
import sys
from typing import Any, Dict, List

class ASTtoJSONEncoder(json.JSONEncoder):
    """Кастомный JSON энкодер для AST узлов"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ast.AST):
            # Преобразуем AST узел в словарь
            result = {'_type': type(obj).__name__}
            
            # Добавляем все поля узла
            for field in obj._fields:
                value = getattr(obj, field)
                if isinstance(value, list):
                    result[field] = [self.default(item) for item in value]
                else:
                    result[field] = self.default(value)
            
            # Добавляем дополнительные атрибуты (lineno, col_offset и т.д.)
            for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
                if hasattr(obj, attr):
                    result[attr] = getattr(obj, attr)
            
            return result
        elif isinstance(obj, list):
            return [self.default(item) for item in obj]
        elif obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        return super().default(obj)

def json_to_ast(json_data: Dict) -> Any:
    """Преобразует JSON данные обратно в AST узел"""
    
    if isinstance(json_data, dict):
        if '_type' in json_data:
            # Это AST узел
            node_type = json_data['_type']
            node_class = getattr(ast, node_type)
            
            # Создаем аргументы для конструктора
            kwargs = {}
            for key, value in json_data.items():
                if key != '_type' and key in node_class._fields:
                    kwargs[key] = json_to_ast(value)
            
            # Создаем экземпляр узла
            node = node_class(**kwargs)
            
            # Устанавливаем дополнительные атрибуты
            for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
                if attr in json_data:
                    setattr(node, attr, json_data[attr])
            
            return node
        else:
            # Обычный словарь
            return {key: json_to_ast(value) for key, value in json_data.items()}
    
    elif isinstance(json_data, list):
        return [json_to_ast(item) for item in json_data]
    
    else:
        return json_data

def python_to_ast_json(source_code: str, output_json_file: str) -> None:
    """Преобразует Python код в AST и сохраняет в JSON файл"""
    
    # Парсим код в AST
    tree = ast.parse(source_code)
    
    # Преобразуем AST в JSON-совместимую структуру
    ast_dict = ASTtoJSONEncoder().default(tree)
    
    # Сохраняем в файл
    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(ast_dict, f, indent=2, ensure_ascii=False)
    
    print(f"AST успешно сохранен в {output_json_file}")

def json_to_python(input_json_file: str, output_py_file: str) -> None:
    """Читает JSON с AST и преобразует обратно в Python код"""
    
    # Читаем JSON файл
    with open(input_json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Преобразуем JSON обратно в AST
    tree = json_to_ast(json_data)
    
    # Восстанавливаем недостающие location атрибуты
    ast.fix_missing_locations(tree)
    
    # Преобразуем AST обратно в код
    python_code = ast.unparse(tree)
    
    # Сохраняем Python код
    with open(output_py_file, 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    print(f"Python код успешно восстановлен в {output_py_file}")

def main():
    if len(sys.argv) != 4:
        print("Использование: python ast_json_converter.py <input.py> <output.json> <restored.py>")
        print("Пример: python ast_json_converter.py script.py ast.json restored_script.py")
        sys.exit(1)
    
    input_py_file = sys.argv[1]
    output_json_file = sys.argv[2]
    output_py_file = sys.argv[3]
    
    try:
        # Читаем исходный Python файл
        with open(input_py_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Преобразуем в AST и сохраняем в JSON
        python_to_ast_json(source_code, output_json_file)
        
        # Восстанавливаем из JSON обратно в Python
        json_to_python(output_json_file, output_py_file)
        
        print("Преобразование завершено успешно!")
        
        # Сравниваем исходный и восстановленный код
        with open(input_py_file, 'r', encoding='utf-8') as f:
            original = f.read()
        
        with open(output_py_file, 'r', encoding='utf-8') as f:
            restored = f.read()
        
        if original == restored:
            print("✓ Исходный и восстановленный код идентичны!")
        else:
            print("⚠ Коды отличаются (возможно из-за форматирования)")
            
    except FileNotFoundError:
        print(f"Ошибка: Файл {input_py_file} не найден")
    except SyntaxError as e:
        print(f"Ошибка синтаксиса в исходном файле: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()