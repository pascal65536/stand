import ast
import re
import base64
import binascii

class FeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        self.features = {
            # Изначальные признаки
            'import_os': 0,
            'import_socket': 0,
            'import_subprocess': 0,
            'import_ctypes': 0,
            'import_urllib': 0,

            # Добавленные импорты
            'import_pickle': 0,
            'import_marshal': 0,
            'import_zlib': 0,
            'import_re': 0,
            'import_shutil': 0,

            # Вызовы функций
            'call_eval': 0,
            'call_exec': 0,
            'call_compile': 0,
            'call_execfile': 0,
            'call_os_system': 0,
            'call_os_chmod': 0,
            'call_os_setuid': 0,
            'call_os_remove': 0,
            'call_os_rename': 0,
            'call_subprocess_popen': 0,
            'call_ctypes_loadlibrary': 0,
            'call_ctypes_cast': 0,
            'call_shutil_rmtree': 0,
            'call_re_compile': 0,

            # Сетевые операции
            'use_socket_socket': 0,
            'use_socket_bind': 0,
            'use_socket_connect': 0,
            'use_http_request': 0,

            # Работа с файлами
            'file_read_write': 0,
            'sensitive_path_access': 0,

            # Строковые константы
            'suspicious_base64_strings': 0,
            'suspicious_hex_strings': 0,
            'suspicious_urls': 0,
            'suspicious_ips': 0,

            # Строковые декодирования (base64, hex, zlib)
            'string_decoding_calls': 0,
            'string_zlib_decompress_calls': 0,

            # Регулярные выражения
            'regex_compile_calls': 0,

            # Обфускация, сложность
            'dynamic_code_exec': 0,
            'complexity_while': 0,
            'complexity_else': 0,
            'complexity_try': 0,
            'complexity_for': 0,
            'complexity_def': 0,
            'complexity_if': 0,
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
            elif name == 'pickle':
                self.features['import_pickle'] = 1
            elif name == 'marshal':
                self.features['import_marshal'] = 1
            elif name == 'zlib':
                self.features['import_zlib'] = 1
            elif name == 're':
                self.features['import_re'] = 1
            elif name == 'shutil':
                self.features['import_shutil'] = 1
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
        elif mod == 'pickle':
            self.features['import_pickle'] = 1
        elif mod == 'marshal':
            self.features['import_marshal'] = 1
        elif mod == 'zlib':
            self.features['import_zlib'] = 1
        elif mod == 're':
            self.features['import_re'] = 1
        elif mod == 'shutil':
            self.features['import_shutil'] = 1
        self.generic_visit(node)

    def visit_Call(self, node):
        # Вызовы по имени
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == 'eval':
                self.features['call_eval'] += 1
                self.features['dynamic_code_exec'] += 1
            elif name == 'exec':
                self.features['call_exec'] += 1
                self.features['dynamic_code_exec'] += 1
            elif name == 'compile':
                self.features['call_compile'] += 1
                self.features['dynamic_code_exec'] += 1
            elif name == 'execfile':  # python2
                self.features['call_execfile'] += 1
                self.features['dynamic_code_exec'] += 1
            elif name == 'open':
                self.features['file_read_write'] += 1
            elif name == 're.compile':
                self.features['regex_compile_calls'] += 1

        # Вызовы с атрибутами
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            val = node.func.value

            # os.system, os.chmod, os.setuid, os.remove, os.rename
            if attr == 'system' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_system'] += 1
                self.features['dynamic_code_exec'] += 1
            elif attr == 'chmod' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_chmod'] += 1
            elif attr == 'setuid' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_setuid'] += 1
            elif attr == 'remove' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_remove'] += 1
            elif attr == 'rename' and isinstance(val, ast.Name) and val.id == 'os':
                self.features['call_os_rename'] += 1

