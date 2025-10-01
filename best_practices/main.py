import re
import os
import ast
from pathlib import Path

IGNORED_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".so", ".dll"}
IGNORED_NAMES = {".venv", "venv", "env", ".env", "__pycache__"}
EXPECTED_DIRS = {"src", "tests", "docs", "data"}
EXPECTED_FILES = {
    "README.md",
    "requirements.txt",
    "setup.py",
    "pyproject.toml",
}
CRITICAL_PATTERNS = {
    "__pycache__/",
    "*.py[cod]",
    "*$py.class",
    ".Python",
    "*.so",
    ".venv/",
    "venv/",
    "env/",
    ".env/",
    ".virtualenv/",
    "*.egg-info/",
    ".installed.cfg",
    "*.egg",
    ".vscode/",
    ".idea/",
}
SECRET_PATTERNS = {
    "API_KEY": r'api[_-]?key["\']?\s*[=:]\s*["\']?([a-zA-Z0-9]{32,})["\']?',
    "SECRET_KEY": r'secret[_-]?key["\']?\s*[=:]\s*["\']?([a-zA-Z0-9]{32,})["\']?',
    "PASSWORD": r'password["\']?\s*[=:]\s*["\']?([^\s"\']{8,})["\']?',
    "DATABASE_URL": r'database[_-]?url["\']?\s*[=:]\s*["\']?(postgres|mysql|sqlite)://[^\s"\']+["\']?',
    "AWS_KEYS": r'aws[_-]?(secret|key)["\']?\s*[=:]\s*["\']?([a-zA-Z0-9+/]{20,})["\']?',
    "PRIVATE_KEY": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
}
MAX_FUNCTION_LENGTH = 50
MAX_CYCLOMATIC_COMPLEXITY = 10
MAX_NESTING_DEPTH = 4


