import sys
from utils import check_gitignore

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python check_gitignore.py <путь_к_проекту>")
        sys.exit(1)
    source_file_path = sys.argv[1]
    has_gitignore = check_gitignore(source_file_path)
    print(has_gitignore)
