import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from pokerbot import web
from fastapi.testclient import TestClient
from pokerbot.web import app

class WebTests(unittest.TestCase):
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
        self.assertIn('started_cst',archive['setup'])

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
