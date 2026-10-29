"""Local FastAPI server. SQLite persists active sessions and complete audit history."""
import json
import pickle
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone, timedelta
from threading import RLock
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .table import Table

ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'data'
DATA.mkdir(exist_ok=True)
DB=DATA/'games.sqlite3'
lock=RLock()

@contextmanager
def database():
    con=sqlite3.connect(DB)
    try:
        with con:
            yield con
    finally:
        con.close()

with database() as con:
    con.execute('CREATE TABLE IF NOT EXISTS games(id TEXT PRIMARY KEY, started TEXT, setup TEXT, state BLOB)')

app=FastAPI(title='Holdem ASCII')
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class Setup(BaseModel):
    human:bool=True
    bots:list[str]=Field(default_factory=lambda:['easy'],min_length=1,max_length=5)
    rounds:int=Field(default=20,ge=1,le=99)

class Action(BaseModel):
    action:str
    version:int
    amount:int|None=Field(default=None,strict=True)

def load(gid):
    with database() as con:
        row=con.execute('SELECT state FROM games WHERE id=?',(gid,)).fetchone()
    if row is None:
        raise HTTPException(404,'Game not found')
    game=pickle.loads(row[0])  # Local database only; never accept uploaded pickle data.
    if not hasattr(game,'min_raise'):
        game.min_raise,game.acted_bets=2,{}
    return game

def save(gid,game):
    with database() as con:
        con.execute('UPDATE games SET state=? WHERE id=?',(pickle.dumps(game),gid))

def view(gid,game):
    result=game.view()
    result.update(id=gid,version=len(game.events))
    with database() as con:
        result['setup']=json.loads(con.execute('SELECT setup FROM games WHERE id=?',(gid,)).fetchone()[0])
    result['events']=[{k:v for k,v in e.items() if k!='cards' or e['kind']=='board'} for e in game.events]
    if game.ended:
        result['hands']=game.hands
    return result

@app.get('/')
def home():
    return FileResponse(ROOT/'static'/'index.html')

@app.post('/api/games')
def create(setup:Setup):
    if any(d not in ('easy','intermediate') for d in setup.bots) or (not setup.human and len(setup.bots)<2):
        raise HTTPException(422,'Choose valid difficulties and at least two seats')
    seats=([dict(name='YOU',kind='human',difficulty='')] if setup.human else [])
    seats += [dict(name=f'BOT {i+1}',kind='bot',difficulty=d) for i,d in enumerate(setup.bots)]
    game=Table(seats,setup.rounds)
    gid=uuid.uuid4().hex
    # Explicit CST (UTC-06:00), year-round as requested; UTC retained for interchange.
    started=datetime.now(timezone.utc)
    meta=dict(**setup.model_dump(),small_blind=1,big_blind=2,starting_chips=100,
              started_utc=started.isoformat(),started_cst=started.astimezone(timezone(timedelta(hours=-6))).isoformat(),timezone='CST UTC-06:00',betting='no-limit',bot_base='RLCard 1.2.0 limit-holdem-rule-v1')
    with lock,database() as con:
        con.execute('INSERT INTO games VALUES(?,?,?,?)',(gid,started.isoformat(),json.dumps(meta),pickle.dumps(game)))
    return view(gid,game)

@app.get('/api/games')
def history():
    with database() as con:
        rows=con.execute('SELECT id,setup,state FROM games ORDER BY started DESC LIMIT 100').fetchall()
    return [dict(id=i,setup=json.loads(s),ended=(g:=pickle.loads(b)).ended,reason=g.reason,hand=g.hand) for i,s,b in rows]

@app.get('/api/games/{gid}')
def state(gid:str):
    with lock:
        return view(gid,load(gid))

@app.post('/api/games/{gid}/action')
def action(gid:str,body:Action):
    with lock:
        game=load(gid)
        if body.version!=len(game.events):
            raise HTTPException(409,'Table changed; refresh')
        try:
            if body.action=='reset':
                game.end('reset')
            elif body.action=='vote':
                # Each remaining bot consents only at a hand boundary, never mid-pot.
                if not game.hand_done or game.ended:
                    raise ValueError('End agreement is available between hands')
                game.votes=[p for p,s in enumerate(game.seats) if s['chips']>0]
                game.event('unanimous_vote',seats=game.votes)
                game.end('unanimous agreement')
            elif body.action=='next':
                game.next_hand()
            elif body.action=='tick':
                if game.hand_done or game.ended or game.seats[game.current]['kind']!='bot':
                    raise ValueError('No bot turn')
                game.action(game.bot_action())
            else:
                if game.ended or game.hand_done or game.seats[game.current]['kind']!='human':
                    raise ValueError('Not your turn')
                game.action(body.action,body.amount)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        save(gid,game)
        return view(gid,game)

@app.get('/api/games/{gid}/export')
def export(gid:str):
    with lock,database() as con:
        game=load(gid)
        if not game.ended:
            raise HTTPException(403,'Full card history unlocks when the game ends')
        setup=json.loads(con.execute('SELECT setup FROM games WHERE id=?',(gid,)).fetchone()[0])
        return dict(id=gid,setup=setup,reason=game.reason,seats=game.seats,hands=game.hands,events=game.events)
