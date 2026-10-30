# Understanding the Python game and its bots

This is a guided reading path through the code that actually runs the current game. The strategy/RL guide describes what to learn next; this document connects those ideas to the implemented program.

## 1. Separate rules, decisions, presentation, and storage

| File | Responsibility | First things to read |
|---|---|---|
| `pokerbot/engine.py` | Card ranking; original two-player desktop game | `rank_five`, `rank_hand`, `hand_description` |
| `pokerbot/table.py` | Current multiplayer no-limit rules and bot adapter | `Table`, `legal`, `action`, `settle_turn`, `finish` |
| `pokerbot/web.py` | Local FastAPI routes, validation, SQLite persistence | `Setup`, `create`, `action`, `view` |
| `pokerbot/browser_api.py` | Browser-hosted Python requests and snapshots | `dispatch`, `visible`, `request` |
| `pokerbot/static/app.js` | Browser controls, cards, public log, archive | `act`, `render`, `updateFeed` |
| `pages-runtime/` | Runs Python in a browser worker; private IndexedDB storage | `python-worker.js`, `browser-runtime.js` |
| `tests/` | Independent examples and invariants | `test_side_pots`, `test_allin_action_sequence_builds_side_pots` |

The original `Game` class in engine.py supports the earlier desktop fixed-limit game. The website uses `Table`. They share the card evaluator. Reading `Table` prevents confusing the old betting rules with the current website.

A button is an input device. It should not decide whether a raise is legal or who wins the pot. Python enforces those rules. Likewise, a bot proposes an action; it cannot award itself chips. This separation makes each piece easier to replace and check.

The public Pages site runs Python in a WebAssembly worker because Pages cannot host a Python web server. Local use runs ordinary Python behind FastAPI. Both use the same Table class. JavaScript handles the page and browser storage; it does not replace the Python settlement rules.

## 2. Values and containers

```python
chips = 100                         # int: a whole number
folded = False                      # bool: True or False
card = "Ah"                         # str: ace of hearts
board = ["2c", "3d", "7h"]          # list: ordered, changeable
seat = {"name": "YOU", "chips": 100} # dict: named keys and values
live = {0, 1, 2}                     # set: unique members
rank = (1, 14, 13, 10, 8)            # tuple: fixed sequence for comparison
```

Seat numbers are zero-based: seat 0 is the first seat. A list works for per-seat values such as chip stacks. A dictionary is useful for one record with named fields. A set is useful when asking whether a player is still in the hand; it prevents duplicate membership.

Cards use compact internal strings. `"Th"` is ten of hearts; the front end displays `10♥`. Display notation and internal data representation can differ without changing the rules.

`None` means an absent value. For example, an action may have no raise amount. It is different from a raise amount of zero.

## 3. Functions: input → calculation → result

```python
def call_cost(target, already_paid):
    return max(0, target - already_paid)

cost = call_cost(12, 5)  # 7
```

`def` defines a function. Parameters are the names for its inputs. `return` gives the result back to the caller. A pure function depends only on its inputs and does not change external state; these are especially easy to test.

`rank_five(cards)` is approximately this pattern: it counts ranks, checks suits and straights, then returns a comparison tuple. `rank_hand(cards)` tries all five-card combinations and chooses the greatest rank. Seven cards contain `C(7,5) = 21` possible five-card combinations.

Python compares tuples from left to right. A pair of aces might rank as `(1, 14, 13, 10, 8)`: category 1, pair rank 14, then kickers. A pair of kings starts `(1, 13, ...)` and loses at the second entry. A straight starts with category 4 and beats either pair at the first entry. `hand_description` turns that machine-readable result into text and records the best five cards.

`max(candidates, key=rank_five)` means choose the candidate with the greatest calculated rank. The candidates are card combinations; the key function tells Python how to compare them.

## 4. Classes: data that changes together

```python
from pokerbot.table import Table

seats = [
    {"name": "YOU", "kind": "human", "difficulty": ""},
    {"name": "BOT 1", "kind": "bot", "difficulty": "easy"},
]
table = Table(seats, limit=20, starting_chips=100)
actions = table.legal()
```

A class defines a kind of object. `table` is one instance of `Table`, holding the state of one match. `__init__` initializes that object. `self` refers to the particular instance whose method is running.

