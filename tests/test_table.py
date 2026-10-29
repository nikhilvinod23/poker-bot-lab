import random
import unittest
from pokerbot.table import Table

def seats(n):
    return [dict(name=f'B{i}',kind='bot',difficulty='easy' if i%2 else 'intermediate') for i in range(n)]

class MultiplayerTests(unittest.TestCase):
    def test_custom_raise_and_invalid_amount(self):
        t=Table(seats(3),seed=9)
        before=t.view()
        with self.assertRaises(ValueError):t.action('raise',1)
        self.assertEqual(t.view(),before)
        t.action('raise',10)
        self.assertEqual(t.target,12)
        self.assertEqual(t.min_raise,10)
        self.assertEqual(t.events[-1]['raise_by'],10)
        self.assertEqual(t.bets[0],12)

    def test_short_allin_does_not_reopen(self):
        t=Table(seats(3),seed=9)
        t.action('raise',10)
        t.seats[1]['chips']=12
        t.action('raise',1)
        t.action('call')
        self.assertEqual(t.current,0)
        self.assertNotIn('raise',t.legal())

    def test_order_and_rotation(self):
        t=Table(seats(4),3,seed=1)
        self.assertEqual((t.dealer,t.sb,t.bb,t.current),(0,1,2,3))
        while not t.hand_done:
            t.action('check' if 'check' in t.legal() else 'call')
        t.next_hand()
        self.assertEqual((t.dealer,t.sb,t.bb,t.current),(1,2,3,0))

    def test_heads_up_order(self):
        t=Table(seats(2),2)
        self.assertEqual((t.dealer,t.sb,t.bb,t.current),(0,0,1,0))
        t.action('call');t.action('check')
        self.assertEqual(t.current,1)

    def test_random_games(self):
        for count in range(2,7):
            for seed in range(12):
                t=Table(seats(count),20,seed=seed)
                rng=random.Random(seed)
                while not t.ended:
                    if t.hand_done:
                        t.next_hand()
                        continue
                    self.assertEqual(sum(s['chips'] for s in t.seats)+sum(t.total),100*count)
                    self.assertTrue(t.legal())
                    t.action(rng.choice(t.legal()) if seed%2 else t.bot_action())
                self.assertEqual(sum(s['chips'] for s in t.seats),100*count)
                self.assertLessEqual(t.hand,20)
                self.assertEqual(t.reason,'round limit' if t.hand==20 else 'last player')

    def test_side_pots(self):
        t=Table(seats(3))
        t.board='2c 3d 7h 9s Jc'.split()
        t.hole={0:['Ac','Ad'],1:['Kc','Kd'],2:['Qc','Qd']}
        t.total=[10,30,60]
        for p,x in enumerate(t.total):t.seats[p]['chips']=100-x
        t.live={0,1,2}
        t.finish()
        self.assertEqual([s['chips'] for s in t.seats],[120,110,70])

    def test_reset_refunds(self):
        t=Table(seats(6))
        t.end('reset')
        self.assertEqual(sum(s['chips'] for s in t.seats),600)
        self.assertTrue(t.hands[-1]['void'])

    def test_no_hidden_cards_before_end(self):
        t=Table([dict(name='YOU',kind='human',difficulty='')]+seats(2))
        self.assertNotEqual(t.view()['seats'][0]['cards'],['??','??'])
        self.assertEqual(t.view()['seats'][1]['cards'],['??','??'])

if __name__=='__main__':unittest.main()
