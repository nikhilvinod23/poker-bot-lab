"""Multiplayer fixed-limit table and RLCard baseline adapters."""
import random
from datetime import datetime, timezone, timedelta
from .engine import rank_hand, RANKS
import ast
from importlib.metadata import distribution

# RLCard's model registry eagerly imports unrelated pretrained games and runs
# pip discovery on import. Load its standalone rule class from the pinned,
# installed package without triggering that registry (no policy reimplementation).
_path = distribution('rlcard').locate_file('rlcard/models/limitholdem_rule_models.py')
_tree = ast.parse(_path.read_text(encoding='utf-8'))
_agent = next(n for n in _tree.body if isinstance(n,ast.ClassDef) and n.name=='LimitholdemRuleAgentV1')
_namespace = {}
exec(compile(ast.Module(body=[_agent],type_ignores=[]),str(_path),'exec'),_namespace)
LimitholdemRuleAgentV1 = _namespace['LimitholdemRuleAgentV1']


class Table:
    def __init__(self, seats, limit=20, seed=None):
        self.rng = random.Random(seed)
        self.seats = [dict(s, chips=100, won=0, played=0, folded=0) for s in seats]
        self.limit, self.hand, self.dealer = limit, 0, -1
        self.events, self.hands = [], []
        self.ended, self.reason, self.hand_done = False, '', True
        self.votes = []
        self.next_hand()

    def event(self, kind, **data):
        self.events.append(dict(index=len(self.events), hand=self.hand, kind=kind,
                                time_cst=datetime.now(timezone(timedelta(hours=-6))).isoformat(), **data))

    def after(self, seat, pool):
        return next((seat+i) % len(self.seats) for i in range(1, len(self.seats)+1) if (seat+i) % len(self.seats) in pool)

    def pay(self, p, amount):
        amount = min(amount, self.seats[p]['chips'])
        self.seats[p]['chips'] -= amount
        self.bets[p] += amount
        self.total[p] += amount

    def next_hand(self):
        if self.ended or not self.hand_done:
            raise ValueError('Hand is still active')
        alive = [i for i,s in enumerate(self.seats) if s['chips'] > 0]
        if len(alive) < 2 or self.hand >= self.limit:
            self.end('last player' if len(alive) < 2 else 'round limit')
            return
        self.dealer = self.after(self.dealer, alive)
        self.hand += 1
        self.hand_done = False
        self.live = set(alive)
        self.hole = {i: [] for i in alive}
        self.deck = [r+s for r in RANKS for s in 'cdhs']
        self.rng.shuffle(self.deck)
        for _ in range(2):
            for p in alive:
                self.hole[p].append(self.deck.pop())
        self.board, self.burned = [], []
        self.bets = [0]*len(self.seats)
        self.total = [0]*len(self.seats)
        self.street, self.raises, self.target = 0, 1, 2
        self.sb = self.dealer if len(alive)==2 else self.after(self.dealer, alive)
        self.bb = self.after(self.sb, alive)
        self.pay(self.sb,1)
        self.pay(self.bb,2)
        self.pending = {p for p in alive if self.seats[p]['chips']}
        for p in alive:
            self.seats[p]['played'] += 1
        self.start_event = len(self.events)
        self.event('deal', dealer=self.dealer, small_blind=self.sb, big_blind=self.bb,
                   cards={str(p): cards[:] for p,cards in self.hole.items()})
        self.current = self.bb
        self.settle_turn()

    def legal(self):
        if self.ended or self.hand_done:
            return []
        p = self.current
        owed = max(0, self.target-self.bets[p])
        actions = ['fold','call'] if owed else ['check']
        size = 2 if self.street < 2 else 4
        if self.raises < 4 and self.seats[p]['chips'] >= owed+size and any(self.seats[q]['chips'] for q in self.live if q!=p):
            actions.append('raise')
        return actions

    def action(self, action):
        if action not in self.legal():
            raise ValueError('Illegal action')
        p = self.current
        before = self.seats[p]['chips']
        self.pending.discard(p)
        if action=='fold':
            self.live.remove(p)
            self.seats[p]['folded'] += 1
        elif action=='raise':
            self.target += 2 if self.street < 2 else 4
            self.pay(p,self.target-self.bets[p])
            self.raises += 1
            self.pending = {q for q in self.live if q!=p and self.seats[q]['chips']}
        elif action=='call':
            self.pay(p,max(0,self.target-self.bets[p]))
        self.event('action', seat=p, action=action, paid=before-self.seats[p]['chips'])
        self.settle_turn()

    def settle_turn(self):
        if len(self.live)==1:
            self.finish()
            return
        self.pending = {p for p in self.pending if p in self.live and self.seats[p]['chips']}
        actionable = [p for p in self.live if self.seats[p]['chips']]
        if len(actionable)==1 and self.bets[actionable[0]] >= max(self.bets[p] for p in self.live):
            self.pending.clear()
        if self.pending:
            self.current = self.after(self.current, self.pending)
            # Initial preflop decision was already chosen before this method.
            return
        if self.street==3:
            self.finish()
            return
        self.street += 1
        self.burned.append(self.deck.pop())
        self.board.extend(self.deck.pop() for _ in range(3 if self.street==1 else 1))
        self.event('board', cards=self.board[:])
        self.bets = [0]*len(self.seats)
        self.target,self.raises = 0,0
        self.pending = {p for p in self.live if self.seats[p]['chips']}
        self.current = self.dealer
        self.settle_turn()

    def finish(self):
        awards = [0]*len(self.seats)
        levels = sorted(set(self.total)-{0})
        previous = 0
        for level in levels:
            contributors = [p for p,v in enumerate(self.total) if v>=level]
            amount = (level-previous)*len(contributors)
            previous=level
            eligible = [p for p in self.live if self.total[p]>=level]
            if len(contributors)==1:
                winners=contributors
            elif len(self.live)==1:
                winners=list(self.live)
            elif not eligible:
                # Only unmatched folded commitments; retain money among contributors.
                winners=contributors
            else:
                ranks={p:rank_hand(self.board+self.hole[p]) for p in eligible}
                winners=[p for p,r in ranks.items() if r==max(ranks.values())]
            ordered=sorted(winners,key=lambda p:(p-self.dealer-1)%len(self.seats))
            share,odd=divmod(amount,len(ordered))
            for j,p in enumerate(ordered):
                awards[p]+=share+(j<odd)
        for p,amount in enumerate(awards):
            self.seats[p]['chips']+=amount
            if amount>self.total[p]:
                self.seats[p]['won']+=1
        self.event('settlement', awards=awards, board=self.board[:], stacks=[s['chips'] for s in self.seats])
        self.hands.append(dict(hand=self.hand, board=self.board[:], cards={str(p):c[:] for p,c in self.hole.items()}, awards=awards, contributions=self.total[:]))
        self.hand_done=True
        if self.hand>=self.limit or sum(s['chips']>0 for s in self.seats)<2:
            self.end('round limit' if self.hand>=self.limit else 'last player')

    def end(self, reason):
        if self.ended:
            return
        if not self.hand_done:
            for p,v in enumerate(self.total):
                self.seats[p]['chips']+=v
            self.event('void_hand', refund=self.total[:], cards={str(p):c[:] for p,c in self.hole.items()}, board=self.board[:])
            self.hands.append(dict(hand=self.hand,void=True,board=self.board[:],cards={str(p):c[:] for p,c in self.hole.items()},refund=self.total[:]))
            self.hand_done=True
        self.ended,self.reason=True,reason
        self.event('end',reason=reason)

    def bot_action(self):
        p=self.current
        legal=self.legal()
        convert=lambda cards:[c[1].upper()+c[0] for c in cards]
        state={'raw_legal_actions':legal,'raw_obs':{'hand':convert(self.hole[p]),'public_cards':convert(self.board)}}
        choice=LimitholdemRuleAgentV1.step(state)
        if choice not in legal:
            choice='check' if 'check' in legal else 'call'
        if self.seats[p]['difficulty']=='easy':
            if self.rng.random()<.45:
                choice='check' if 'check' in legal else 'call'
            if choice=='raise' and self.rng.random()<.65:
                choice='check' if 'check' in legal else 'call'
        return choice

    def view(self):
        return dict(hand=self.hand,limit=self.limit,dealer=self.dealer,sb=self.sb,bb=self.bb,
                    street=self.street,board=self.board, pot=0 if self.hand_done else sum(self.total),
                    current=None if self.hand_done else self.current,legal=self.legal(),
                    to_call=max(0,self.target-self.bets[self.current]) if not self.hand_done else 0,
                    seats=[dict(s,seat=p,live=p in self.live,bet=0 if self.hand_done else self.bets[p],
                                cards=self.hole.get(p,[]) if s['kind']=='human' or self.ended or (self.hand_done and p in self.live and len(self.board)==5) else ['??']*len(self.hole.get(p,[]))) for p,s in enumerate(self.seats)],
                    ended=self.ended,reason=self.reason,hand_done=self.hand_done,votes=self.votes)
