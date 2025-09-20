import os
import sys


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

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python check_filenames.py <путь_к_проекту>")
        sys.exit(1)    
    source_file_path = sys.argv[1]
    has_requirements = check_requirements(source_file_path)
    print(has_requirements)
