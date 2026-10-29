import random
import unittest
from pokerbot import Game, rank_hand


class RankingTests(unittest.TestCase):
    def test_categories_and_order(self):
        hands = ['Ac Jd 9h 6s 3c', 'Ac Ad 9h 6s 3c', 'Ac Ad 9h 9s 3c',
                 'Ac Ad Ah 6s 3c', '2c 3d 4h 5s 6c', 'Ac Jc 9c 6c 3c',
                 'Ac Ad Ah 6s 6c', 'Ac Ad Ah As 3c', 'Tc Jc Qc Kc Ac']
        scores = [rank_hand(h.split()) for h in hands]
        self.assertEqual([s[0] for s in scores], list(range(9)))
        self.assertEqual(sorted(scores), scores)

    def test_wheel_and_kickers(self):
        self.assertEqual(rank_hand('Ac 2d 3h 4s 5c'.split()), (4, 5))
        self.assertGreater(rank_hand('Ac Ad Kh 8s 3c'.split()), rank_hand('Ac Ad Qh Js 3c'.split()))

    def test_seven_card_selection(self):
        self.assertEqual(rank_hand('Ac Ad Ah Kc Kd Kh 2c'.split()), (6, 14, 13))
        self.assertEqual(rank_hand('2c 3c 4c 5c 6c 7d As'.split()), (8, 6))

    def test_invalid_card_count(self):
        with self.assertRaises(ValueError):
            rank_hand(['Ac'] * 5)


class EngineTests(unittest.TestCase):
    def test_blinds_and_order(self):
        game = Game(seed=1)
        self.assertEqual((game.current, game.pot, game.stacks), (0, 3, [99, 98]))
        game.step('call')
        self.assertEqual(game.current, 1)
        self.assertEqual(game.street, 0)
        game.step('check')
        self.assertEqual((game.current, game.street, len(game.board)), (1, 1, 3))

    def test_fold(self):
        game = Game()
        game.step('fold')
        self.assertEqual(game.stacks, [99, 101])
        self.assertTrue(game.done)
        self.assertFalse(game.showdown)

    def test_raise_cap(self):
        game = Game()
        for _ in range(3):
            game.step('raise')
        self.assertNotIn('raise', game.legal_actions())

    def test_illegal_action_is_atomic(self):
        game = Game()
        before = game.observation(0)
        with self.assertRaises(ValueError):
            game.step('check')
        self.assertEqual(before, game.observation(0))

    def test_observation_and_determinism(self):
        game, other = Game(seed=10), Game(seed=10)
        self.assertEqual(game.hole, other.hole)
        self.assertEqual(game.deck, other.deck)
        obs = game.observation(0)
        self.assertEqual(obs['opponent_cards'], [])
        self.assertNotIn('deck', obs)
        obs['hole_cards'].clear()
        self.assertEqual(len(game.hole[0]), 2)
        self.assertEqual(game.observation(1)['legal_actions'], [])

    def test_split_and_odd_chip(self):
        game = Game()
        game.board = 'Tc Jc Qc Kc Ac'.split()
        game.hole = [['2d', '3d'], ['4h', '5h']]
        game.stacks, game.pot = [98, 97], 5
        game._finish()
        self.assertEqual(game.stacks, [100, 100])
        self.assertIn('Split pot', game.result)

    def test_short_call_refund(self):
        game = Game(stacks=(3, 100), seed=2)
        game.step('call')
        game.step('raise')
        game.step('call')
        self.assertTrue(game.done)
        self.assertEqual(game.contributions, [3, 3])
        self.assertEqual(sum(game.stacks), 103)
        self.assertEqual(len(game.board), 5)
        self.assertTrue(any('unmatched' in event for event in game.history))

    def test_seeded_trajectories(self):
        rng = random.Random(401)
        for seed in range(1000):
            stacks = (rng.randint(1, 100), rng.randint(1, 100))
            game = Game(stacks=stacks, dealer=seed % 2, seed=seed)
            steps = 0
            while not game.done:
                self.assertEqual(sum(game.stacks) + game.pot, sum(stacks))
                self.assertGreaterEqual(min(game.stacks), 0)
                cards = game.deck + game.board + game.hole[0] + game.hole[1] + game.burned
                self.assertEqual(len(cards), 52)
                self.assertEqual(len(set(cards)), 52)
                legal = game.legal_actions()
                self.assertTrue(legal)
                game.step(rng.choice(legal))
                steps += 1
                self.assertLess(steps, 40)
            self.assertEqual(sum(game.stacks), sum(stacks))
            self.assertEqual(game.pot, 0)
            self.assertEqual(sum(game.observation(p)['reward'] for p in (0, 1)), 0)
            self.assertEqual(game.legal_actions(), [])


if __name__ == '__main__':
    unittest.main()
