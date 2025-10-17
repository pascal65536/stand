import sys
from utils import check_requirements

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python check_requirements.py <путь_к_проекту>")
        sys.exit(1)    
    source_file_path = sys.argv[1]
    has_requirements = check_requirements(source_file_path)
    print(has_requirements)