`self.board`, `self.seats`, `self.total`, and `self.current` are attributes. A method is a function attached to the object, such as `table.action(...)`. Two separate Table instances can represent independent matches with different cards and chip stacks.

Defaults such as `limit=20` let a caller omit a setting. Named arguments such as `starting_chips=250` make a call readable. `self` is supplied automatically when calling a method; you do not write `table.legal(table)`.

## 5. Trace one action through the state machine

1. The page requests the acting player's permitted view.
2. `legal()` derives allowed actions from the current state.
3. The human or bot selects an action and optional raise increment.
4. `action()` validates the request before altering the table.
5. `pay()` moves chips from the player's stack into commitments.
6. `event()` records the action, size, time, and all-in status.
7. `settle_turn()` chooses the next decision, next street, or settlement.
8. The Python response supplies a new public view; JavaScript updates the screen.

This is a state machine: the program defines which states and transitions are allowed. No active game → deal → betting → next street → showdown/fold → next hand/end. It should be impossible to deal another hand while the current one is unresolved.

Important state distinctions:

- `bets`: each player's contribution on the current street; reset after the street.
- `total`: each player's contribution over the entire hand; used for side pots.
- `target`: the current street amount a player must reach to fully call.
- `pending`: players who still owe a decision in this betting round.
- `live`: players who have not folded, including players who are all-in.
- `chips`: money remaining behind a player's committed bets.

Zero remaining chips is not the same as folding. An all-in player stays eligible for the pots they funded but does not take further betting turns.

## 6. Conditionals, loops, comprehensions, and errors

```python
if action == "fold":
    self.live.remove(player)
elif action == "call":
    self.pay(player, amount_owed)
```

`if` and `elif` select a branch. A `for` loop processes items. `while` repeats until a condition changes, which is useful for simulating a whole hand until it ends.

This comprehension:

```python
eligible = [p for p in self.live if self.total[p] >= level]
```

means the same as:

```python
eligible = []
for p in self.live:
    if self.total[p] >= level:
        eligible.append(p)
```

Learn the longer form first. Comprehensions are compact ways of building collections, not a different algorithm.

`raise ValueError(...)` rejects invalid input. `try`/`except` handles a failure at a boundary: FastAPI converts a rules error into an HTTP error, and the UI displays a message. Validation should happen before changing chip stacks so a rejected action does not partly execute.

`assert` in tests checks an expected fact. It is appropriate for test expectations; use explicit validation/errors for live user inputs, since Python can disable assertions.

## 7. Main pots, side pots, and conservation

Suppose contributions are A=20, B=50, C=80, D=80:

| Pot | Calculation | Amount | Eligible players before folds |
|---|---|---:|---|
| Main | 20 × 4 | 80 | A, B, C, D |
| Side 1 | (50−20) × 3 | 90 | B, C, D |
| Side 2 | (80−50) × 2 | 60 | C, D |

A can win only the main pot. B can win the main pot and side 1. Each pot is evaluated separately among its eligible non-folded players. Folded chips stay in the pot while folded players lose eligibility.

`pot_layers()` constructs these layers from sorted distinct contributions. `finish()` selects each layer's winner(s), splits tied pots, assigns an odd chip in seat order left of the dealer, and adds all awards to stacks. A layer funded by only one player is an uncalled return, not a contested pot.

The useful invariant is:

```text
Before settlement: sum(remaining stacks) + sum(commitments) = initial chips
After settlement:  sum(remaining stacks) = initial chips
```

This catches lost or duplicated chips. It does not alone prove the right players won, so tests also assert explicit pot amounts, eligibility, winners, ties, and refunds. The live log states only public hand types; the completed-game archive can evaluate folded cards against the board that was actually dealt. There is no invented five-card result when fewer than five total cards were available.

## 8. How today's bots are constructed

The policy base is RLCard 1.2.0's `LimitholdemRuleAgentV1`. RLCard is a toolkit that also supports RL; this particular agent is a hand-written heuristic. It has no trained neural network and does not update itself from your results.

`bot_action()` gathers the bot's own two cards, public board, and legal actions. A small adapter converts `"Ah"` into RLCard's `"HA"` notation. The rule agent uses card-rank and suit patterns to choose fold/check/call/raise. Its rules are rough approximations, not an equity solver or an optimal no-limit strategy. If its requested action is illegal, the adapter selects a legal passive action.

