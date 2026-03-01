import os
import re
import ast, json
from behoof import load_json as lj
from json import dump as jd

def process_data(data):
    result = []
    message = "hello"
    number = 42
    flag = True
    squares = [x**2 for x in range(10) if x % 2 == 0]
    matrix = [[i*j for j in range(3)] for i in range(3)]
    unique_chars = {c for c in "hello world" if c.isalpha()}
    squares_dict = {x: x**2 for x in range(5)}
    gen_squares = (x**2 for x in range(10))
    
    for item in data:
        if item > 0:
            result.append(item)
        elif item < 0:
            pass
        else:
            print("zero")
    
    counter = 0
    while counter < 5:
        counter += 1
    
    try:
        risky_value = 1 / 0
    except ZeroDivisionError:
        print("Error caught")
    
    return result

def check_folder(root):
    files_lst = list()
    for root, dirs, files in os.walk(root):
        for ignored in ignore_paths:
            if ignored in root:
                break

        for filename in files:
            if set(filename) <= set(legal_chars):
                continue
            files_lst.append(filename)
    return files_lst

o = 0
k = 1
f = [z for z in os.listdir('.')]
squares = [x**2 for x in range(10) if x % 2 == 0]
matrix = [[i*j for j in range(3)] for i in range(3) if i*j]

