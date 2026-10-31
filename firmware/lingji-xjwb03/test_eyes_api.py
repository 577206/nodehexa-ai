import asyncio,json
from aiohttp.test_utils import TestClient,TestServer
from omni_bridge import Controller,create_app
from test_omni import config

def test_eye_controls_validation_transport_and_no_motion():
 async def run():
  owner=Controller(config());sent=[]
  async def request(method,path,data=None):
   sent.append((method,path,json.loads(data)));return 202,b'{}'
  owner.request=request
  h={'Host':'127.0.0.1:8765'}
  async with TestClient(TestServer(create_app(owner))) as c:
   valid={'mode':8,'durationMs':1000,'contrast':127}
   for bad in ([],{},dict(valid,mode=17),dict(valid,mode=True),dict(valid,contrast=256),dict(valid,durationMs=0)):
    assert (await c.post('/api/eyes',headers=h,json=bad)).status==400
   assert not sent
   assert (await c.post('/api/eyes',headers={**h,'Origin':'https://example.com'},json=valid)).status==403
   for mode in (8,-1):
    value=dict(valid,mode=mode)
    assert (await c.post('/api/eyes',headers=h,json=value)).status==202
    assert sent[-1]==('POST','/api/eyes',value)
   async def offline(*args):raise TimeoutError('offline')
   owner.request=offline
   assert (await c.post('/api/eyes',headers=h,json=valid)).status==503
   assert not owner.motion_enabled
 asyncio.run(run())
