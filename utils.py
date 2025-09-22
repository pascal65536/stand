import os
import sys
import string
import requests
import datetime
from bs4 import BeautifulSoup
from behoof import load_json, save_json


legal_chars = string.ascii_lowercase + string.ascii_uppercase + string.digits + './_-'


def check_folder(root):
    """
    Проверяет, содержит ли строка символы не-латиницы в папках проекта,
    исключение - фикстуры.
    """    
    ignore_paths = ['fixtures']
    files_lst = list()
    for r, d, files in os.walk(root):
        for ignored in ignore_paths:
            if ignored not in r:
                for filename in files:
                    if not set(filename) <= set(legal_chars):
                        files_lst.append(filename)
    return files_lst


def check_gitignore(root):
    """
    Проверяет, содержит ли проект файл .gitignore и его содержимое
    """    
    if '.gitignore' not in os.listdir(root):
        return {'status': 'error', 'message': 'File .gitignore not found'}
    gitignore_path = os.path.join(root, '.gitignore')
    with open(gitignore_path, 'r') as f:
        fitestr = f.readlines()
        print(fitestr)
    return {}


def check_requirements(root):
    """
    Проверяет, содержит ли проект файл requirements.txt и его содержимое
    """    
    if 'requirements.txt' not in os.listdir(root):
        return {'status': 'error', 'message': 'File requirements.txt not found'}
    requirements_path = os.path.join(root, 'requirements.txt')
    with open(requirements_path, 'r') as f:
        fitestr = f.readlines()
        print(fitestr)
    return {}


def pypi_search(package_name):
    url = f"https://pypi.org/simple/{package_name}/"
    response = requests.get(url, timeout=30)
    response.raise_for_status() 
    soup = BeautifulSoup(response.content, 'html.parser')
    links = soup.find_all('a', href=True)
    packages = []
    for link in links:
        package_info = {
            'filename': link.get_text(strip=True),
            'url': link['href'],
            'requires_python': link.get('data-requires-python'),
            'dist_info_metadata_sha256': link.get('data-dist-info-metadata'),
            'core_metadata_sha256': link.get('data-core-metadata'),
            'check_date': datetime.datetime.now().isoformat()
        }
        packages.append(package_info)
    return packages


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python pypi_search.py <имя_пакета>")
        sys.exit(1)    
    package_name = sys.argv[1]
    pypi_lst = pypi_search(package_name)

    package_dct = load_json('data', 'package.json')
    package_dct[package_name] = pypi_lst
    package_dct = save_json('data', 'package.json', package_dct)