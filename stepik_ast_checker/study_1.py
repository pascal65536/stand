class Cell:
    def __init__(self, state):
        self.state = state

    def status(self):
        return self.state


class Checkers:
    def __init__(self):
        self.board = {}
        self.setup_board()

    def setup_board(self):
        for i, row in enumerate("87654321"):
            for j, col in enumerate("ABCDEFGH"):
                if (i + j) % 2 == 0:
                    self.board[col + row] = Cell("X")
                elif row in "678":
                    self.board[col + row] = Cell("B")
                elif row in "123":
                    self.board[col + row] = Cell("W")
                else:
                    self.board[col + row] = Cell("X")

    def move(self, f, t):
        if f in self.board and t in self.board:
            self.board[t].state = self.board[f].state
            self.board[f].state = "X"

    def get_cell(self, p):
        return self.board.get(p)


checkers = Checkers()
checkers.move("C3", "D4")
checkers.move("H6", "G5")
for row in "87654321":
    for col in "ABCDEFGH":
        print(checkers.get_cell(col + row).status(), end="")
    print()
