"""
Файл vulture_to_json.py для приведения результата
в единый формат
"""

import subprocess
import json
import sys
import re
from pathlib import Path


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


def main():
    if len(sys.argv) != 3:
        print("Использование: python vulture_to_json.p" "<input.py> <output.json>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_file.exists():
        print(f"Файл {input_file} не найден.")
        sys.exit(1)

    result = subprocess.run(
        ["vulture", str(input_file), "--min-confidence", "0"],
        capture_output=True,
        text=True,
    )

    data = parse_vulture_text(result.stdout) if result.stdout.strip() else []
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ vulture: {len(data)} записей → {output_file}")


if __name__ == "__main__":
    main()
