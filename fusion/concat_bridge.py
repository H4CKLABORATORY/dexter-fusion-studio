"""Cliente real de Concat JSON-RPC (API 0.2, loopback + token obligatorio).

Referencia oficial: https://concat.standalones.org/docs/transports/json-rpc/
No abre servidores ni envía credenciales a proveedores externos.
"""
import itertools
import json
import socket
from pathlib import Path
from .project import read_json

class ConcatClient:
    def __init__(self,token,host='127.0.0.1',port=7420,timeout=20,on_event=None):
        if host not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Por seguridad solo se admite Concat local')
        if not token: raise ValueError('Introduce el token de Concat: Settings > Remote')
        self.sock=socket.create_connection((host,int(port)),timeout=timeout)
        self.sock.settimeout(timeout)
        self.reader=self.sock.makefile('r',encoding='utf-8')
        self.ids=itertools.count(1)
        self.on_event=on_event or (lambda event:None)
        self._send({'jsonrpc':'2.0','id':0,'method':'auth','params':{'token':token}})
        self._wait(0)
    def _send(self,packet):
        self.sock.sendall((json.dumps(packet,ensure_ascii=False)+'\n').encode('utf-8'))
    def _wait(self,identifier):
        while True:
            line=self.reader.readline()
            if not line:raise ConnectionError('Concat cerró la conexión')
            msg=json.loads(line)
            if 'id' not in msg:
                self.on_event(msg)
                continue
            if msg.get('id')!=identifier:continue
            if 'error' in msg:
                e=msg['error']
                raise RuntimeError(f"Concat {e.get('data',{}).get('code','error')}: {e.get('message')}")
            return msg.get('result')
    def call(self,method,**params):
        ident=next(self.ids)
        self._send({'jsonrpc':'2.0','id':ident,'method':method,'params':params})
        return self._wait(ident)
    def close(self):
        try:self.reader.close()
        finally:self.sock.close()
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()

def list_concat_effects(token,port=7420):
    """Devuelve IDs reales de los efectos instalados en la versión local de Concat."""
    with ConcatClient(token,port=port) as cli:
        cli.call('version')
        return cli.call('catalogue.list',kind='effect')

def create_concat_edit(folder,token,*,use_export=True,port=7420,effect_id=None):
    """Crea un proyecto Concat con un video de este estudio; no clona sus efectos.

    Edición manual avanzada después en Concat. Nunca sobrescribe su proyecto.
    """
    folder=Path(folder).resolve()
    proj=read_json(folder/'project.json')
    video=Path(proj['source'])
    plan=read_json(folder/'edit-plan.json',{})
    if use_export and plan:
        final=folder/'output'/f"{plan['platform']}-{plan['effects']}.mp4"
        if final.is_file():video=final
    base=folder/'concat-edits'
    base.mkdir(exist_ok=True)
    with ConcatClient(token,port=port) as api:
        version=api.call('version')
        if str(version.get('apiVersion','')).split('.')[0]!='0':
            raise RuntimeError('La API Concat es distinta: requiere revisión del adaptador')
        if effect_id:
            available=api.call('catalogue.list',kind='effect')
            if effect_id not in {item['id'] for item in available}:
                raise ValueError('Ese efecto no existe en la versión de Concat instalada')
        name='Dexter-Edit'
        path=base/name
        if path.exists():raise FileExistsError('El proyecto ya existe, no se sobrescribe')
        api.call('project.create',location=str(base),name=name)
        view=api.call('media.import',path=str(path),file=str(video))
        media_id=view.get('createdId')
        if not media_id:
            raise RuntimeError('Concat no devolvió ID de medio; comprobar la librería de medios')
        clip=api.call('edit.apply',path=str(path),command={'op':'addClipAtFirstFree','mediaId':media_id,'start':0})
        clip_id=clip.get('createdId')
        if effect_id:
            if not clip_id:raise RuntimeError('Concat no proporcionó el ID del clip')
            api.call('edit.apply',path=str(path),command={
                'op':'updateClip','clipId':clip_id,
                'patch':{'videoEffects':[{'id':effect_id,'params':{}}]}})
        api.call('project.save',path=str(path))
        return {'folder':str(path),'concat_version':version.get('concat'),
                'source':str(video),'concat_effect':effect_id,'status':'created_and_saved'}
