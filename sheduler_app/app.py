import os
import json
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash
from behoof import load_json, save_json, calculate_md5


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)


def run_bandit(filepath):
    result = subprocess.run(['bandit', '-f', 'json', '-r', filepath],
                            capture_output=True, text=True)
    return result.stdout

def run_pylint(filepath):
    result = subprocess.run(['pylint', filepath, '--output-format=json'], capture_output=True, text=True)
    return result.stdout

def run_flake8(filepath):
    result = subprocess.run(['flake8', filepath, '--format=json'], capture_output=True, text=True)
    return result.stdout

def update_reports_for_file(key, filepath):
    filecheck_dct = load_json('data', 'filecheck.json', default={})
    filecheck_dct[key] = {
        'bandit': json.loads(run_bandit(filepath)).get('results'),
        'pylint': json.loads(run_pylint(filepath)),
        'flake8': json.loads(run_flake8(filepath)).get(filepath)
    }
    for pyl in filecheck_dct[key]['pylint']:
        pyl['message_id'] = pyl['message-id']

    save_json('data', 'filecheck.json', filecheck_dct)


def scan_python_files(root_dir):
    """Рекурсивно находит все .py файлы, игнорируя указанные директории (например, .venv, __pycache__ и т.д.)"""
    if not os.path.exists(root_dir):
        return []

    py_files = []
    exclude_dirs = {'.venv', 'venv', '__pycache__', '.git', '.idea', '.vscode', 'build', 'dist'}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Модифицируем список dirnames "на лету", чтобы os.walk не заходил в исключённые папки
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for f in filenames:
            if f.endswith('.py'):
                full_path = os.path.join(dirpath, f)
                py_files.append(full_path)

    return py_files



@app.route('/', methods=['GET', 'POST'])
def index():
    files_dct = load_json('data', 'files.json', default={})
    report = None
    selected_key = request.args.get('key')
    selected_file_info = None
    table_data = []

    if request.method == 'POST':
        project_path = request.form.get('project_path', '').strip()
        if project_path and os.path.exists(project_path) and os.path.isdir(project_path):
            save_json('data', 'files.json', {})
            save_json('data', 'filecheck.json', {})
            files_dct = {}
            all_py_files = scan_python_files(project_path)
            if not all_py_files:
                flash("В указанной директории не найдено .py файлов.", "warning")
                return redirect(url_for('index'))

            for fp in all_py_files:
                key = calculate_md5(fp)
                try:
                    display_path = os.path.relpath(fp, project_path)
                except:
                    display_path = fp
                files_dct[key] = {
                    'filename': os.path.basename(fp),
                    'filepath': fp,
                    'display_path': display_path,
                    'project_root': project_path
                }

            save_json('data', 'files.json', files_dct)

            for fp in all_py_files:
                key = calculate_md5(fp)
                update_reports_for_file(key, fp)

            flash(f"Проект '{project_path}' загружен. Найдено и проанализировано {len(all_py_files)} Python-файлов.", "success")
            return redirect(url_for('index'))
        else:
            flash("Пожалуйста, укажите корректный путь к существующей директории.", "error")

    # Загружаем отчет, если выбран файл
    if selected_key and selected_key in files_dct:
        selected_file_info = files_dct[selected_key]
        filecheck_dct = load_json('data', 'filecheck.json', default={})
        report = filecheck_dct.get(selected_key)

        if report:
            # Группировка данных по номерам строк и анализаторам
            grouped = {}  # { line_num: {analyzer: [description, ...], ...}, ... }

            for analyzer, issues in report.items():
                for issue in issues:
                    line_num = issue.get('line_number') or issue.get('line') or ''
                    grouped.setdefault(line_num, {}).setdefault(analyzer, dict())
                    grouped[line_num][analyzer] = issue
                    
                    # description = issue.get('issue_text') or issue.get('message') or ''
                    # severity = issue.get('issue_severity') or ''
                    # highlight = True if severity and severity.upper() == 'HIGH' else False
                    # full_desc = f"{description} (Уровень: {severity})"

                    # if line_num not in grouped:
                    #     grouped[line_num] = {'bandit': [], 'pylint': [], 'flake8': [], 'highlight': False}
                    # if analyzer.lower() in grouped[line_num]:
                    #     grouped[line_num][analyzer.lower()].append(full_desc)
                    # else:
                    #     grouped[line_num][analyzer.lower()] = [full_desc]

                    # if highlight:
                    #     grouped[line_num]['highlight'] = True

            # Сортируем номера строк по возрастанию (числа)
            def line_sort_key(x):
                try:
                    return int(x)
                except:
                    return float('inf')  # нечисловые строки в конец

            sorted_lines = sorted(grouped.keys(), key=line_sort_key)

            # Формируем данные для таблицы
            table_data = []
            for line in sorted_lines:
                row = {
                    'line': line,
                    'bandit': grouped[line].get('bandit'),
                    'pylint': grouped[line].get('pylint'),
                    'flake8': grouped[line].get('flake8'),
                    'highlight': grouped[line].get('highlight'),
                }
                table_data.append(row)
    else:
        table_data = []

    return render_template(
        'index.html',
        files=files_dct,
        selected_key=selected_key,
        selected_file_info=selected_file_info,
        table_data=table_data
    )


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     files_dct = load_json('data', 'files.json', default={})
#     report = None
#     selected_key = request.args.get('key')
#     selected_file_info = None

