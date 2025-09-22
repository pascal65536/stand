# word1 = "A grass snake is lying in the grass"
# word2 = "and a hedgehog was running nearby"
# word1 = "My dog is clever, strong and quick,"
# word2 = "It's name is Spot, my name is Nick."
word1 = "Where is the fox? It’s in the box."
word2 = "Where is the frog? It’s in the log."
# word1 = "She lives with her granny In a little town"
# word2 = "She lives with her granny And with a cat"
# word1 = input()
# word2 = input()


def match(a, b):
    if a > b:
        return True
    elif a < b:
        return False
    else:
        return None


result_lst = [
    match(word1.lower().count("a"), word2.lower().count("a")),
    match(len(word1), len(word2)),
    match(word1[::-1], word2[::-1]),
]
print([z for z in result_lst if z is not None][0])