class UniversalChecker:
    def __init__(self, base_path):
        self.base_path = Path(base_path)

    def check_basic_structure(self):
        """Проверка наличия основных папок и файлов"""
        issues = []

        for dir_name in EXPECTED_DIRS:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                issues.append(
                    {
                        "type": "STRUCTURE_WARNING",
                        "message": f"Отсутствует рекомендуемая папка: {dir_name}",
                        "file": str(self.base_path),
                        "severity": "warning",
                        "explanation": f"Папка {dir_name} помогает организовать код. src - для исходного кода, tests - для тестов, docs - для документации.",
                    }
                )

        for file_name in EXPECTED_FILES:
            file_path = self.base_path / file_name
            if not file_path.exists():
                issues.append(
                    {
                        "type": "STRUCTURE_WARNING",
                        "message": f"Отсутствует рекомендуемый файл: {file_name}",
                        "file": str(self.base_path),
                        "severity": "info",
                        "explanation": f"Файл {file_name} важен для управления проектом. README.md описывает проект, requirements.txt задает зависимости.",
                    }
                )

        return issues

    def check_gitignore(self):
        """Проверка корректности .gitignore файла"""
        gitignore_path = Path(os.path.join(self.base_path, ".gitignore"))

        issues = []

        if not gitignore_path.exists():
            issues.append(
                {
                    "type": "GITIGNORE_MISSING",
                    "message": "Отсутствует файл .gitignore",
                    "file": str(gitignore_path),
                    "severity": "high",
                    "explanation": "Файл .gitignore необходим для исключения служебных файлов и конфиденциальных данных из репозитория.",
                }
            )
            return issues

        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                content = f.read()

            missing_patterns = []
            for pattern in CRITICAL_PATTERNS:
                if pattern in content:
                    continue
                missing_patterns.append(pattern)

            if missing_patterns:
                issues.append(
                    {
                        "type": "GITIGNORE_INCOMPLETE",
                        "message": f'В .gitignore отсутствуют важные паттерны: {", ".join(missing_patterns)}',
                        "file": str(gitignore_path),
                        "severity": "medium",
                        "explanation": "Эти паттерны исключают временные файлы Python, виртуальные окружения и служебные данные.",
                    }
                )

        except UnicodeDecodeError:
            issues.append(
                {
                    "type": "GITIGNORE_ENCODING",
                    "message": "Файл .gitignore имеет неверную кодировку",
                    "file": str(gitignore_path),
                    "severity": "medium",
                    "explanation": "Используйте UTF-8 кодировку для .gitignore",
                }
            )

        return issues

    """
    Обнаружение credentials в файлах
    Цель обучения: Научить безопасности и не коммитить секреты.
    """

    def analyze_file_content(self, content, file_path):
        """Анализирует содержимое файла на наличие credentials"""
        issues = []

        for secret_type, pattern in SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_number = content[: match.start()].count("\n") + 1
                secret_preview = (
                    match.group(0)[:50] + "..."
                    if len(match.group(0)) > 50
                    else match.group(0)
                )

                issues.append(
                    {
                        "type": "CREDENTIALS_FOUND",
                        "message": f"Обнаружены потенциальные credentials: {secret_type}",
                        "file": str(file_path),
                        "line": line_number,
                        "severity": "critical",
                        "explanation": f"В файле обнаружены данные, похожие на секретные ключи: {secret_preview}. Никогда не коммитьте секреты в git! Используйте .env файлы и добавляйте их в .gitignore.",
                        "suggestion": "Вынесите секретные данные в .env файл (добавленный в .gitignore) и используйте os.getenv() для их чтения.",
                    }
                )

        return issues

    def is_git_ignored(self, file_path):
        """Проверяет, игнорируется ли файл git'ом"""
        if file_path.suffix in IGNORED_EXTENSIONS:
            return True
        if file_path.name in IGNORED_NAMES:
            return True
        if any(part in IGNORED_NAMES for part in file_path.parts):
            return True

        return False

    def scan_for_credentials(self):
        """Сканирует проект на наличие credentials"""
        issues = []

        for file_path in self.base_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Пропускаем git-ignored файлы
            if self.is_git_ignored(file_path):
                continue

            # Пропускаем бинарные файлы
            if self.is_binary_file(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                file_issues = self.analyze_file_content(content, file_path)
                issues.extend(file_issues)

            except (UnicodeDecodeError, PermissionError, IOError):
                continue

        return issues

    def is_binary_file(self, file_path):
        """Проверяет, является ли файл бинарным"""
        try:
            with open(file_path, "tr") as check_file:
                check_file.read()
            return False
        except UnicodeDecodeError:
            return True

    """
    Testing & Documentation
    Проверка наличия тестов
    """

    def check_test_structure(self, base_path: str):
        issues = []
        test_path = Path(os.path.join(base_path, "tests"))

        if not test_path.exists():
            issues.append(
                {
                    "type": "NO_TESTS_DIRECTORY",
                    "message": "Отсутствует папка tests/",
                    "file": str(base_path),
                    "severity": "medium",
                    "explanation": "Тесты помогают предотвратить регрессии и убедиться в корректности кода.",
                    "suggestion": "Создайте папку tests/ и добавьте unit-тесты для ваших функций.",
                }
            )
            return issues

        # Проверяем наличие тестовых файлов
        test_files = list(test_path.glob("test_*.py")) + list(
            test_path.glob("*_test.py")
        )
        if not test_files:
            issues.append(
                {
                    "type": "NO_TEST_FILES",
                    "message": "В папке tests нет файлов с тестами",
                    "file": str(test_path),
                    "severity": "medium",
                    "explanation": "Тесты должны следовать соглашениям об именовании: test_*.py или *_test.py.",
                    "suggestion": "Создайте файлы с тестами, например test_calculator.py",
                }
            )

        return issues

    def check_test_coverage(self, base_path: str):
        """Проверка простейших признаков тестового покрытия"""
        src_path = Path(os.path.join(base_path, "src"))
        test_path = Path(os.path.join(base_path, "tests"))

        if not src_path.exists():
            return []
        if not test_path.exists():
            return []

        src_files = {f.stem for f in os.listdir(src_path) if f.name != "__init__.py"}
        test_files = {f.stem.replace("test_", "") for f in test_path.glob("test_*.py")}

        untested_modules = src_files - test_files
        issues = []

        for module in untested_modules:
            issues.append(
                {
                    "type": "UNTESTED_MODULE",
                    "message": f"Модуль {module} не покрыт тестами",
                    "file": str(src_path / f"{module}.py"),
                    "severity": "low",
                    "explanation": "Каждый модуль должен иметь соответствующие тесты.",
                    "suggestion": f"Создайте test_{module}.py с тестами для этого модуля.",
                }
            )

        return issues

    """
    Dependency Management
    Проверка управления зависимостями
    """

    def check_requirements_files(self, base_path: str):
        """Проверка файлов зависимостей"""
        issues = []
        path = Path(base_path)

        requirements_files = [
            ("requirements.txt", "стандартный файл зависимостей"),
            ("pyproject.toml", "современный стандарт с metadata"),
            ("setup.py", "legacy способ установки"),
        ]

        found_files = []
        for file_name, description in requirements_files:
            if (path / file_name).exists():
                found_files.append((file_name, description))

        if not found_files:
            issues.append(
                {
                    "type": "NO_DEPENDENCY_FILE",
                    "message": "Отсутствует файл с зависимостями",
                    "file": str(base_path),
                    "severity": "medium",
                    "explanation": "Файл зависимостей необходим для воспроизводимости установки.",
                    "suggestion": "Создайте requirements.txt или pyproject.toml с перечислением зависимостей.",
                }
            )

        # Проверка зафиксированных версий
        req_file = path / "requirements.txt"
        if req_file.exists():
            with open(req_file, "r") as f:
                content = f.read()

            loose_deps = [
                line.strip()
                for line in content.split("\n")
                if line.strip()
                and not line.strip().startswith("#")
                and not any(op in line for op in ["==", ">=", "<=", "~="])
            ]

            for dep in loose_deps:
                issues.append(
                    {
                        "type": "LOOSE_DEPENDENCY",
                        "message": f"Незафиксированная версия зависимости: {dep}",
                        "file": str(req_file),
                        "severity": "medium",
                        "explanation": "Незафиксированные версии могут привести к невоспроизводимым установкам.",
                        "suggestion": f"Зафиксируйте версию: {dep}==x.y.z",
                    }
                )

        return issues

    """
    Testing & Documentation
    Проверка документации
    """

    def check_module_docstring(self, node):
        issues = []
        if isinstance(node, ast.Module) and not ast.get_docstring(node):
            issues.append(
                {
                    "type": "MISSING_MODULE_DOCSTRING",
                    "message": "Отсутствует docstring для модуля",
                    "line": 1,
                    "severity": "low",
                    "explanation": "Docstring помогает понять назначение модуля.",
                    "suggestion": "Добавьте строку документации в начало файла.",
                }
            )
        return issues

    def check_function_docstrings(self, node):
        issues = []
        
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(
            node
        ):
            issues.append(
                {
                    "type": "MISSING_DOCSTRING",
                    "message": f"Отсутствует docstring для {node.name}",
                    "line": node.lineno,
                    "severity": "low",
                    "explanation": "Docstring помогает понять назначение функции/класса.",
                    "suggestion": "Добавьте строку документации с описанием параметров и возвращаемого значения.",
                }
            )
        return issues

    def check_type_hints(self, node):
        """Проверка наличия аннотаций типов"""
        issues = []
        if not isinstance(node, ast.FunctionDef):
            return issues            
        # Проверяем отсутствие аннотаций типов для параметров
        for arg in node.args.args:
            if not arg.annotation and arg.arg != "self":
                issues.append(
                    {
                        "type": "MISSING_TYPE_HINT",
                        "message": f"Параметр {arg.arg} не имеет аннотации типа",
                        "line": node.lineno,
                        "severity": "low",
                        "explanation": "Аннотации типов улучшают читаемость кода и помогают IDE.",
                        "suggestion": f"Добавьте аннотацию типа для параметра {arg.arg}",
                    }
                )

        # Проверяем возвращаемое значение
        if not node.returns:
            issues.append(
                {
                    "type": "MISSING_RETURN_TYPE",
                    "message": f"Функция {node.name} не имеет аннотации возвращаемого типа",
                    "line": node.lineno,
                    "severity": "low",
                    "explanation": "Аннотация возвращаемого типа помогает понять, что возвращает функция.",
                    "suggestion": "Добавьте -> ReturnType после объявления функции",
                }
            )

        return issues

    """
    Security Best Practices
    Расширенная проверка безопасности
    """

    def check_hardcoded_config(self, node):
        """Проверка жестко закодированных конфигураций"""
        issues = []
        if isinstance(node, ast.Assign) and 'targets' in node.__dict__ and any(
            isinstance(target, ast.Name)
            and "config" in target.id.lower()
            or "setting" in target.id.lower()
            for target in node.targets if 'id' in target.__dict__
        ):
            import pdb; pdb.set_trace()

            if self.contains_sensitive_value(node.value):
                issues.append(
                    {
                        "type": "HARDCODED_CONFIG",
                        "message": "Жестко закодированная конфигурация",
                        "line": node.lineno,
                        "severity": "medium",
                        "explanation": "Конфигурационные значения должны выноситься в отдельные файлы или переменные окружения.",
                        "suggestion": "Используйте os.getenv() или config-файлы для хранения настроек.",
                    }
                )
        return issues

    def contains_sensitive_value(self, node):
        """Проверяет, содержит ли значение чувствительные данные"""
        if isinstance(node, ast.Str):
            value = node.s.lower()
            sensitive_indicators = ["password", "secret", "key", "token", "auth"]
            return any(indicator in value for indicator in sensitive_indicators)
        return False

    """
    Error Handling & Robustness
    Проверка обработки ошибок
    """

    def check_bare_except(self, node):
        """Проверка голых except"""
        issues = []
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                {
                    "type": "BARE_EXCEPT",
                    "message": 'Обнаружен "голый" except',
                    "line": node.lineno,
                    "severity": "high",
                    "explanation": "Голый except перехватывает все исключения, включая SystemExit и KeyboardInterrupt.",
                    "suggestion": "Указывайте конкретные типы исключений: except ValueError: или except Exception:",
                }
            )
        return issues

    def check_too_broad_except(self, node):
        """Проверка слишком широких except"""
        issues = []
        if (
            isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ):
            issues.append(
                {
                    "type": "TOO_BROAD_EXCEPT",
                    "message": "Слишком широкий перехват исключений",
                    "line": node.lineno,
                    "severity": "medium",
                    "explanation": "Перехват Exception может скрыть важные ошибки.",
                    "suggestion": "Перехватывайте только конкретные типы исключений, которые ожидаете.",
                }
            )
        return issues

    """
    Performance & Optimization
    Проверка неоптимальных конструкций
    """

    def check_string_building(self, node):
        """Проверка неэффективного построения строк"""
        issues = []
        if isinstance(node, ast.For) and any(
            isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add)
            for stmt in node.body
        ):
            issues.append(
                {
                    "type": "INEFFICIENT_STRING_BUILDING",
                    "message": "Неэффективное построение строки в цикле",
                    "line": node.lineno,
                    "severity": "medium",
                    "explanation": "Конкатенация строк в цикле создает много временных объектов.",
                    "suggestion": 'Используйте list.append() и "".join() для построения строк.',
                }
            )
        return issues

    def check_unnecessary_comprehensions(self, node):
        """Проверка ненужных генераторов списков"""
        issues = []
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in ["list", "tuple", "set"]
            and node.args
            and isinstance(node.args[0], ast.GeneratorExp)
        ):
            issues.append(
                {
                    "type": "UNNECESSARY_COMPREHENSION",
                    "message": "Избыточное преобразование генератора в коллекцию",
                    "line": node.lineno,
                    "severity": "low",
                    "explanation": "Вместо list(generator) можно использовать просто [выражение].",
                    "suggestion": "Замените list(generator) на list comprehension [x for x in items]",
                }
            )
        return issues

    """
    Testing & Documentation
    Проверка документации
    """

    def check_module_docstring(self, node):
        issues = []
        if isinstance(node, ast.Module) and not ast.get_docstring(node):
            issues.append(
                {
                    "type": "MISSING_MODULE_DOCSTRING",
                    "message": "Отсутствует docstring для модуля",
                    "line": 1,
                    "severity": "low",
                    "explanation": "Docstring помогает понять назначение модуля.",
                    "suggestion": "Добавьте строку документации в начало файла.",
                }
            )
        return issues

    def check_function_docstrings(self, node):
        issues = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(
            node
        ):
            issues.append(
                {
                    "type": "MISSING_DOCSTRING",
                    "message": f"Отсутствует docstring для {node.name}",
                    "line": node.lineno,
                    "severity": "low",
                    "explanation": "Docstring помогает понять назначение функции/класса.",
                    "suggestion": "Добавьте строку документации с описанием параметров и возвращаемого значения.",
                }
            )
        return issues

    def check_type_hints(self, node):
        """Проверка наличия аннотаций типов"""
        issues = []
        if not isinstance(node, ast.FunctionDef):
            return issues            
        # Проверяем отсутствие аннотаций типов для параметров
        for arg in node.args.args:
            if not arg.annotation and arg.arg != "self":
                issues.append(
                    {
                        "type": "MISSING_TYPE_HINT",
                        "message": f"Параметр {arg.arg} не имеет аннотации типа",
                        "line": node.lineno,
                        "severity": "low",
                        "explanation": "Аннотации типов улучшают читаемость кода и помогают IDE.",
                        "suggestion": f"Добавьте аннотацию типа для параметра {arg.arg}",
                    }
                )

        # Проверяем возвращаемое значение
        if not node.returns:
            issues.append(
                {
                    "type": "MISSING_RETURN_TYPE",
                    "message": f"Функция {node.name} не имеет аннотации возвращаемого типа",
                    "line": node.lineno,
                    "severity": "low",
                    "explanation": "Аннотация возвращаемого типа помогает понять, что возвращает функция.",
                    "suggestion": "Добавьте -> ReturnType после объявления функции",
                }
            )

        return issues

    """
    Code Quality & Maintainability
    Проверка магических чисел
    """

    def check_magic_numbers(self, node):
        issues = []
        if not isinstance(node, ast.Compare):
            return issues
        for op in node.ops:
            if isinstance(
                op, (ast.Eq, ast.NotEq, ast.Lt, ast.Gt)
            ) and self.is_magic_number(node.comparators[0]):
                issues.append(
                    {
                        "type": "MAGIC_NUMBER",
                        "message": 'Обнаружено "магическое число" в условии',
                        "line": node.lineno,
                        "severity": "low",
                        "explanation": "Магические числа затрудняют понимание кода.",
                        "suggestion": "Вынесите число в именованную константу с понятным названием.",
                    }
                )
        return issues

    def is_magic_number(self, node):
        return isinstance(node, ast.Constant) and not (
            node.n in [0, 1, -1] or (isinstance(node.n, float) and node.n in [0.0, 1.0])
        )

    """
    Code Quality & Maintainability
    Проверка сложности кода
    """

    def check_function_length(self, node):
        issues = []
        if not isinstance(node, ast.FunctionDef):
            return issues
        lines = node.end_lineno - node.lineno if node.end_lineno else 0
        if lines > MAX_FUNCTION_LENGTH:
            issues.append(
                {
                    "type": "FUNCTION_TOO_LONG",
                    "message": f"Функция {node.name} слишком длинная ({lines} строк)",
                    "line": node.lineno,
                    "severity": "medium",
                    "explanation": "Длинные функции сложно понимать и тестировать. Разбейте функцию на более мелкие.",
                    "suggestion": "Выделите логические блоки в отдельные функции.",
                }
            )
        return issues

    def check_cyclomatic_complexity(self, node):
        """Проверка цикломатической сложности"""
        complexity = 1  # базовая сложность
        node_lineno = float("inf")
        for child in ast.walk(node):
            if hasattr(child, "lineno"):
                if node_lineno > child.lineno:
                    node_lineno = child.lineno
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            if isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        if complexity > MAX_CYCLOMATIC_COMPLEXITY:
            return [
                {
                    "type": "HIGH_COMPLEXITY",
                    "message": f"Высокая цикломатическая сложность: {complexity}",
                    "line": node_lineno,
                    "severity": "medium",
                    "explanation": "Сложные функции труднее тестировать и поддерживать.",
                    "suggestion": "Упростите логику или разбейте функцию на части.",
                }
            ]
        return []


