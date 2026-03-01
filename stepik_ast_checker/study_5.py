# print(sum(map(int, input().split())))
e = [int(z) for z in input().split() if z]
if e:
    print(sum(e))
