"""Same Python table for Pages; snapshots stay in the visitor's IndexedDB."""
import base64
import json
import pickle
import uuid
from datetime import datetime, timezone
from .table import Table

games={}
counter=0

def dump():
    return base64.b64encode(pickle.dumps((games,counter))).decode()

def restore(snapshot):
    global games,counter
    if snapshot:
        games,counter=pickle.loads(base64.b64decode(snapshot))

def visible(gid):
    item=games[gid]
    game=item['game']
    data=game.view()
    data.update(id=gid,version=len(game.events),setup=item['setup'],events=[{k:v for k,v in e.items() if k!='cards' or e['kind']=='board'} for e in game.events])
    if game.ended:data['hands']=game.hands
    return data

def dispatch(path,method,body):
    global counter
    bits=path.strip('/').split('/')
    if path=='/api/games':
        if method=='GET':
            return [dict(id=gid,setup=item['setup'],ended=item['game'].ended,reason=item['game'].reason,hand=item['game'].hand) for gid,item in reversed(list(games.items()))]
        if method=='DELETE':
            games.clear();counter=0
            return dict(cleared=True)
        if method=='POST':
            human=body.get('human',True);bots=body.get('bots',['easy']);rounds=body.get('rounds',20)
            small=body.get('small_blind',1);big=body.get('big_blind',2);chips=body.get('starting_chips',100)
            if any(type(x)is not int for x in (rounds,small,big,chips)) or not 1<=rounds<=99 or not 1<=small<big<=chips<=1000000 or small>10000 or big>20000:
                raise ValueError('Invalid table settings')
            if type(human)is not bool or not 1<=len(bots)<=5 or any(b not in ('easy','intermediate') for b in bots) or len(bots)+human<2:
                raise ValueError('Choose valid bots and at least two seats')
            seats=([dict(name='YOU',kind='human',difficulty='')] if human else [])+[dict(name=f'BOT {i+1}',kind='bot',difficulty=d) for i,d in enumerate(bots)]
            table=Table(seats,rounds,small_blind=small,big_blind=big,starting_chips=chips)
            counter+=1;gid=uuid.uuid4().hex
            setup=dict(human=human,bots=bots,rounds=rounds,small_blind=small,big_blind=big,starting_chips=chips,game_number=counter,title=f'Game {counter}',started_utc=datetime.now(timezone.utc).isoformat(),betting='no-limit',bot_base='RLCard 1.2.0 limit-holdem-rule-v1')
            games[gid]=dict(game=table,setup=setup)
            return visible(gid)
    gid=bits[2]
    if gid not in games:raise KeyError('Game not found')
    game=games[gid]['game']
    if method=='DELETE':
        del games[gid]
        return dict(cleared=True,id=gid)
    if bits[-1]=='export':
        if not game.ended:raise PermissionError('Full history unlocks when the game ends')
        return dict(id=gid,setup=games[gid]['setup'],reason=game.reason,seats=game.seats,hands=game.hands,events=game.events)
    if method=='GET':return visible(gid)
    if body.get('version')!=len(game.events):raise ValueError('Table changed; refresh')
    action=body['action']
    if action=='reset':game.end('reset')
    elif action=='next':game.next_hand()
    elif action=='vote':
        if not game.hand_done or game.ended:raise ValueError('Agreement requires a settled hand')
        game.votes=[p for p,s in enumerate(game.seats) if s['chips']>0]
        game.event('unanimous_vote',seats=game.votes);game.end('unanimous agreement')
    elif action=='tick':
        if game.ended or game.hand_done or game.seats[game.current]['kind']!='bot':raise ValueError('No bot turn')
        game.action(game.bot_action())
    else:
        if game.ended or game.hand_done or game.seats[game.current]['kind']!='human':raise ValueError('Not your turn')
        game.action(action,body.get('amount'))
    return visible(gid)

def request(raw):
    try:
        args=json.loads(raw)
        result=dispatch(args['path'],args['method'],args.get('body') or {})
        return json.dumps(dict(status=200,result=result,snapshot=dump()))
    except (ValueError,KeyError,PermissionError) as exc:
        return json.dumps(dict(status=403 if isinstance(exc,PermissionError) else 404 if isinstance(exc,KeyError) else 422,result=dict(detail=str(exc))))
