# ASCII web table

Install `python -m pip install -r requirements-web.txt`, then double-click `Web.cmd` or run `python -m uvicorn pokerbot.web:app --host 127.0.0.1 --port 8000`. Open http://127.0.0.1:8000. The original desktop launcher is still available.

Defaults: one human, one Easy bot, 20 hands, 100 chips per player, rotating 1/2 blinds. Select 1–99 hands and 1–5 bots before dealing. Disable HUMAN SEAT to watch bots; at least two seats are required. A human plus five bots seats six; bots-only allows two to five. No players can join mid-session. Click Next Hand between hands, including while spectating.

No-limit sizing: enter an opening bet or raise increment. A raise increment is added to the current street target; calling the outstanding amount is additional. The minimum full bet/raise starts at two chips and a full raise sets the next minimum. Stack-sized short all-ins are accepted but do not reopen betting for a player unless the cumulative increase since their action meets a full raise. Side pots, ties, odd chips, eliminated seats, and rotating live-seat blinds are handled.

Bots use the installed RLCard 1.2.0 `LimitholdemRuleAgentV1`. The adapter translates cards and filters illegal actions. Easy randomly calls more often and raises less; Intermediate uses the upstream rule baseline. These are untrained heuristic difficulties, not measured skill ratings or RL models. Only the acting bot's own cards and public board are passed to the policy. The standalone upstream rule class is loaded from the installed source to avoid RLCard's registry eagerly importing unrelated games and invoking pip subprocess discovery. No upstream policy code is copied into this repository.

The match ends at the hand limit or when only one solvent player remains. End by Agreement is available between hands: bots always consent at a settled boundary and a human's button click supplies their vote. In spectator mode the button requests all remaining bots' votes. Reset ends and archives the game; an interrupted hand is voided and its committed chips refunded. Completed hand scores remain intact. New Table returns to setup.

FastAPI owns state and enforces turns. Requests carry an event version to reject duplicate/stale actions. Each bot decision is one request, allowing the UI to show turns rather than freezing through a whole hand. SQLite in ignored `data/games.sqlite3` stores configuration, complete deals, timestamped events, results, and player stats after each action; refresh/resume survives server restart. Keep the local database private and trusted; local snapshot serialization uses pickle and does not accept uploads.

Logs are shown via LOGS or ACTION LOG. At game end, the results table, dealt-card history, and downloadable JSON are available. Full hidden-card exports are blocked until the match ends. Times are explicitly fixed CST (UTC−06:00) year-round, with UTC in setup metadata; this deliberately differs from daylight-saving Central time. Stats count hands entered, profitable hands, folds, ending chips, and net change. Reset/void hands are marked in history. Pending actions are not resumed automatically while the browser is closed.

This is a local app, with no accounts or multiplayer authentication. Bind to loopback; deploy behind authentication/session authorization before exposing its API publicly. Sites' Workers runtime does not host this Python backend, so no Sites deployment is claimed.

Verification: `python -m unittest discover -s tests -v` (install `httpx` for API tests). Tests cover original engine, 2–6 seat simulations, order/rotation, side pots, reset conservation, bot legality, API limits, privacy, archives, version conflicts, and end agreement.

## Public table and complete game archive

The persistent sidebar shows public setup, blinds, board cards, actions, sizes, and payouts. It never renders hidden deal cards. Bots receive their own two cards plus public board/legal actions; they never receive other players' cards or the deck. The baseline remains RLCard's limit-poker heuristic adapted to choose minimum legal raises in this no-limit environment; the profiles are not calibrated no-limit strategies. Bot turns wait 2.2 seconds and their latest actions remain on their seat and in the sidebar.

LOGS lists matches by unique game ID and start time. Opening a finished game shows configuration and final stacks, with each hand nested beneath it: all players' cards (including folds), board, public actions, and payouts. Full private histories remain unavailable until the match ends, including reset. Each SQLite row is one complete game, not one hand. Card display uses suit symbols and 10 while stored machine-readable cards retain standard T/c/d/h/s codes.

## Game numbering, time, and log controls

Each match has an opaque internal ID and a persistent sequential display title, Gamer 1, Gamer 2, etc. Clearing an individual game preserves the sequence; clearing all games resets the counter to zero so the next game is Gamer 1. LOGS has controls for individual/all deletion. Deleting the active game also removes its local resume pointer.

Timestamps use America/Chicago with daylight saving (CST/CDT); the browser displays dates and event times in the computer's current time zone. Earlier references above to fixed CST are superseded by this behavior. UTC is retained for interchange.

Automated API checks patch the database path to a temporary directory; engine simulations write no database. Tests never create games through the live production API. Only sessions started through the normal app appear in its history.

Easy now relaxes the RLCard preflop fold decision when the call is inexpensive (at most eight chips and at most roughly 12% of the remaining stack, with a two-chip floor). It overrides baseline folds 85% of the time in that inexpensive range, while retaining caution against expensive raises. Intermediate remains the upstream rule baseline. These heuristics are deliberately beginner-oriented, not solved strategy.
