"""Eight-puzzle transitions, reachability validation, and Manhattan distance."""

from searches.core import Transition

STANDARD_GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
SPIRAL_GOAL = (1, 2, 3, 8, 0, 4, 7, 6, 5)


def _parity(board: tuple[int, ...]) -> int:
    tiles = [tile for tile in board if tile]
    return sum(a > b for i, a in enumerate(tiles) for b in tiles[i + 1 :]) % 2


class PuzzleProblem:
    def __init__(self, initial: tuple[int, ...], goal: tuple[int, ...] = STANDARD_GOAL):
        for board in (initial, goal):
            if len(board) != 9 or set(board) != set(range(9)):
                raise ValueError("A puzzle board must contain each integer 0–8 exactly once")
        if _parity(initial) != _parity(goal):
            raise ValueError("Puzzle start and goal have incompatible inversion parity")
        self.initial = tuple(initial)
        self.goal = tuple(goal)
        self._positions = {tile: divmod(i, 3) for i, tile in enumerate(goal)}

    def successors(self, state: tuple[int, ...]):
        blank = state.index(0)
        row, col = divmod(blank, 3)
        # The transition diagram (slide 11) orders moves up, left, down, right.
        moves = (
            ("up", blank - 3, row > 0),
            ("left", blank - 1, col > 0),
            ("down", blank + 3, row < 2),
            ("right", blank + 1, col < 2),
        )
        for action, target, valid in moves:
            if valid:
                board = list(state)
                board[blank], board[target] = board[target], board[blank]
                yield Transition(action, tuple(board))

    def is_goal(self, state: tuple[int, ...]) -> bool:
        return state == self.goal

    def heuristic(self, state: tuple[int, ...]) -> float:
        distance = 0
        for i, tile in enumerate(state):
            if tile:
                row, col = divmod(i, 3)
                goal_row, goal_col = self._positions[tile]
                distance += abs(row - goal_row) + abs(col - goal_col)
        return float(distance)
