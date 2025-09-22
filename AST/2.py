s1 = input()
s2 = input()

a1 = s1.lower().count("a")
a2 = s2.lower().count("a")

if a1 > a2:
    print(True)
elif a1 < a2:
    print(False)
else:
    # a1 == a2
    if len(s1) > len(s2):
        print(True)
    elif len(s1) < len(s2):
        print(False)
    else:
        # length equal
        if s1[::-1] > s2[::-1]:
            print(True)
        else:
            print(False)