#     if request.method == 'POST':
#         project_path = request.form.get('project_path', '').strip()
#         if project_path and os.path.exists(project_path) and os.path.isdir(project_path):
#             save_json('data', 'files.json', {})
#             save_json('data', 'filecheck.json', {})
#             files_dct = {}
#             all_py_files = scan_python_files(project_path)
#             if not all_py_files:
#                 flash("В указанной директории не найдено .py файлов.", "warning")
#                 return redirect(url_for('index'))

#             for fp in all_py_files:
#                 key = calculate_md5(fp)
#                 try:
#                     display_path = os.path.relpath(fp, project_path)
#                 except:
#                     display_path = fp
#                 files_dct[key] = {
#                     'filename': os.path.basename(fp),
#                     'filepath': fp,
#                     'display_path': display_path,
#                     'project_root': project_path
#                 }

#             # Сохраняем список файлов
#             save_json('data', 'files.json', files_dct)

#             # Генерируем отчеты для всех файлов
#             for fp in all_py_files:
#                 key = calculate_md5(fp)
#                 update_reports_for_file(key, fp)

#             flash(f"Проект '{project_path}' загружен. Найдено и проанализировано {len(all_py_files)} Python-файлов.", "success")
#             return redirect(url_for('index'))
#         else:
#             flash("Пожалуйста, укажите корректный путь к существующей директории.", "error")

#     # Загружаем отчет, если выбран файл
#     if selected_key and selected_key in files_dct:
#         selected_file_info = files_dct[selected_key]
#         filecheck_dct = load_json('data', 'filecheck.json', default={})
#         report = filecheck_dct.get(selected_key)
#         print(report)

#     return render_template(
#         'index.html',
#         report=report,
#         files=files_dct,
#         selected_key=selected_key,
#         selected_file_info=selected_file_info
#     )


@app.route('/refresh/<key>')
def refresh(key):
    files_dct = load_json('data', 'files.json', default={})
    if key in files_dct:
        filepath = files_dct[key]['filepath']
        update_reports_for_file(key, filepath)
        flash(f"Отчет для '{files_dct[key]['display_path']}' обновлен.", "info")
    else:
        flash("Файл не найден.", "error")
    return redirect(url_for('index', key=key))


@app.route('/refresh-all')
def refresh_all():
    files_dct = load_json('data', 'files.json', default={})
    count = 0
    for key, info in files_dct.items():
        update_reports_for_file(key, info['filepath'])
        count += 1
    flash(f"Обновлено отчетов: {count}", "info")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
