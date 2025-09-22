import os
import json
import subprocess
from flask import Flask, render_template, request, redirect, url_for
from behoof import load_json, save_json, calculate_md5


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def run_bandit(filepath):
    result = subprocess.run(['bandit', '-f', 'json', '-r', filepath],
                            capture_output=True, text=True)
    return result.stdout

def run_pylint(filepath):
    result = subprocess.run(['pylint', filepath, '--output-format=json'],
                            capture_output=True, text=True)
    return result.stdout

def run_flake8(filepath):
    result = subprocess.run(['flake8', filepath, '--format=json'], capture_output=True, text=True)
    return result.stdout


def load_report(first_key):
    '''Функция для загрузки и преобразования JSON-отчета в удобный формат'''
    filecheck_dct = load_json('data', 'filecheck.json')          
    reports = filecheck_dct[first_key]

    bandit = json.loads(reports['bandit']) if 'bandit' in reports else {}
    pylint = json.loads(reports['pylint']) if 'pylint' in reports else []
    flake8 = json.loads(reports['flake8']) if 'flake8' in reports else {}

    return {
        'bandit': bandit.get('results', []),
        'pylint': pylint,
        'flake8': flake8
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    files_dct = load_json('data', 'files.json', default={})
    report = None
    filename = None

    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.py'):

                filename = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filename)

                key = calculate_md5(filename)
                file_info = {
                    'filename': file.filename,
                    'filepath': filename,
                }
                files_dct.setdefault(key, file_info)
                save_json('data', 'files.json', files_dct)

                filecheck_dct = load_json('data', 'filecheck.json')      
                filecheck_dct.setdefault(key, dict())                
                if not filecheck_dct[key].get('bandit'):
                    bandit_report = run_bandit(filename)
                    filecheck_dct[key]['bandit'] = bandit_report
                if not filecheck_dct[key].get('pylint'):
                    pylint_report = run_pylint(filename)
                    filecheck_dct[key]['pylint'] = pylint_report  
                if not filecheck_dct[key].get('flake8'):
                    flake8_report = run_flake8(filename)
                    filecheck_dct[key]['flake8'] = flake8_report                      
                save_json('data', 'filecheck.json', filecheck_dct)

    key = request.args.get('key')
    if key and key in files_dct:
        report = load_report(key)
    else:
        report = None

    return render_template('index.html', report=report, filename=filename, files=files_dct, selected_key=key)


if __name__ == '__main__':
    app.run(debug=True)