class CustomStaticAnalyzer:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.python_files_lst = self.get_python_files()
        self.universal_checker = UniversalChecker(self.base_path)

    def get_python_files(self):
        files_lst = []
        for dirpath, _, filenames in os.walk(self.base_path):
            is_ignored = False
            for ignored_name in IGNORED_NAMES:
                if ignored_name in dirpath:
                    is_ignored = True
                    break
            if is_ignored:
                continue
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                if not full_path.endswith(".py"):
                    continue
                files_lst.append(full_path)
        return files_lst

    def analyze_project_structure(self):
        """Полный анализ структуры проекта"""
        issues = []
        issues.extend(self.universal_checker.check_basic_structure())
        issues.extend(self.universal_checker.check_gitignore())
        issues.extend(self.universal_checker.scan_for_credentials())
        return issues

    def analyze_project_best_practices(self):
        """Анализ best practices на уровне проекта"""
        issues = []
        issues.extend(self.universal_checker.check_test_structure(self.base_path))
        issues.extend(self.universal_checker.check_test_coverage(self.base_path))
        issues.extend(self.universal_checker.check_requirements_files(self.base_path))
        issues.extend(self.universal_checker.check_module_docstring(ast.parse("")))
        return issues

    def analyze_ast_tree(self, tree, file_path):
        """Анализ best practices в коде"""
        issues = []

        for node in ast.walk(tree):
            # Code quality
            issues.extend(self.universal_checker.check_function_length(node))
            issues.extend(self.universal_checker.check_cyclomatic_complexity(node))
            issues.extend(self.universal_checker.check_magic_numbers(node))

            # Documentation
            issues.extend(self.universal_checker.check_function_docstrings(node))
            issues.extend(self.universal_checker.check_type_hints(node))

            # Performance
            issues.extend(self.universal_checker.check_string_building(node))
            issues.extend(self.universal_checker.check_unnecessary_comprehensions(node))

            # Error handling
            issues.extend(self.universal_checker.check_bare_except(node))
            issues.extend(self.universal_checker.check_too_broad_except(node))

            # Security
            issues.extend(self.universal_checker.check_hardcoded_config(node))

        ret = []
        for iss in issues:
            iss["file_path"] = file_path
            ret.append(iss)
        return ret

    def analyze_code_best_practices(self):
        issues = []
        for file_path in self.python_files_lst:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
            issues.extend(self.analyze_ast_tree(tree, file_path))
        return issues


if __name__ == "__main__":
    project_path = "/home/pascal65536/git/stand"

    analyzer = CustomStaticAnalyzer(project_path)
    print(analyzer.analyze_project_structure())
    print(analyzer.analyze_project_best_practices())
    print(analyzer.analyze_code_best_practices())

"""
Образовательная ценность этих проверок:
Профессиональные привычки: Студенты учатся организовывать проекты как профессионалы
Безопасность: Понимают важность защиты секретов с самого начала
Работа с Git: Учатся правильно настраивать .gitignore для Python-проектов
Проектное мышление: Видят проект как целостную структуру, а не набор файлов


Образовательные преимущества:
Профессиональные стандарты: Студенты учатся писать код как профессионалы
Предотвращение ошибок: Раннее обнаружение антипаттернов
Качество кода: Формирование привычки к чистому и поддерживаемому коду
Безопасность: Понимание security best practices с самого начала
Тестирование: Культура тестирования и уверенности в своем коде
"""
