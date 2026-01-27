import sys

text = sys.stdin.read()
content = text.strip()
if not content:
    print({"error": 3, "message": "The file is empty"})
    exit()
lines = content.split()
if all(line.isdigit() for line in lines):
    numbers = [int(line) for line in lines]
    print({"result": numbers, "message": "Ok"})
    exit()
    
else:
    print({"error": 2, "message": "The file contains invalid data"})
    exit()
    
