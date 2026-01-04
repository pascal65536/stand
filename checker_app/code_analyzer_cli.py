import os
import sys
import json
import subprocess
import re
from pathlib import Path

TOOLS = {
    "1": "pylint",
    "2": "flake8",
    "3": "mypy",
    "4": "bandit",
    "5": "vulture",
    "6": "pycodestyle",  # <-- ДОБАВЛЕНО
    "0": "exit",
}


def run_command(cmd: list) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout
    except FileNotFoundError:
        print(
            f"Ошибка: команда {' '.join(cmd)} не найдена. Убедитесь, что инструмент установлен."
        )
        return ""


# --- Анализаторы ---
def analyze_pylint(filepath: str) -> str:
    return run_command(["pylint", filepath, "--output-format=json"])


def analyze_flake8(filepath: str) -> str:
    return run_command(["flake8", filepath, "--format=json"])


def analyze_mypy(filepath: str) -> str:
    return run_command(["mypy", filepath, "--output=json"])


def analyze_bandit(filepath: str) -> str:
    return run_command(["bandit", filepath, "-f", "json"])


def analyze_vulture(filepath: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "vulture_to_json.py", filepath, "temp_vulture.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and Path("temp_vulture.json").exists():
            with open("temp_vulture.json", "r", encoding="utf-8") as f:
                content = f.read()
            os.remove("temp_vulture.json")
            return content
        else:
            print("Ошибка при запуске vulture_to_json.py")
            return ""
    except Exception as e:
        print(f"Исключение при обработке vulture: {e}")
        return ""


def analyze_pycodestyle(filepath: str) -> str:
    # pycodestyle не поддерживает --format=json, поэтому парсим текст
    raw_output = run_command(["pycodestyle", filepath])
    if not raw_output.strip():
        return json.dumps({"errors": []})

    errors = []
    # Формат: filename:line:col: code message
    pattern = r"^(.+?):(\d+):(\d+):\s+([A-Z]\d{3})\s+(.+)$"
    for line in raw_output.strip().splitlines():
        match = re.match(pattern, line)
        if match:
            _, line_no, col_no, code, message = match.groups()
            errors.append(
                {
                    "line": int(line_no),
                    "column": int(col_no),
                    "code": code,
                    "message": message.strip(),
                }
            )
    return json.dumps({"errors": errors}, indent=2, ensure_ascii=False)


# --- Сохранение ---
def save_report(tool: str, output: str, filename: str):
    json_filename = f"{tool}_{Path(filename).stem}.json"
    try:
        parsed = json.loads(output)
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        print(f"Отчёт сохранён в {json_filename}")
    except json.JSONDecodeError:
        # Если всё же пришёл не JSON (маловероятно после обработки)
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(
                {"raw_output": output.strip().splitlines()},
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Отчёт (сырой вывод) сохранён в {json_filename}")


# --- Основная логика ---
def main():
    print("=== Анализатор Python-кода (CLI) ===")
    filename = input("Введите имя файла для анализа (например, my_script.py): ").strip()

    if not filename:
        print("Имя файла не указано.")
        return

    if not os.path.isfile(filename):
        print(f"Файл '{filename}' не найден.")
        return

    while True:
        print("\nВыберите инструмент анализа:")
        for key, name in TOOLS.items():
            print(f"  {key}. {name}")
        choice = input("Ваш выбор (0–6): ").strip()

        if choice == "0":
            print("Выход.")
            break

        tool_name = TOOLS.get(choice)
        if not tool_name:
            print("Неверный выбор. Попробуйте снова.")
            continue

        print(f"\nЗапуск {tool_name} для '{filename}'...")
        if tool_name == "pylint":
            output = analyze_pylint(filename)
        elif tool_name == "flake8":
            output = analyze_flake8(filename)
        elif tool_name == "mypy":
            output = analyze_mypy(filename)
        elif tool_name == "bandit":
            output = analyze_bandit(filename)
        elif tool_name == "vulture":
            output = analyze_vulture(filename)
        elif tool_name == "pycodestyle":
            output = analyze_pycodestyle(filename)
        else:
            continue

        if output.strip():
            print(f"\n--- Вывод {tool_name} (первые 500 символов) ---")
            print(output[:500].strip())
            if len(output) > 500:
                print("...")
        else:
            print(f"{tool_name} не вернул данных.")

        save_report(tool_name, output, filename)


if __name__ == "__main__":
    main()
