"""Fixed-limit heads-up Hold'em. UI and future policies use the same public API."""
from collections import Counter
from itertools import combinations
import random

RANKS = "23456789TJQKA"
CATEGORIES = ("High card", "Pair", "Two pair", "Three of a kind", "Straight",
              "Flush", "Full house", "Four of a kind", "Straight flush")


def rank_five(cards):
    values = sorted((RANKS.index(c[0]) + 2 for c in cards), reverse=True)
    counts = Counter(values)
    groups = sorted(((n, v) for v, n in counts.items()), reverse=True)
    unique = sorted(counts, reverse=True)
    straight = 5 if unique == [14, 5, 4, 3, 2] else (
        unique[0] if len(unique) == 5 and unique[0] - unique[-1] == 4 else 0)
    flush = len({c[1] for c in cards}) == 1
    if straight and flush:
        return (8, straight)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *values)
    if straight:
        return (4, straight)
    if groups[0][0] == 3:
        return (3, groups[0][1], *sorted((v for v in counts if counts[v] == 1), reverse=True))
    if [g[0] for g in groups[:2]] == [2, 2]:
        pairs = sorted((v for v in counts if counts[v] == 2), reverse=True)
        return (2, *pairs, next(v for v in counts if counts[v] == 1))
    if groups[0][0] == 2:
        return (1, groups[0][1], *sorted((v for v in counts if counts[v] == 1), reverse=True))
    return (0, *values)


def rank_hand(cards):
    if not 5 <= len(cards) <= 7 or len(set(cards)) != len(cards):
        raise ValueError("Use five to seven distinct cards")
    return max(rank_five(c) for c in combinations(cards, 5))


class Game:
    """One hand. Actions: fold, check, call, raise. Seats are 0 and 1.

    Simplification: no short all-in raises; short calls and unmatched refunds work.
    Raises are fixed at 2 chips preflop/flop, 4 turn/river, cap four bets/street.
    Internal deck/hole state is privileged: policies must receive observation().
    """

    def __init__(self, stacks=(100, 100), dealer=0, seed=None):
        if len(stacks) != 2 or any(type(s) is not int or s <= 0 for s in stacks):
            raise ValueError("Two positive integer stacks required")
        if dealer not in (0, 1):
            raise ValueError("Dealer must be 0 or 1")
        self.starting = list(stacks)
        self.stacks = list(stacks)
        self.dealer = dealer
        self.deck = [r + s for r in RANKS for s in "cdhs"]
        random.Random(seed).shuffle(self.deck)
        self.hole = [[], []]
        for _ in range(2):
            for p in (1 - dealer, dealer):
                self.hole[p].append(self.deck.pop())
        self.board, self.history = [], []
        self.burned = []
        self.contributions, self.street_bets = [0, 0], [0, 0]
        self.street, self.pot, self.bet_count = 0, 0, 1
        self.done, self.showdown, self.result = False, False, ""
        self._pay(dealer, min(1, self.stacks[dealer]))
        self._pay(1 - dealer, min(2, self.stacks[1 - dealer]))
        self.history.append(f"P{dealer + 1} posts small blind; P{2 - dealer} posts big blind.")
        self.pending = {p for p in (0, 1) if self.stacks[p]}
        self.current = dealer if dealer in self.pending else 1 - dealer
        if not self.pending or (0 in self.stacks and self.to_call() == 0):
            self._advance()

    def _pay(self, p, amount):
        self.stacks[p] -= amount
        self.street_bets[p] += amount
        self.contributions[p] += amount
        self.pot += amount

    def to_call(self):
        return max(self.street_bets) - self.street_bets[self.current]

    def legal_actions(self):
        if self.done:
            return []
        p = self.current
        owed = self.to_call()
        actions = ["fold", "call"] if owed else ["check"]
        size = 2 if self.street < 2 else 4
        if self.bet_count < 4 and self.stacks[p] >= owed + size and self.stacks[1 - p] > 0:
            actions.append("raise")
        return actions

    def step(self, action):
        if action not in self.legal_actions():
            raise ValueError(f"Illegal action {action}; choose {self.legal_actions()}")
        p = self.current
        if action == "fold":
            winner = 1 - p
            self.history.append(f"P{p + 1} folds.")
            self.stacks[winner] += self.pot
            self.result = f"Player {winner + 1} wins {self.pot} chips by fold."
            self.pot, self.done = 0, True
            return
        if action == "raise":
            amount = self.to_call() + (2 if self.street < 2 else 4)
            self._pay(p, amount)
            self.bet_count += 1
            self.pending = {1 - p}
            self.history.append(f"P{p + 1} bets/raises to {self.street_bets[p]}.")
        else:
            amount = min(self.to_call(), self.stacks[p])
            self._pay(p, amount)
            self.pending.discard(p)
            self.history.append(f"P{p + 1} {action}s" + (f" {amount}." if amount else "."))
        if not self.pending:
            self._advance()
        else:
            self.current = 1 - p
            if 0 in self.stacks and self.to_call() == 0:
                self._advance()

    def _deal_street(self):
        self.burned.append(self.deck.pop())
        self.board.extend(self.deck.pop() for _ in range(3 if not self.board else 1))

    def _advance(self):
        if 0 in self.stacks:
            difference = abs(self.contributions[0] - self.contributions[1])
            if difference:
                p = 0 if self.contributions[0] > self.contributions[1] else 1
                self.stacks[p] += difference
                self.contributions[p] -= difference
                self.pot -= difference
                self.history.append(f"P{p + 1} receives {difference} unmatched chips back.")
            while len(self.board) < 5:
                self._deal_street()
            self._finish()
            return
        if self.street == 3:
            self._finish()
            return
        self.street += 1
        self._deal_street()
        self.street_bets = [0, 0]
        self.bet_count = 0
        self.pending = {0, 1}
        self.current = 1 - self.dealer
        self.history.append(f"{('Preflop', 'Flop', 'Turn', 'River')[self.street]}: {' '.join(self.board)}")

    def _finish(self):
        ranks = [rank_hand(self.board + h) for h in self.hole]
        winners = [p for p in (0, 1) if ranks[p] == max(ranks)]
        share, odd = divmod(self.pot, len(winners))
        for p in winners:
            self.stacks[p] += share
        if odd:
            self.stacks[1 - self.dealer] += odd
        self.result = (f"Player {winners[0] + 1} wins {self.pot} chips" if len(winners) == 1
                       else f"Split pot: {self.pot} chips") + f" — {CATEGORIES[max(ranks)[0]]}."
        self.pot, self.done, self.showdown = 0, True, True
        self.history.append(self.result)

    def observation(self, player):
        if player not in (0, 1):
            raise ValueError("Player must be 0 or 1")
        return {"player": player, "current_player": None if self.done else self.current,
                "hole_cards": list(self.hole[player]), "board": list(self.board),
                "opponent_cards": list(self.hole[1-player]) if self.showdown else [],
                "stacks": list(self.stacks), "pot": self.pot, "dealer": self.dealer,
                "street": self.street, "street_bets": list(self.street_bets),
                "to_call": self.to_call() if not self.done and player == self.current else 0,
                "legal_actions": self.legal_actions() if player == self.current else [],
                "history": list(self.history), "done": self.done,
                "reward": self.stacks[player] - self.starting[player] if self.done else 0,
                "result": self.result}
