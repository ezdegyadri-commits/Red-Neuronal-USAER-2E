"""Compatibilidad de arranque Render: sólo sirve la interfaz original Streamlit.

Permite conservar el comando uvicorn main:app de un servicio existente.
Los nuevos despliegues usan directamente streamlit run app.py (render.yaml).
No hay formulario paralelo ni segundo sistema de autenticación.
"""
import asyncio,json,os,subprocess,sys
from pathlib import Path
import httpx
from websockets.asyncio.client import connect

ROOT=Path(__file__).resolve().parent
PORT=int(os.getenv('USAER_STREAMLIT_PORT','8501'))
TARGET=f'http://127.0.0.1:{PORT}'
HOP={b'connection',b'keep-alive',b'proxy-authenticate',b'proxy-authorization',b'te',b'trailer',b'transfer-encoding',b'upgrade'}
_child=None
_ready=False

def child_command():
    command=[sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--server.port',str(PORT),'--server.headless','true','--browser.gatherUsageStats','false']
    host=os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if host:command+=['--browser.serverAddress',host]
    return command

async def startup():
    global _child,_ready
    _child=subprocess.Popen(child_command(),cwd=ROOT,env=os.environ.copy(),creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    async with httpx.AsyncClient(trust_env=False,timeout=2) as client:
        for _ in range(150):
            if _child.poll() is not None:raise RuntimeError('Streamlit no pudo iniciar; revisar configuración del servicio.')
            try:
                response=await client.get(TARGET+'/_stcore/health')
                if response.status_code==200:_ready=True;return
            except httpx.HTTPError:pass
            await asyncio.sleep(.2)
    raise RuntimeError('Streamlit no respondió al inicio.')

async def shutdown():
    global _ready
    _ready=False
    if _child is not None and _child.poll() is None:
        _child.terminate()
        try:await asyncio.to_thread(_child.wait,5)
        except subprocess.TimeoutExpired:_child.kill();await asyncio.to_thread(_child.wait)

async def websocket(scope,receive,send):
    await receive()  # websocket.connect
    headers=[(k.decode('latin1'),v.decode('latin1')) for k,v in scope['headers'] if k.lower() not in HOP|{b'host',b'origin',b'sec-websocket-key',b'sec-websocket-version',b'sec-websocket-protocol',b'sec-websocket-extensions'}]
    origin=next((v.decode('latin1') for k,v in scope['headers'] if k.lower()==b'origin'),None)
    path=scope.get('raw_path',scope['path'].encode()).decode('ascii')
    query=scope.get('query_string',b'').decode('ascii');url=f'ws://127.0.0.1:{PORT}'+path+('?' +query if query else '')
    try:
        async with connect(url,origin=origin,additional_headers=headers,subprotocols=scope.get('subprotocols',[]),proxy=None,max_size=None,open_timeout=10) as remote:
            await send({'type':'websocket.accept','subprotocol':remote.subprotocol})
            async def upstream():
                while True:
                    msg=await receive()
                    if msg['type']=='websocket.disconnect':break
                    await remote.send(msg.get('bytes') if msg.get('bytes') is not None else msg.get('text',''))
            async def downstream():
                async for message in remote:
                    await send({'type':'websocket.send', 'text' if isinstance(message,str) else 'bytes':message})
            tasks=[asyncio.create_task(upstream()),asyncio.create_task(downstream())]
            try:
                done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                for task in pending:task.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)
            finally:
                for task in tasks:task.cancel()
    except Exception:
        try:await send({'type':'websocket.close','code':1011})
        except Exception:pass

async def app(scope,receive,send):
    if scope['type']=='lifespan':
        while True:
            msg=await receive()
            if msg['type']=='lifespan.startup':
                try:await startup();await send({'type':'lifespan.startup.complete'})
                except Exception:await shutdown();await send({'type':'lifespan.startup.failed','message':'No se pudo iniciar Streamlit.'});return
            elif msg['type']=='lifespan.shutdown':await shutdown();await send({'type':'lifespan.shutdown.complete'});return
    elif scope['type']=='websocket':await websocket(scope,receive,send)
    elif scope['type']=='http':
        if scope['path'] in {'/health','/healthz'}:
            ok=_ready and _child is not None and _child.poll() is None
            body=json.dumps({'status':'ok' if ok else 'starting'}).encode()
            await send({'type':'http.response.start','status':200 if ok else 503,'headers':[(b'content-type',b'application/json'),(b'cache-control',b'no-store')]})
            await send({'type':'http.response.body','body':b'' if scope['method']=='HEAD' else body});return
        async def body():
            while True:
                msg=await receive()
                if msg['type']=='http.disconnect':break
                yield msg.get('body',b'')
                if not msg.get('more_body',False):break
        path=scope.get('raw_path',scope['path'].encode()).decode('ascii');query=scope.get('query_string',b'').decode('ascii')
        url=TARGET+path+('?' +query if query else '')
        headers=[(k,v) for k,v in scope['headers'] if k.lower() not in HOP]
        async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(60,connect=5)) as client:
            try:
                request=client.build_request(scope['method'],url,headers=headers,content=body())
                response=await client.send(request,stream=True)
            except httpx.HTTPError:
                await send({'type':'http.response.start','status':503,'headers':[(b'content-type',b'text/plain; charset=utf-8')]})
                await send({'type':'http.response.body','body':'El servicio está iniciando. Tu sesión no se ha cerrado.'.encode()});return
            try:
                await send({'type':'http.response.start','status':response.status_code,'headers':[(k,v) for k,v in response.headers.raw if k.lower() not in HOP]})
                async for chunk in response.aiter_raw():await send({'type':'http.response.body','body':chunk,'more_body':True})
                await send({'type':'http.response.body','body':b''})
            finally:await response.aclose()
