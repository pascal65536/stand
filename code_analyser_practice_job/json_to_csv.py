"""
Файл json_to_csv.py для обработки JSON файлов и сбора данных
в общий CSV файл.

Буквально хардкодом указаны имена JSON файлов,
которые нужно объединить. Так что будьте внимательны.
Ошибка возникнет, если какого-то файла не будет.
"""

import json
import csv
from pathlib import Path


def load_json(path):

    if not Path(path).exists():
        return []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as err:
        data = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                data.append(obj)

    if isinstance(data, list):
        return data

    if "results" in data:
        data_results = data["results"]
        if isinstance(data_results, list):
            return data_results

    for k, value_lst in data.items():
        if isinstance(value_lst, list):
            return value_lst
    return []


class Checker:
    def __init__(self, name):
        self.name = name
        self.path = f"{name}.json"
        self.array = load_json(self.path)


def transform(self):

    mapping = {
        "bandit": {
            "tool": "bandit",
            "file": lambda item: item.get("filename", "").strip("./"),
            "line": lambda item: item.get("line_number", ""),
            "column": lambda item: item.get("col_offset", ""),
            "severity": lambda item: item.get("issue_severity", "MEDIUM").lower(),
            "message_code": lambda item: item.get("test_name", ""),
            "message_text": lambda item: item.get("issue_text", ""),
        },
        "flake8": {
            "tool": "flake8",
            "file": lambda item: item.get("filename", ""),
            "line": lambda item: item.get("line_number", ""),
            "column": lambda item: item.get("column_number", ""),
            "severity": lambda item: "error",
            "message_code": lambda item: item.get("code", ""),
            "message_text": lambda item: item.get("text", ""),
        },
        "vulture": {
            "tool": "vulture",
            "file": lambda item: item.get("file", ""),
            "line": lambda item: item.get("line", ""),
            "column": lambda item: "_",
            "severity": lambda item: "info",
            "message_code": lambda item: "_",
            "message_text": lambda item: item.get("message", ""),
        },
        "pylint": {
            "tool": "pylint",
            "file": lambda item: item.get("path", ""),
            "line": lambda item: item.get("line", ""),
            "column": lambda item: item.get("column", ""),
            "severity": lambda item: item.get("type", "info").lower(),
            "message_code": lambda item: item.get("symbol", ""),
            "message_text": lambda item: item.get("message", ""),
        },
        "mypy": {
            "tool": "mypy",
            "file": lambda item: item.get("file", ""),
            "line": lambda item: item.get("line", ""),
            "column": lambda item: item.get("column", ""),
            "severity": lambda item: item.get("severity", "error").lower(),
            "message_code": lambda item: item.get("code", ""),
            "message_text": lambda item: item.get("message", ""),
        },
    }

    all_rows = []
    if self.name in mapping:
        for item in self.array:
            template = mapping[self.name]
            row = {key: func(item) for key, func in template.items()}
            all_rows.append(row)
    return all_rows


if __name__ == "__main__":
    filename = [
        "bandit",
        "flake8",
        "mypy",
        "pylint",
        "vulture",
    ]
    result = []
    for name in filename:
        res = Checker(name)
        result.extend(res.transform())

    # Сохранение в CSV
    fieldnames = [
        "tool",
        "file",
        "line",
        "column",
        "severity",
        "message_code",
        "message_text",
    ]
    with open("static_analysis_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)
