import asyncio
import copy
import json
import os
import pytest
from aiohttp.test_utils import TestClient, TestServer
from omni_bridge import Controller, Conversation, create_app
from omni_memory import MemoryStore
from test_omni import config


def test_memory_persists_edits_and_bounded_context(tmp_path):
    path=tmp_path/'memory.json'
    memory=MemoryStore(path)
    memory.remember('nickname','小米')
    for i in range(30):
        memory.append('user' if i%2==0 else 'assistant', str(i))
    assert len(memory.pairs())==24 and memory.pairs()[0][1]=='6'
    item=memory.data['history'][0]
    memory.edit(item['id'], item['text'], '更正内容')
    loaded=MemoryStore(path)
    assert loaded.data['preferences']['nickname']=='小米'
    assert loaded.pairs()[0][1]=='更正内容'
    assert os.stat(path).st_mode & 0o777 == 0o600
    with pytest.raises(RuntimeError):
        loaded.edit(item['id'], item['text'], '过期的修改')
    loaded.clear()
    assert not MemoryStore(path).pairs()
    assert MemoryStore(path).data['preferences']['nickname']=='小米'


def test_write_failure_preserves_old_memory(tmp_path,monkeypatch):
    memory=MemoryStore(tmp_path/'memory.json')
    memory.remember('nickname','原称呼')
    old=copy.deepcopy(memory.data)
    def fail(*args): raise OSError('disk failed')
    monkeypatch.setattr(os,'replace',fail)
    with pytest.raises(OSError): memory.remember('nickname','新称呼')
    assert memory.data==old and MemoryStore(memory.path).data==old
    assert not list(tmp_path.glob('.lingxi-memory-*'))


def test_settings_are_snapshot_until_next_wake():
    owner=Controller(config())
    before=Conversation(owner,1)
    owner.conversation=before
    owner.memory.remember('nickname','新的称呼')
    assert '新的称呼' not in before.instructions
    assert '新的称呼' in Conversation(owner,2).instructions
    assert owner.memory_status()['pending'] is True
    with pytest.raises(ValueError): owner.memory.remember('api_key','not-allowed')


def test_end_waits_for_hardware_tail_not_cloud_completion():
    async def run():
        owner=Controller(config());owner.generation=1
        states=iter([3,3,2,1]);sent=[];observed=[]
        async def request(method,path,data=None):
            state=next(states);observed.append(state)
            return 200,json.dumps({'audioState':state,'audioGeneration':1}).encode()
        async def down(gen,cmd,packets=()): sent.append((cmd,observed[-1]))
        owner.request=request;owner.down=down
        await owner.finish_dialog(1)
        assert observed==[3,3,2,1] and sent==[(5,1)]
    asyncio.run(run())


def test_end_tool_does_not_send_idle_before_goodbye():
    async def run():
        owner=Controller(config());s=Conversation(owner,1);commands=[];messages=[]
        async def down(gen,cmd,packets=()):commands.append(cmd)
        async def send(message):messages.append(message)
        owner.down=down;s.send=send
        await s.run_tools([{'call_id':'end1','name':'end_conversation','arguments':'{}'}])
        assert s.ending and commands==[4]
        assert json.loads(messages[0]['item']['output'])['ok'] is True
        assert messages[-1]['type']=='response.create'
    asyncio.run(run())


def test_editor_api_validation_conflicts_and_origin(tmp_path):
    async def run():
        owner=Controller(config(),MemoryStore(tmp_path/'memory.json'))
        async with TestClient(TestServer(create_app(owner))) as client:
            headers={'Host':'127.0.0.1:8765'}
            r=await client.get('/api/memory',headers=headers);assert r.status==200
            m=await r.json();payload={k:m[k] for k in ('identity','preferences','revision')}
            payload['identity']['name']='测试灵犀'
            r=await client.post('/api/settings',headers=headers,json=payload);assert r.status==200
            owner.memory.remember('nickname','测试称呼')
            r=await client.post('/api/settings',headers=headers,json=payload);assert r.status==409
            assert owner.memory.data['preferences']['nickname']=='测试称呼'
            r=await client.post('/api/settings',headers=headers,json=[]);assert r.status==400
            r=await client.post('/api/context',headers={**headers,'Origin':'https://example.com'},json={'action':'clear'});assert r.status==403
            owner.memory.append('user','需要修改的内容')
            item=owner.memory.data['history'][0]
            r=await client.post('/api/context',headers=headers,json={'id':item['id'],'previous':item['text'],'text':'已更正'});assert r.status==200
            r=await client.get('/api/memory',headers=headers);body=await r.text()
            assert 'fake-test-key' not in body and 'a'*64 not in body
            assert '已更正' in json.loads(body)['history'][0]['text']
    asyncio.run(run())
