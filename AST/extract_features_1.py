import ast
import re
import base64
import binascii

class FeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        # Признаки (значения - счетчики или бинарные флаги)
        self.features = {
            'import_os': 0,
            'import_socket': 0,
            'import_subprocess': 0,
            'import_ctypes': 0,
            'import_urllib': 0,

            'call_eval': 0,
            'call_exec': 0,
            'call_os_system': 0,
            'call_subprocess_popen': 0,

            'use_socket_socket': 0,
            'use_http_request': 0,

            'file_read_write': 0,
            'sensitive_path_access': 0,

            'suspicious_base64_strings': 0,
            'suspicious_hex_strings': 0,
            'suspicious_urls': 0,
            'suspicious_ips': 0,

            'string_decoding_calls': 0,

            'complexity': 0  # кол-во узлов в AST как приблизительная метрика сложности
        }
        self.sensitive_paths = ['/etc/', '/var/', '/home/', 'passwd', 'shadow', 'root']

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.name
            if name == 'os':
                self.features['import_os'] = 1
            elif name == 'socket':
                self.features['import_socket'] = 1
            elif name == 'subprocess':
                self.features['import_subprocess'] = 1
            elif name == 'ctypes':
                self.features['import_ctypes'] = 1
            elif name.startswith('urllib'):
                self.features['import_urllib'] = 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        mod = node.module or ''
        if mod == 'os':
            self.features['import_os'] = 1
        elif mod == 'socket':
            self.features['import_socket'] = 1
        elif mod == 'subprocess':
            self.features['import_subprocess'] = 1
        elif mod == 'ctypes':
            self.features['import_ctypes'] = 1
        elif mod.startswith('urllib'):
            self.features['import_urllib'] = 1
        self.generic_visit(node)

    def visit_Call(self, node):
        # Опасные вызовы eval, exec
        if isinstance(node.func, ast.Name):
            if node.func.id == 'eval':
                self.features['call_eval'] += 1
            elif node.func.id == 'exec':
                self.features['call_exec'] += 1

        # Вызовы с точечной нотацией: os.system, subprocess.Popen, socket.socket и др
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            val = node.func.value
            # os.system()
            if attr == 'system' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_system'] += 1
            # subprocess.Popen()
            elif attr == 'Popen' and isinstance(val, ast.Name) and val.id == 'subprocess':
                self.features['call_subprocess_popen'] += 1
            # socket.socket()
            elif attr == 'socket' and isinstance(val, ast.Name) and val.id == 'socket':
                self.features['use_socket_socket'] += 1

            # Возможный HTTP-запрос (requests.get / urllib.request.urlopen и т.п.)
            if attr in ('get', 'post', 'urlopen'):
                # Проверка, что вызов связан с urllib или requests
                if isinstance(val, ast.Name) and val.id in ('requests', 'urllib', 'urllib2', 'urllib_request', 'urllib.request'):
                    self.features['use_http_request'] += 1
                elif isinstance(val, ast.Attribute) and getattr(val, 'attr', '') in ('request',):
                    self.features['use_http_request'] += 1

            # Раскодирование строк (base64.b64decode, binascii.unhexlify)
            if (isinstance(val, ast.Name) and val.id in ('base64', 'binascii')) or \
               (isinstance(val, ast.Attribute) and val.attr in ('base64', 'binascii')):
                if attr in ('b64decode', 'a85decode', 'unhexlify', 'hexlify'):
                    self.features['string_decoding_calls'] += 1

        self.generic_visit(node)

    def visit_With(self, node):
        # Можно отслеживать операции с файлами с помощью менеджеров контекста
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func = item.context_expr.func
                if isinstance(func, ast.Name) and func.id == 'open':
                    self.features['file_read_write'] += 1
        self.generic_visit(node)

    def visit_Call_open(self, node):
        # Отдельная функция не используется, можно обработать в visit_Call (open())
        pass

    def visit_Attribute(self, node):
        # Проверка доступа к путям (например, os.path)
        self.generic_visit(node)

    def visit_Str(self, node):
        # Обработка строковых констант — в Python 3.8 и ниже используется visit_Str,
        # в Python 3.8+ используется ast.Constant для строк.
        self.check_string(node.s)
        self.generic_visit(node)

    def visit_Constant(self, node):
        # Python 3.8+ для строк
        if isinstance(node.value, str):
            self.check_string(node.value)
        self.generic_visit(node)

    def check_string(self, s):
        # Проверка base64 (приблизительно): строка длины кратна 4 и содержит base64-символы
        b64_pattern = re.compile(r'^[A-Za-z0-9+/=]+\Z')
        hex_pattern = re.compile(r'^[0-9a-fA-F]+$')
        url_pattern = re.compile(
            r'https?://[^\s\'"<>]+', re.IGNORECASE)
        ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

        # Проверка base64
        if len(s) % 4 == 0 and b64_pattern.match(s):
            try:
                base64.b64decode(s, validate=True)
                self.features['suspicious_base64_strings'] += 1
            except binascii.Error:
                pass

        # Проверка hex
        if hex_pattern.match(s):
            self.features['suspicious_hex_strings'] += 1

        # Проверка URL
        if url_pattern.search(s):
            self.features['suspicious_urls'] += 1

        # Проверка IP
        if ip_pattern.search(s):
            self.features['suspicious_ips'] += 1

        # Проверка чувствительных путей
        for p in self.sensitive_paths:
            if p in s:
                self.features['sensitive_path_access'] += 1

    def visit_FunctionDef(self, node):
        self.features['complexity'] += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.features['complexity'] += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.features['complexity'] += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.features['complexity'] += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.features['complexity'] += 1
        self.generic_visit(node)

    def visit_Assign(self, node):
        # Проверка присвоений с вызовами open() (чтение/запись файлов)
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == 'open':
                self.features['file_read_write'] += 1
        self.generic_visit(node)

def extract_features(code_str):
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return None
    extractor = FeatureExtractor()
    extractor.visit(tree)
    return extractor.features

if __name__ == "__main__":
    with open('app.py', 'r') as f:
        example_code = f.read()
    features = extract_features(example_code)

    import pprint
    pprint.pprint(features)
