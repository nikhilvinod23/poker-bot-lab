# Poker strategy and RL experiment guide

## What a policy must learn

Maximize expected net chip return under the exact rules. A policy is a distribution over legal actions given an information history, not a list of instructions keyed only by hand strength. Bluffing, value betting, calling, and folding should follow from expected returns and how your range interacts with the opponent's possible hands.

Learn in order: conditional probability and Bayes updates; expected value and variance; pot odds and equity; position and stack-to-pot ratios; card removal/blockers; ranges conditioned on betting histories; mixed strategies and best responses; equilibrium and exploitability; regret minimization; then function approximation and RL.

For a call of C chips into a pot P (before calling), the simplified break-even equity is C/(P+C), assuming no future betting, no rake, and no extra payouts. Real street decisions must also account for future actions and changing ranges.

## Approaches to implement later

| Approach | What it teaches | Main limitation |
|---|---|---|
| Transparent rules plus equity estimates | Pot odds, ranges, debugging a baseline | Predictable and sensitive to modeled ranges |
| CFR / CFR+ / sampled CFR on small games | Regret, information sets, mixed strategies | Large trees need abstraction or approximation |
| Blueprint plus subgame solving | Offline strategy and decision-time refinement | Imperfect-information resolving requires correct boundary beliefs/values; naive perfect-information search leaks information |
| Opponent modeling | Exploiting measured tendencies | Few hands give noisy estimates; opponents adapt |
| NFSP / Deep CFR / self-play RL | Learning distributions and values from experience | Approximation, instability, and evaluation complexity |

The averaged policy in standard CFR has an equilibrium convergence result for two-player zero-sum games with the relevant assumptions. A generic PPO policy trained against itself does not inherit that guarantee. Multiplayer, rake, abstractions, and approximate solvers require separate analysis. Do not infer low exploitability merely from positive self-play rewards.

## Recommended learning stack

Use Python for this environment, experiments, and analysis. Use OpenSpiel as a reference implementation for small poker games, CFR, and exploitability calculations. Use PettingZoo's turn-based AEC interface for future multiagent integration, with an action mask. PyTorch is suitable for a small policy/value network. CleanRL offers readable PPO implementations; Stable-Baselines3 offers a more packaged single-agent workflow. Both need a correct wrapper/opponent design for this game. Start with a dense network over history features; use an RNN or explicit history encoding if the observation would otherwise omit relevant history. Benchmark before moving expensive rollout/evaluation loops to C++ or Rust.

No RL dependency, adapter, baseline bot, or trained model is installed or implemented in the current game. Check framework support for your chosen Python version in an isolated virtual environment when adding ML packages; the GUI itself uses only the standard library.

## Define the environment contract before training

1. **Episode:** one hand initially. Record initial stacks and seat. Keep match-long play as a separate task.
2. **Observation:** own cards, board, dealer/position, both stacks, pot, betting commitments, street, action history. Never opponent cards, undealt deck, or future random draws. A privileged critic is an explicit research choice, never an inference input.
3. **Actions:** fold/check/call/fixed raise. Mask invalid choices consistently when sampling, computing loss, and evaluating. Do not silently convert invalid actions to valid ones.
4. **Reward:** terminal net chips, normalized in big blinds; zero otherwise. Use gamma=1 for finite-hand chip EV unless deliberately changing the objective.
5. **Transitions:** the engine advances a single acting player. A wrapper that skips opponent turns must return the correct next observation/reward to the learning player. AEC dead-agent handling and terminal rewards need explicit tests.
6. **Information history:** do not collapse distinct betting histories unless you knowingly accept that abstraction. Avoid training using simulator state unavailable at play time.
7. **Randomness:** record deal and model seeds separately. Repeatability requires code/dependency/hardware metadata too.
8. **Opponent schedule:** use simple baselines plus frozen previous policies. Keep a held-out pool for evaluation and a separate pool for tuning.

## Minimal RL training sequence

First demonstrate learning in a tiny known environment. Then hold a poker opponent fixed while verifying observations, masks, terminal rewards, value targets, losses, gradients, and entropy. Only then introduce a frozen-opponent pool and self-play. Save model weights together with observation encoding, normalization, action vocabulary, hyperparameters, and revision ID. A checkpoint without its environment contract is not a reproducible strategy.

For PPO, understand policy ratios, clipping, advantage estimation, critic targets, entropy, minibatches, and rollout length. For off-policy learning, understand replay distribution, exploration, bootstrapping, target networks, and instability as opponent policies change. Historical poker hands do not supply counterfactual returns for every unchosen action.

## Confirmation methodology

**Environment correctness:** chip conservation; unique cards; correct action order and blinds; hand evaluator examples; split-pot/odd-chip rules; all-in refunds; termination; observations that exclude hidden information. Run the intended framework's API checker once the adapter exists.

**Learning correctness:** reproduce a known toy-game result before increasing complexity. Check the model can overfit a deliberately simple diagnostic task, then generalize to fresh seeds. Verify a supposedly learned behavior disappears when its relevant input is removed. Inspect reward accounting independently of the loss implementation.

**Strategy strength:** freeze the final model and run against held-out policies with fresh deals, both seat assignments, and a fixed budget. Preserve stochastic mixed strategies at evaluation; greedy argmax can make a good poker policy exploitable. Use common/paired decks and swapped seats where suitable to reduce variance, but keep duplicated pairs in one statistical cluster. For larger games, report empirical adversarial tests; exact exploitability may be infeasible.

**Statistics:** report mean bb/100, number of hands, training seeds, confidence intervals, opponent-wise results, and variability across runs. Bootstrap independent hand/session or duplicate-deal clusters as appropriate; hands from the same match/policy training run are not all independent evidence. A positive point estimate with a confidence interval covering zero is inconclusive. Set the meaningful effect size and evaluation budget before looking at the final result. Avoid treating an arbitrary hand count as sufficient.

**Robustness:** vary stacks, opponent tendencies, seeds, action abstractions, and compute budgets inside the supported rule set. Compare with simpler baselines and ablations under the same training/evaluation budgets. Training reward and lower neural loss alone do not confirm profitable or equilibrium play.

**Transfer:** prediction-market and power-market agents need new reward, simulator, execution, and constraint models. Test forecasting, allocation, and execution separately. Historical optimization can overfit; use time-ordered data, archived forecast vintages, realistic costs, stress cases, and paper execution before live capital.

## Primary references

- [CFR](https://martin.zinkevich.org/publications/regretpoker.pdf)
- [DeepStack](https://poker.cs.ualberta.ca/publications/17science.pdf)
- [Pluribus](https://noambrown.github.io/papers/19-Science-Superhuman.pdf)
- [Deep CFR](https://arxiv.org/abs/1811.00164)
- [OpenSpiel](https://github.com/google-deepmind/open_spiel)
- [PettingZoo AEC](https://pettingzoo.farama.org/api/aec/)
- [CleanRL PPO](https://docs.cleanrl.dev/rl-algorithms/ppo/)
- [Stable-Baselines3 evaluation guidance](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html)
