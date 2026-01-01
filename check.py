a = -3
b = -2
c = -1
count = 0
while True:
    a = b
    b = c
    c = int(input())
    l = 1
    if a < 0 or b < 0:
        continue
    if c == 0:
        break
    if a < b > c:
        count += 1
O = 0
print(count)