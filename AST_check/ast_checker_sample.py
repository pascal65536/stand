import string
import pprint
import ast
import subprocess
import json
import re


class Checker:
    def __init__(self, filepath):
        self.filepath = filepath
        self.cmd = []
        self.errors = []

    def run(self):
        if not self.cmd:
            return {}
        result = subprocess.run(self.cmd, capture_output=True, text=True)
        return self.parse(result.stdout)

    def parse(self, result):
        return json.loads(result)

    def line(self, lines_dct):
        return lines_dct
    
word_set_1 = set(input())
word_set_2 = set(input())
word_set_3 = set(input())
print(*sorted(word_set_1 & word_set_2 & word_set_3))


def col(a, b):
    def tripple(c):
        return c * 3

    c = a + b
    return tripple(c)


q = "1"
w = "2"
e = col(q, w)
