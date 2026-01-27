::python3
::header
def check_data(text):
    content = text.strip()
    if not content:
        return {"error": 3, "message": "The file is empty"}
    lines = content.split()
    if all(line.isdigit() for line in lines):
        numbers = [int(line) for line in lines]
        return {"result": numbers, "message": "Ok"}
    else:
        return {"error": 2, "message": "The file contains invalid data"}

::code
def get_data():
    return

::footer
import sys

text = sys.stdin.read()
try:
    ticket = Ticket()
except Exception as err:
    print(err)
    
ret = ticket.get_data(text)
print(ret)
