import os
import subprocess
import json
import sys
import re
from pathlib import Path
from utils_ast import code_to_json
from behoof import save_json


def parse_vulture_text(output: str):
    results = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        match = re.match(r"^(.+?):(\d+):\s*(.*?)\s*(?:\(\d+% confidence\))?$", line)
        if match:
            file, line_no, message = match.groups()
            results.append(
                {"file": file, "line": int(line_no), "message": message.strip()}
            )
    return results


def parse_pycodestyle_text(raw_output):
    errors = []
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


def run_bandit(filepath):
    result = subprocess.run(
        ["bandit", "-f", "json", "-r", filepath], capture_output=True, text=True
    )
    return result.stdout


def run_pylint(filepath):
    result = subprocess.run(
        ["pylint", filepath, "--output-format=json"], capture_output=True, text=True
    )
    return json.dumps({"errors": result.stdout}, indent=2, ensure_ascii=False)


def run_flake8(filepath):
    result = subprocess.run(
        ["flake8", filepath, "--format=json"], capture_output=True, text=True
    )
    return result.stdout


def run_mypy(filepath):
    result = subprocess.run(
        ["mypy", filepath, "--output=json"], capture_output=True, text=True
    )
    return result.stdout


def run_vulture(filepath):
    result = subprocess.run(["vulture", filepath], capture_output=True, text=True)
    return parse_vulture_text(result.stdout) if result.stdout.strip() else []


def run_pycodestyle(filepath):
    result = subprocess.run(["pycodestyle", filepath], capture_output=True, text=True)
    return parse_pycodestyle_text(result.stdout) if result.stdout.strip() else []


def run_ast(filepath):
    return code_to_json(filepath)


def load_report(first_key):
    """Функция для загрузки и преобразования JSON-отчета в удобный формат"""
    filecheck_dct = load_json("data", "filecheck.json")
    reports = filecheck_dct[first_key]

    bandit = json.loads(reports["bandit"]) if "bandit" in reports else {}
    pylint = json.loads(reports["pylint"]) if "pylint" in reports else []
    flake8 = json.loads(reports["flake8"]) if "flake8" in reports else {}

    return {"bandit": bandit.get("results", []), "pylint": pylint, "flake8": flake8}


if __name__ == "__main__":
    filename = "my_script.py"

    result = dict()
    result["bandit"] = run_bandit(filename)
    result["pylint"] = run_pylint(filename)
    result["flake8"] = run_flake8(filename)
    result["mypy"] = run_mypy(filename)
    result["vulture"] = run_vulture(filename)
    result["pycodestyle"] = run_pycodestyle(filename)
    result["ast"] = run_ast(filename)

    save_json("1", "1.json", result)
