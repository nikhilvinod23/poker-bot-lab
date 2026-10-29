import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from pokerbot import web
from fastapi.testclient import TestClient
from pokerbot.web import app

class WebTests(unittest.TestCase):
    def test_settings_validation(self):
        c=TestClient(app)
        self.assertEqual(c.post('/api/games',json={'small_blind':5,'big_blind':2}).status_code,422)
        self.assertEqual(c.post('/api/games',json={'starting_chips':10,'big_blind':20}).status_code,422)
        g=c.post('/api/games',json={'small_blind':3,'big_blind':7,'starting_chips':250,'rounds':9}).json()
        self.assertEqual(g['setup']['title'],'Game 1')
        self.assertEqual(g['setup']['small_blind'],3)
        self.assertEqual(g['raise_min'],7)
        self.assertEqual(sum(s['chips'] for s in g['seats'])+g['pot'],500)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.dbpatch=patch.object(web,'DB',Path(self.temp.name)/'test.sqlite3')
        self.dbpatch.start()
        with web.database() as con:
            con.execute('CREATE TABLE games(id TEXT PRIMARY KEY, started TEXT, setup TEXT, state BLOB)')

    def tearDown(self):
        self.dbpatch.stop()
        self.temp.cleanup()

    def test_bot_game_and_archive(self):
        c=TestClient(app)
        g=c.post('/api/games',json={'human':False,'bots':['easy','intermediate'],'rounds':2}).json()
        gid=g['id']
        self.assertEqual(c.get(f'/api/games/{gid}/export').status_code,403)
        for _ in range(200):
            if g['ended']:break
            action='next' if g['hand_done'] else 'tick'
            r=c.post(f'/api/games/{gid}/action',json={'action':action,'version':g['version']})
            self.assertEqual(r.status_code,200,r.text)
            g=r.json()
        self.assertTrue(g['ended'])
        self.assertEqual(g['reason'],'round limit')
        archive=c.get(f'/api/games/{gid}/export').json()
        self.assertEqual(len(archive['hands']),2)
        self.assertEqual(sum(s['chips'] for s in archive['seats']),200)
        self.assertIn('started_local',archive['setup'])
        self.assertEqual(archive['setup']['timezone'],'America/Chicago')

    def test_numbering_and_clear(self):
        c=TestClient(app)
        a=c.post('/api/games',json={}).json()
        b=c.post('/api/games',json={}).json()
        self.assertEqual(a['setup']['title'],'Game 1')
        self.assertEqual(b['setup']['game_number'],2)
        self.assertEqual(c.delete('/api/games/'+b['id']).status_code,200)
        self.assertEqual(c.post('/api/games',json={}).json()['setup']['game_number'],3)
        self.assertEqual(c.delete('/api/games').status_code,200)
        self.assertEqual(c.get('/api/games').json(),[])
        self.assertEqual(c.post('/api/games',json={}).json()['setup']['title'],'Game 1')

    def test_reset_privacy_and_validation(self):
        c=TestClient(app)
        self.assertEqual(c.post('/api/games',json={'rounds':100}).status_code,422)
        self.assertEqual(c.post('/api/games',json={'human':False,'bots':['easy']}).status_code,422)
        g=c.post('/api/games',json={}).json()
        self.assertNotIn('cards',g['events'][0])
        self.assertEqual(g['seats'][1]['cards'],['??','??'])
        self.assertEqual(c.post(f"/api/games/{g['id']}/action",json={'action':'reset','version':-1}).status_code,409)
        r=c.post(f"/api/games/{g['id']}/action",json={'action':'reset','version':g['version']}).json()
        self.assertTrue(r['ended'])
        self.assertEqual(sum(s['chips'] for s in r['seats']),200)

    def test_unanimous_vote(self):
        c=TestClient(app)
        g=c.post('/api/games',json={'human':True,'bots':['easy'],'rounds':20}).json()
        g=c.post(f"/api/games/{g['id']}/action",json={'action':'fold','version':g['version']}).json()
        g=c.post(f"/api/games/{g['id']}/action",json={'action':'vote','version':g['version']}).json()
        self.assertEqual(g['reason'],'unanimous agreement')
        self.assertEqual(len(g['votes']),2)
