import asyncio
import json
import re
from pathlib import Path
import pytest
from generate_motion_presets import render, DEST
from omni_protocol import PRESETS,ACTIONS,LEGACY_ACTIONS,validate_action
from omni_bridge import Controller,Conversation,session_config
from test_omni import config

ROOT=Path(__file__).parent

def test_catalog_covers_all_implemented_modes_and_bounded_performances():
    enum=(ROOT.parent/'src/movement.h').read_text()
    modes=set(re.findall(r'\bMOVEMENT_([A-Z]+)\b',enum))-{'TOTAL'}
    actual={p['payload']['mode'].replace('_','').upper() for p in PRESETS if 'mode' in p['payload']}
    assert actual==modes
    assert len(set(ACTIONS))==len(ACTIONS)==18
    assert {p['payload']['performance'] for p in PRESETS if 'performance' in p['payload']}=={'freestyle','beatsway','showtime'}
    for p in PRESETS:
        payload=p['payload']
        if 'cycles' in payload:assert 0<payload['cycles']<=1
        elif 'performance' in payload:assert payload['repeat'] is False
        else:assert payload=={'stop':True}
        assert len(json.dumps(payload,separators=(',',':')).encode())<=117
        assert validate_action({'action':p['id']})==p['id']
    assert DEST.read_text()==render()
    with pytest.raises(ValueError):validate_action({'action':'freestyle','repeat':True})
    with pytest.raises(ValueError):validate_action({'action':'single_leg_raw'})


def test_old_firmware_does_not_advertise_or_receive_new_actions():
    async def run():
        c=Controller(config());c.motion_enabled=True
        async def forbidden(*a,**kw):raise AssertionError('Unsupported action reached hardware')
        c.request=forbidden
        assert c.available_actions()==LEGACY_ACTIONS
        r=await c.move('freestyle')
        assert not r['ok'] and r['status']=='firmware_update_required'
        session=Conversation(c,1)
        tools=session_config(session.instructions,session.actions)['session']['tools']
        move=next(t['function'] for t in tools if t['function']['name']=='move')
        assert tuple(move['parameters']['properties']['action']['enum'])==LEGACY_ACTIONS
    asyncio.run(run())


def test_expanded_actions_still_require_enable_and_real_ack():
    async def run():
        c=Controller(config());c.board_status={'robot':{'actions':list(ACTIONS)}}
        assert len(c.available_actions())==18
        r=await c.move('showtime');assert r['status']=='disabled'
        c.motion_enabled=True;calls=[]
        async def request(method,path,data=None):
            calls.append((method,path,data))
            if method=='POST':return 202,b'{"status":"queued"}'
            seq=1 if len(calls)==1 else 2
            return 200,json.dumps({'robot':{'online':True,'bench':False,'ackSequence':seq,'ackAction':'showtime','ackSuccess':True}}).encode()
        c.request=request
        r=await c.move('showtime');assert r['ok'] is True
        assert json.loads(calls[1][2])=={'action':'showtime'}
    asyncio.run(run())