**Intermediate:** uses the upstream rule choice with legality checks. It has no opponent memory, explicit range model, equity simulation, or learned strategy.

**Easy:** starts with that choice, then adds random beginner behavior. Cheap calls are defined by `owed <= min(8, max(2, int(0.12 * remaining_stack)))`. It changes a baseline fold to a call 85% of the time in that range, has a further 25% chance of a passive action when affordable, and turns a raise into a passive action 65% of the time. These conditions interact; they are not independent probabilities for the final action. The 8-chip threshold is a current heuristic and may be poorly calibrated for unusually large or small custom blinds.

Bots currently choose an action category but do not optimize sizing: a raise uses the minimum legal increment. The browser's thinking delay is presentation timing; the policy itself is fast. It should not be confused with deeper search.

The local Python code loads the standalone upstream rule class without RLCard's eager registry imports. The Pages build includes the same class under its upstream license. The AST loader is dependency plumbing, not a beginner pattern to use for ordinary bot logic. Focus first on `bot_action` and its input/output contract.

`random.Random(seed)` creates repeatable random behavior. Right now shuffling and policy randomness share one generator. For rigorous comparisons, give dealing and bot decisions separate seeds or replay fixed deals so one policy's random draws cannot change the next policy's test cards.

## 9. Connect programming to probability and game theory

- **Expected value:** probability-weighted profit across possible outcomes. Winning more hands is not necessarily winning more chips.
- **Pot odds:** calling C into a pot P requires simplified break-even equity C/(P+C), assuming no later betting or rake. Calling 10 into 30 requires 25% equity. With side pots, count only the pots you can win.
- **Equity:** expected share of the eligible pot across possible unknown cards, including ties. Estimate by enumeration or repeated sampled deals, never by reading the actual hidden cards.
- **Ranges:** probabilities over possible opponent hands. Betting actions can update those probabilities; today's bots do not maintain them.
- **Mixed strategy:** a distribution over legal actions. Randomly making mistakes is stochastic, but it is not evidence of equilibrium play.
- **Regret/CFR:** update action probabilities according to how alternatives would have performed in an information set. Start in Kuhn or Leduc poker, where you can verify results.
- **RL:** learn a policy from observations, actions, and rewards. Define observations and reward accounting before choosing a neural architecture.

For a future one-hand RL episode, use terminal ending chips minus starting chips (often normalized by the big blind). Keep intermediate reward zero initially. A policy that farms bonuses for aggression or wins tiny hands while losing large pots can optimize the wrong objective.

## 10. Interfaces, persistence, and future projects

An API is a contract for inputs and outputs. FastAPI validates a request against Pydantic models such as `Setup` and `Action`. A route such as POST `/api/games/{id}/action` accepts an action and returns a new observation. A version number prevents applying a stale action twice. The UI and bots should use a narrow interface rather than editing object internals.

JSON carries simple records between Python and JavaScript. SQLite is local durable server storage. IndexedDB stores Pages snapshots inside the visitor's browser. Pickle preserves Python objects for these trusted local snapshots; do not unpickle arbitrary files supplied by strangers. Public views and full game archives are different outputs, so a live view can omit hidden cards even though the simulator stores them.

Asynchronous JavaScript lets the interface wait for Python work without blocking the page. The worker runs the Python interpreter away from the main UI thread. This is different from training several agents in parallel; no neural training is happening in the background.

The transferable structure for markets is observation/data ingestion → model/policy → action validation → execution → accounting → audit. Replace poker rules with market-specific prices, fills, costs, constraints, and settlement. A good simulator is necessary, but it cannot establish that a forecasting or trading strategy has an edge.

## Suggested exercises

1. Trace a call from the page into `action`, then print `bets` and `total` after each street in a separate scratch simulation.
2. Write a pure function for call cost and check three cases by hand before writing assertions.
3. Compare two rank tuples and explain the exact component that breaks the tie.
4. Work through the side-pot table above with paper chips, then compare with the corresponding unit tests.
5. Create a separate bot function that accepts an observation and returns one legal action; start with always-check-else-call as a measurable baseline.
6. Record fold/call/raise frequencies on fixed deals. Change one Easy parameter and compare results over fresh deals; do not infer strength from one session.
7. Reproduce a small-game CFR result before trying to train a Hold'em neural policy.

Keep scratch simulations and automated tests separate from the live game database and the public site's browser origin.
