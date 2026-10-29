# Poker Bot Lab

A tiny playable two-player Texas Hold'em foundation for learning game theory and building agents later. The current release is human-versus-human hotseat play: there is no bot, trained policy, poker-site connection, or money involved. One person can operate both seats to explore the game.

## Play

Requires Python 3.11+ with Tkinter (included in the normal Windows Python installation). No third-party packages are required. From this folder:

```text
python -m pokerbot
```

On Windows, double-click `Play.cmd`. Pass the device to the indicated player and click **Reveal my cards**. Choose a legal action. Cards hide after each action. Board, stacks, pot, betting history, and showdown results are visible. Next hand rotates the dealer and retains stacks; New session resets to 100 chips each.

Terminal alternative: `python -m pokerbot --cli`. Terminal scrollback can expose old cards, so this is a learning/debug mode, not private hotseat play.

## Rules and deliberate simplifications

- Heads-up fixed-limit Hold'em, 100 chips per seat, 1/2 blinds.
- Dealer posts small blind and acts first preflop; big blind acts first postflop.
- Raise increment 2 preflop/flop and 4 turn/river; four bets maximum per street, including the preflop big blind.
- Short all-in calls are supported; unmatched contributions are refunded. No short all-in raises are offered.
- Best five of seven cards; ace-low straights, kickers, ties, and board-playing work.
- Heads-up only: no multiway side pots, rake, tournament structure, rebuy rules, straddles, or variable bet sizing.
- No-limit and additional players are future rule changes, not current capabilities.

The rules intentionally keep the first environment small. Train and evaluate agents against these documented rules, not assumptions about a commercial poker room.

## Structure and future policy interface

```text
pokerbot/engine.py       rules, hand evaluator, betting and settlement
pokerbot/__main__.py     desktop UI and terminal mode
tests/test_engine.py    independent examples and invariant checks
docs/STRATEGIES_AND_RL.md   strategy, RL design, and verification plan
```

```python
from pokerbot import Game

game = Game(seed=42)
player = game.current
observation = game.observation(player)
# Future policy selects one of observation['legal_actions'].
game.step(observation['legal_actions'][0])  # demonstration of API, not a strategy
```

`step` rejects illegal actions and advances through the next decision or settlement. `observation(player)` returns copies of public state plus that player's cards, their legal actions, and terminal net chip reward. No opponent hole cards are returned until showdown. The internal `Game` object contains privileged simulator state: pass only observations to future policies, not the object itself. The interface is not yet a Gymnasium or PettingZoo adapter.

For one-hand RL episodes, terminal reward is ending stack minus starting stack; intermediate reward is zero. Define a separate match objective if bankroll carries across episodes. Do not reward folds, aggression, or hand win percentage in place of profit.

## Verify

```text
python -m unittest discover -s tests -v
```

The suite checks hand rankings, action order, folds, split pots, short stacks, hidden observations, deterministic deals, invalid-action rejection, and chip/card invariants over seeded trajectories. A desktop smoke check is separate from engine tests.

## Next increments

1. Implement an RL adapter with explicit action masks and terminal handling.
2. Build simple evaluation baselines and a frozen-opponent tournament runner.
3. Reproduce a Kuhn/Leduc CFR reference result using OpenSpiel.
4. Train a small RL policy and compare it on fresh seeds, both seats, and held-out opponents.

See [strategy and RL notes](docs/STRATEGIES_AND_RL.md). Use the environment for offline learning or explicitly authorized bot competitions.
