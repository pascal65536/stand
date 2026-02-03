EDUCATIONAL_RULES = [
    # Имена переменных
    {
        "target": "store_vars",
        "check": "name",
        "condition": "len(name) == 1 and name not in ['_', 'i', 'j', 'k']",
        "message": "Односимвольное имя переменной '{name}' (строки {lines})",
        "code": "EDU-VAR-001",
        "severity": "high",
    },
    {
        "target": "store_vars",
        "check": "name",
        "condition": "name in ['l', 'o', 'O']",
        "message": "Имя переменной '{name}' визуально похоже на цифру",
        "code": "EDU-VAR-002",
        "severity": "high",
    },
    {
        "target": "store_vars",
        "check": "name",
        "condition": "not name[0].isalpha() and name[0] != '_'",
        "message": "Имя переменной '{name}' должно начинаться с буквы или _",
        "code": "EDU-VAR-003",
        "severity": "medium",
    },
    # Импорты
    {
        "target": "imports",
        "check": "name",
        "condition": "'re' in name",
        "message": "Запрещённый модуль 're' (регулярные выражения) в учебном задании",
        "code": "EDU-IMP-001",
        "severity": "medium",
    },
    {
        "target": "imports",
        "check": "name",
        "condition": "name in ['os', 'sys', 'subprocess']",
        "message": "Системные модули запрещены в учебном задании: {name}",
        "code": "EDU-IMP-002",
        "severity": "high",
    },
    # Вызовы функций
    {
        "target": "function_calls",
        "check": "name",
        "condition": "name in ['eval', 'exec', 'compile']",
        "message": "Опасная функция '{name}' запрещена",
        "code": "EDU-CALL-001",
        "severity": "critical",
    },
    # Классы
    {
        "target": "class_names",
        "check": "name",
        "condition": "not name[0].isupper()",
        "message": "Класс '{name}' должен начинаться с заглавной буквы (PEP 8)",
        "code": "EDU-CLS-001",
        "severity": "medium",
    },
    # Структурные ограничения
    {
        "target": "genexp",
        "check": "absent",
        "condition": "True",
        "message": "Генераторные выражения запрещены в учебном задании",
        "code": "EDU-STRUCT-001",
        "severity": "high",
    },
    {
        "target": "lambda",
        "check": "absent",
        "condition": "True",
        "message": "Анонимные функции (lambda) запрещены",
        "code": "EDU-STRUCT-002",
        "severity": "medium",
    },
    # Тип 1: Проверка имён элементов коллекций (переменные, функции, классы, импорты)
    {
        "target": "store_vars",  # ← ключ словаря для анализа
        "check": "name",  # ← что проверять: "name" | "lines" | "count"
        "condition": "len(name) == 1",  # ← Python-выражение с переменной {name}
        "message": "Односимвольное имя переменной '{name}' в строках {lines}",
        "code": "R001",
        "severity": "high",
    },
    # Тип 2: Проверка содержимого импортов
    {
        "target": "imports",
        "check": "name",
        "condition": "'re' in name",
        "message": "Запрещённый модуль в импорте: {name}",
        "code": "R021",
        "severity": "medium",
    },
    # Тип 3: Проверка вызовов функций
    {
        "target": "function_calls",
        "check": "name",
        "condition": "name in ['eval', 'exec']",
        "message": "Опасная функция: {name} (строки {lines})",
        "code": "R032",
        "severity": "critical",
    },
    # Тип 4: Структурная проверка классов
    {
        "target": "class_names",
        "check": "name",
        "condition": "not name[0].isupper()",
        "message": "Класс '{name}' должен начинаться с заглавной буквы",
        "code": "R011",
        "severity": "medium",
    },
    # Тип 5: Проверка количества использований (редкость/избыточность)
    {
        "target": "load_vars",
        "check": "count",  # ← проверка количества строк использования
        "condition": "count == 1",
        "message": "Переменная '{name}' используется только один раз (строка {lines})",
        "code": "R050",
        "severity": "low",
    },
    # Тип 6: Проверка отсутствия ключа (генераторные выражения)
    {
        "target": "genexp",  # ← ключ, которого не должно быть
        "check": "absent",  # ← "absent" = ключ отсутствует в словаре
        "condition": "True",  # ← всегда выполняется для absent-проверок
        "message": "Генераторные выражения запрещены",
        "code": "R031",
        "severity": "high",
    },
]
