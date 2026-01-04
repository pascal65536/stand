import json
import re
import base64
from behoof import load_json
import binascii


class FeatureExtractor:
    def __init__(self):
        self.features = {
            # Изначальные признаки
            "import_os": 0,
            "import_socket": 0,
            "import_subprocess": 0,
            "import_ctypes": 0,
            "import_urllib": 0,
            # Добавленные импорты
            "import_pickle": 0,
            "import_marshal": 0,
            "import_zlib": 0,
            "import_re": 0,
            "import_shutil": 0,
            # Вызовы функций
            "call_eval": 0,
            "call_exec": 0,
            "call_compile": 0,
            "call_execfile": 0,
            "call_os_system": 0,
            "call_os_chmod": 0,
            "call_os_setuid": 0,
            "call_os_remove": 0,
            "call_os_rename": 0,
            "call_subprocess_popen": 0,
            "call_ctypes_loadlibrary": 0,
            "call_ctypes_cast": 0,
            "call_shutil_rmtree": 0,
            "call_re_compile": 0,
            # Сетевые операции
            "use_socket_socket": 0,
            "use_socket_bind": 0,
            "use_socket_connect": 0,
            "use_http_request": 0,
            # Работа с файлами
            "file_read_write": 0,
            "sensitive_path_access": 0,
            # Строковые константы
            "suspicious_base64_strings": 0,
            "suspicious_hex_strings": 0,
            "suspicious_urls": 0,
            "suspicious_ips": 0,
            # Строковые декодирования (base64, hex, zlib)
            "string_decoding_calls": 0,
            "string_zlib_decompress_calls": 0,
            # Регулярные выражения
            "regex_compile_calls": 0,
            # Обфускация, сложность
            "dynamic_code_exec": 0,
            "complexity_while": 0,
            "complexity_else": 0,
            "complexity_try": 0,
            "complexity_for": 0,
            "complexity_def": 0,
            "complexity_if": 0,
        }
        self.sensitive_paths = ["/etc/", "/var/", "/home/", "passwd", "shadow", "root"]

    def extract_features_from_json(self, json_ast):
        """Извлекает признаки из JSON AST"""
        self._visit(json_ast)
        return self.features

    def _visit(self, node):
        """Рекурсивно обходит AST в JSON формате"""
        if isinstance(node, dict):
            node_type = node.get("_type")

            # Обработка специфичных типов узлов
            if node_type == "Import":
                self._visit_Import(node)
            elif node_type == "ImportFrom":
                self._visit_ImportFrom(node)
            elif node_type == "Call":
                self._visit_Call(node)
            elif node_type == "With":
                self._visit_With(node)
            elif node_type == "Constant":
                self._visit_Constant(node)
            elif node_type == "FunctionDef":
                self._visit_FunctionDef(node)
            elif node_type == "If":
                self._visit_If(node)
            elif node_type == "For":
                self._visit_For(node)
            elif node_type == "While":
                self._visit_While(node)
            elif node_type == "Try":
                self._visit_Try(node)
            elif node_type == "Assign":
                self._visit_Assign(node)

            # Рекурсивно обходим все дочерние узлы
            for key, value in node.items():
                self._visit(value)

        elif isinstance(node, list):
            for item in node:
                self._visit(item)

    def _visit_Import(self, node):
        """Обработка импортов"""
        for alias in node.get("names", []):
            name = alias.get("name", "")
            if name == "os":
                self.features["import_os"] = 1
            elif name == "socket":
                self.features["import_socket"] = 1
            elif name == "subprocess":
                self.features["import_subprocess"] = 1
            elif name == "ctypes":
                self.features["import_ctypes"] = 1
            elif name.startswith("urllib"):
                self.features["import_urllib"] = 1
            elif name == "pickle":
                self.features["import_pickle"] = 1
            elif name == "marshal":
                self.features["import_marshal"] = 1
            elif name == "zlib":
                self.features["import_zlib"] = 1
            elif name == "re":
                self.features["import_re"] = 1
            elif name == "shutil":
                self.features["import_shutil"] = 1

    def _visit_ImportFrom(self, node):
        """Обработка импортов из модулей"""
        mod = node.get("module", "")
        if mod == "os":
            self.features["import_os"] = 1
        elif mod == "socket":
            self.features["import_socket"] = 1
        elif mod == "subprocess":
            self.features["import_subprocess"] = 1
        elif mod == "ctypes":
            self.features["import_ctypes"] = 1
        elif mod.startswith("urllib"):
            self.features["import_urllib"] = 1
        elif mod == "pickle":
            self.features["import_pickle"] = 1
        elif mod == "marshal":
            self.features["import_marshal"] = 1
        elif mod == "zlib":
            self.features["import_zlib"] = 1
        elif mod == "re":
            self.features["import_re"] = 1
        elif mod == "shutil":
            self.features["import_shutil"] = 1

    def _visit_Call(self, node):
        """Обработка вызовов функций"""
        func = node.get("func", {})

        # Вызовы по имени
        if func.get("_type") == "Name":
            name = func.get("id", "")
            if name == "eval":
                self.features["call_eval"] += 1
                self.features["dynamic_code_exec"] += 1
            elif name == "exec":
                self.features["call_exec"] += 1
                self.features["dynamic_code_exec"] += 1
            elif name == "compile":
                self.features["call_compile"] += 1
                self.features["dynamic_code_exec"] += 1
            elif name == "execfile":
                self.features["call_execfile"] += 1
                self.features["dynamic_code_exec"] += 1
            elif name == "open":
                self.features["file_read_write"] += 1
            elif name == "re.compile":
                self.features["regex_compile_calls"] += 1

        # Вызовы с атрибутами
        if func.get("_type") == "Attribute":
            attr = func.get("attr", "")
            val = func.get("value", {})

            # os.system, os.chmod, os.setuid, os.remove, os.rename
            if (
                attr == "system"
                and val.get("_type") == "Name"
                and val.get("id") == "os"
            ):
                self.features["call_os_system"] += 1
                self.features["dynamic_code_exec"] += 1
            elif (
                attr == "chmod" and val.get("_type") == "Name" and val.get("id") == "os"
            ):
                self.features["call_os_chmod"] += 1
            elif (
                attr == "setuid"
                and val.get("_type") == "Name"
                and val.get("id") == "os"
            ):
                self.features["call_os_setuid"] += 1
            elif (
                attr == "remove"
                and val.get("_type") == "Name"
                and val.get("id") == "os"
            ):
                self.features["call_os_remove"] += 1
            elif (
                attr == "rename"
                and val.get("_type") == "Name"
                and val.get("id") == "os"
            ):
                self.features["call_os_rename"] += 1

            # subprocess.Popen
            elif (
                attr == "Popen"
                and val.get("_type") == "Name"
                and val.get("id") == "subprocess"
            ):
                self.features["call_subprocess_popen"] += 1
                self.features["dynamic_code_exec"] += 1

            # ctypes.cdll.LoadLibrary, ctypes.cast
            elif (
                attr == "LoadLibrary"
                and val.get("_type") == "Attribute"
                and val.get("value", {}).get("_type") == "Name"
                and val.get("value", {}).get("id") == "ctypes"
                and val.get("attr") == "cdll"
            ):
                self.features["call_ctypes_loadlibrary"] += 1
                self.features["dynamic_code_exec"] += 1
            elif (
                attr == "cast"
                and val.get("_type") == "Name"
                and val.get("id") == "ctypes"
            ):
                self.features["call_ctypes_cast"] += 1
                self.features["dynamic_code_exec"] += 1

            # shutil.rmtree
            elif (
                attr == "rmtree"
                and val.get("_type") == "Name"
                and val.get("id") == "shutil"
            ):
                self.features["call_shutil_rmtree"] += 1

            # socket.socket, socket.bind, socket.connect
            elif (
                attr == "socket"
                and val.get("_type") == "Name"
                and val.get("id") == "socket"
            ):
                self.features["use_socket_socket"] += 1
            elif (
                attr == "bind"
                and val.get("_type") == "Name"
                and val.get("id") == "socket"
            ):
                self.features["use_socket_bind"] += 1
            elif (
                attr == "connect"
                and val.get("_type") == "Name"
                and val.get("id") == "socket"
            ):
                self.features["use_socket_connect"] += 1

            # HTTP-запросы
            if attr in ("get", "post", "urlopen"):
                if val.get("_type") == "Name" and val.get("id") in (
                    "requests",
                    "urllib",
                    "urllib2",
                    "urllib_request",
                    "urllib.request",
                ):
                    self.features["use_http_request"] += 1
                elif val.get("_type") == "Attribute" and val.get("attr") in (
                    "request",
                ):
                    self.features["use_http_request"] += 1

            # Декодирование строк
            if (
                val.get("_type") == "Name" and val.get("id") in ("base64", "binascii")
            ) or (
                val.get("_type") == "Attribute"
                and val.get("attr") in ("base64", "binascii")
            ):
                if attr in ("b64decode", "a85decode", "unhexlify", "hexlify"):
                    self.features["string_decoding_calls"] += 1

            if (
                val.get("_type") == "Name" and val.get("id") == "zlib"
            ) and attr == "decompress":
                self.features["string_zlib_decompress_calls"] += 1

            # Регулярные выражения
            if (
                val.get("_type") == "Name" and val.get("id") == "re"
            ) and attr == "compile":
                self.features["regex_compile_calls"] += 1

    def _visit_With(self, node):
        """Обработка менеджеров контекста"""
        for item in node.get("items", []):
            context_expr = item.get("context_expr", {})
            if context_expr.get("_type") == "Call":
                func = context_expr.get("func", {})
                if func.get("_type") == "Name" and func.get("id") == "open":
                    self.features["file_read_write"] += 1

    def _visit_Constant(self, node):
        """Обработка строковых констант"""
        value = node.get("value")
        if isinstance(value, str):
            self._check_string(value)

    def _visit_FunctionDef(self, node):
        """Обработка определений функций"""
        self.features["complexity_def"] += 1

    def _visit_If(self, node):
        """Обработка условных операторов"""
        self.features["complexity_if"] += 1

    def _visit_For(self, node):
        """Обработка циклов for"""
        self.features["complexity_for"] += 1

    def _visit_While(self, node):
        """Обработка циклов while"""
        self.features["complexity_while"] += 1

    def _visit_Try(self, node):
        """Обработка блоков try"""
        self.features["complexity_try"] += 1

    def _visit_Assign(self, node):
        """Обработка присваиваний"""
        value = node.get("value", {})
        if value.get("_type") == "Call":
            func = value.get("func", {})
            if func.get("_type") == "Name" and func.get("id") == "open":
                self.features["file_read_write"] += 1

    def _check_string(self, s):
        """Проверка строк на подозрительные паттерны"""
        b64_pattern = re.compile(r"^[A-Za-z0-9+/=]+\Z")
        hex_pattern = re.compile(r"^[0-9a-fA-F]+$")
        url_pattern = re.compile(r'https?://[^\s\'"<>]+', re.IGNORECASE)
        ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

        # Проверка base64
        if len(s) % 4 == 0 and b64_pattern.match(s):
            try:
                base64.b64decode(s, validate=True)
                self.features["suspicious_base64_strings"] += 1
            except binascii.Error:
                pass

        # Проверка hex
        if hex_pattern.match(s):
            self.features["suspicious_hex_strings"] += 1

        # Проверка URL
        if url_pattern.search(s):
            self.features["suspicious_urls"] += 1

        # Проверка IP
        if ip_pattern.search(s):
            self.features["suspicious_ips"] += 1

        # Проверка чувствительных путей
        for p in self.sensitive_paths:
            if p in s:
                self.features["sensitive_path_access"] += 1


if __name__ == "__main__":

    extractor = FeatureExtractor()
    json_ast = load_json("data", "ast.json")
    ret = extractor.extract_features_from_json(json_ast)

    import pprint

    pprint.pprint(ret)
