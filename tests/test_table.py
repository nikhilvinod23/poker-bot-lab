import random
import unittest
from pokerbot.table import Table

def seats(n):
    return [dict(name=f'B{i}',kind='bot',difficulty='easy' if i%2 else 'intermediate') for i in range(n)]

class MultiplayerTests(unittest.TestCase):
    def test_configurable_blinds_and_stack(self):
        t=Table(seats(3),small_blind=3,big_blind=7,starting_chips=250)
        self.assertEqual(t.bets,[0,3,7])
        self.assertEqual(t.min_raise,7)
        self.assertEqual(sum(s['chips'] for s in t.seats)+sum(t.total),750)
        t.action('call');t.action('call');t.action('check')
        self.assertEqual(t.min_raise,7)

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
        self.assertEqual([p['amount'] for p in t.last_pots],[30,40,30])
        self.assertEqual(t.last_pots[0]['awards'],{'0':30})
        self.assertEqual(t.last_pots[1]['awards'],{'1':40})
        self.assertTrue(t.last_pots[2]['refund'])
        self.assertEqual(t.events[-1]['hand_types']['0']['label'],'Pair of aces')

    def test_three_contested_pots_and_folded_privacy(self):
        for folded in (False,True):
            t=Table(seats(4))
            t.board='2c 3d 7h 9s Jc'.split()
            t.hole={0:['7c','7d'],1:['Kc','Kd'],2:['Qc','Qd'],3:['Tc','Td']}
            t.total=[20,50,80,80]
            for p,v in enumerate(t.total):t.seats[p]['chips']=100-v
            t.live={0,2,3} if folded else {0,1,2,3}
            t.finish()
            self.assertEqual([p['amount'] for p in t.last_pots],[80,90,60])
            self.assertEqual(sum(s['chips'] for s in t.seats),400)
            self.assertEqual([s['chips'] for s in t.seats],[160,50,170,20] if folded else [160,140,80,20])
            self.assertEqual(t.hands[-1]['hand_types']['1']['label'],'Pair of kings')
            if folded:self.assertEqual(t.events[-1]['hand_types']['1'],{'label':'Folded — not shown'})

    def test_tied_pot_odd_chip(self):
        t=Table(seats(3))
        t.board='Tc Jc Qc Kc Ac'.split()
        t.hole={0:['2d','3d'],1:['4d','5d'],2:['6d','7d']}
        t.total=[1,2,2];t.live={1,2}
        for p,v in enumerate(t.total):t.seats[p]['chips']=100-v
        t.finish()
        self.assertEqual([s['chips'] for s in t.seats],[99,101,100])
        self.assertEqual(t.events[-1]['hand_types']['1']['label'],'Royal flush')

    def test_allin_action_sequence_builds_side_pots(self):
        t=Table(seats(4),seed=81)
        for p,stack in enumerate([50,80,80,20]):t.seats[p]['chips']=stack-t.total[p]
        t.action('raise',18)
        t.action('call')
        t.action('raise',30)
        t.action('raise',30)
        t.action('call')
        t.action('call')
        self.assertTrue(t.hand_done)
        self.assertEqual(t.total,[50,80,80,20])
        self.assertEqual([p['amount'] for p in t.last_pots],[80,90,60])
        self.assertEqual(sum(s['chips'] for s in t.seats),230)
        self.assertEqual(sum(e.get('all_in',False) for e in t.events),4)

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