            # subprocess.Popen
            elif attr == 'Popen' and isinstance(val, ast.Name) and val.id == 'subprocess':
                self.features['call_subprocess_popen'] += 1
                self.features['dynamic_code_exec'] += 1

            # ctypes.cdll.LoadLibrary, ctypes.cast
            elif attr == 'LoadLibrary' and isinstance(val, ast.Attribute) and \
                 isinstance(val.value, ast.Name) and val.value.id == 'ctypes' and val.attr == 'cdll':
                self.features['call_ctypes_loadlibrary'] += 1
                self.features['dynamic_code_exec'] += 1
            elif attr == 'cast' and isinstance(val, ast.Name) and val.id == 'ctypes':
                self.features['call_ctypes_cast'] += 1
                self.features['dynamic_code_exec'] += 1

            # shutil.rmtree
            elif attr == 'rmtree' and isinstance(val, ast.Name) and val.id == 'shutil':
                self.features['call_shutil_rmtree'] += 1

            # socket.socket, socket.bind, socket.connect
            elif attr == 'socket' and isinstance(val, ast.Name) and val.id == 'socket':
                self.features['use_socket_socket'] += 1
            elif attr == 'bind' and isinstance(val, ast.Name) and val.id == 'socket':
                self.features['use_socket_bind'] += 1
            elif attr == 'connect' and isinstance(val, ast.Name) and val.id == 'socket':
                self.features['use_socket_connect'] += 1

            # HTTP-запросы
            if attr in ('get', 'post', 'urlopen'):
                if isinstance(val, ast.Name) and val.id in ('requests', 'urllib', 'urllib2', 'urllib_request', 'urllib.request'):
                    self.features['use_http_request'] += 1
                elif isinstance(val, ast.Attribute) and getattr(val, 'attr', '') in ('request',):
                    self.features['use_http_request'] += 1

            # Декодирование строк
            if (isinstance(val, ast.Name) and val.id in ('base64', 'binascii')) or \
               (isinstance(val, ast.Attribute) and val.attr in ('base64', 'binascii')):
                if attr in ('b64decode', 'a85decode', 'unhexlify', 'hexlify'):
                    self.features['string_decoding_calls'] += 1

            if (isinstance(val, ast.Name) and val.id == 'zlib') and attr == 'decompress':
                self.features['string_zlib_decompress_calls'] += 1

            # Регулярные выражения
            if (isinstance(val, ast.Name) and val.id == 're') and attr == 'compile':
                self.features['regex_compile_calls'] += 1

        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.check_string(node.value)
        self.generic_visit(node)

    def check_string(self, s):
        b64_pattern = re.compile(r'^[A-Za-z0-9+/=]+\Z')
        hex_pattern = re.compile(r'^[0-9a-fA-F]+$')
        url_pattern = re.compile(r'https?://[^\s\'"<>]+', re.IGNORECASE)
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

        if len(s) % 4 == 0 and b64_pattern.match(s):
            try:
                base64.b64decode(s, validate=True)
                self.features['suspicious_base64_strings'] += 1
            except binascii.Error:
                pass

        if hex_pattern.match(s):
            self.features['suspicious_hex_strings'] += 1

        if url_pattern.search(s):
            self.features['suspicious_urls'] += 1

        if ip_pattern.search(s):
            self.features['suspicious_ips'] += 1

        for p in self.sensitive_paths:
            if p in s:
                self.features['sensitive_path_access'] += 1

    def visit_FunctionDef(self, node):
        self.features['complexity_def'] += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.features['complexity_if'] += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.features['complexity_for'] += 1
        self.generic_visit(node)

    def visit_Else(self, node):
        self.features['complexity_else'] += 1
        self.generic_visit(node)        

    def visit_While(self, node):
        self.features['complexity_while'] += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.features['complexity_try'] += 1
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
    with open('extract_features_1.py', 'r') as f:
        example_code = f.read()
    features = extract_features(example_code)
    import pprint
    pprint.pprint(features)
