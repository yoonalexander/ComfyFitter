"""Opt-in local look storage, independent of temporary inference assets."""
import hashlib
import json
import shutil
import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field
from fastapi import Response
from fastapi import Request
from fastapi.responses import FileResponse
from .errors import AppError
from .identity import user_id,owned

class SaveLook(BaseModel):
    job_id: uuid.UUID
    name: str = Field(min_length=1,max_length=80)
    consent: Literal[True]

class Looks:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.root = store.root / 'looks'
        if self.root.is_symlink(): raise ValueError('Saved look storage must not be a link')
        self.root.mkdir(exist_ok=True)
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS looks (id TEXT PRIMARY KEY, bytes INTEGER NOT NULL, record TEXT NOT NULL)')
        self.reconcile_orphans()

    def reconcile_orphans(self):
        with self.store.connect() as db: known={r['id'] for r in db.execute('SELECT id FROM looks')}
        for path in self.root.iterdir():
            try:
                if str(uuid.UUID(path.name))!=path.name:continue
            except ValueError:continue
            if path.name in known or not path.is_dir() or path.is_symlink() or time.time()-path.stat().st_mtime<self.settings.retention_seconds:continue
            resolved=path.resolve()
            if not resolved.is_relative_to(self.root.resolve()):continue
            if any(p.is_symlink() or not p.resolve().is_relative_to(resolved) for p in path.rglob('*')):continue
            shutil.rmtree(path)

    def listing(self,owner_id='local'):
        with self.store.connect() as db:
            rows = db.execute("SELECT bytes,record FROM looks WHERE COALESCE(json_extract(record,'$.owner_id'),'local')=? ORDER BY rowid DESC",(owner_id,)).fetchall()
        return {'looks':[json.loads(r['record']) for r in rows], 'used_bytes':sum(r['bytes'] for r in rows),
                'max_bytes':self.settings.saved_look_bytes,'max_looks':self.settings.saved_look_capacity}

    def directory(self, id):
        path = self.root / str(uuid.UUID(id))
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):
            raise AppError(409,'LOOK_LOCATION_CHANGED','The saved look location changed; its files were preserved.')
        return path

    def get(self, id):
        with self.store.connect() as db:
            row = db.execute('SELECT record FROM looks WHERE id=?',(id,)).fetchone()
        if row is None: raise AppError(404,'LOOK_NOT_FOUND','This saved look does not exist.')
        return json.loads(row['record'])

    def save(self, request,owner_id='local'):
        name = request.name.strip()
        if not name or any(ord(c)<32 for c in name):
            raise AppError(422,'INVALID_LOOK_NAME','Use a name with 1 to 80 visible characters.')
        job = self.store.get(str(request.job_id))
        if job.get('owner_id','local')!=owner_id:raise AppError(404,'JOB_NOT_FOUND','This job does not exist.')
        if job['assets_expired'] or job['expires_at'] and job['expires_at']<=time.time():
            raise AppError(410,'RESULT_EXPIRED','These temporary photos expired. Generate another preview to save it.')
        if job['state']!='complete' or job['upstream_active']:
            raise AppError(409,'RESULT_NOT_READY','Only a completed preview can be saved.')
        self.store.validate_inputs(job)
        source = self.store.directory(job['id'])
        hashes = {role+'.png':image['sha256'] for role,image in job['manifest']['images'].items()}
        hashes['result.png']=job['manifest']['result_sha256']
        files = {}
        for filename, expected in hashes.items():
            path = source / filename
            if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
                raise AppError(409,'RESULT_CHANGED','A preview asset location changed.')
            try:raw = path.read_bytes()
            except OSError as error:raise AppError(409,'RESULT_CHANGED','A preview asset is missing or unavailable.') from error
            if hashlib.sha256(raw).hexdigest()!=expected: raise AppError(409,'RESULT_CHANGED','A preview asset changed.')
            files[filename] = raw
        files['manifest.json'] = json.dumps(job['manifest'],indent=2).encode()
        size = sum(len(raw) for raw in files.values())
        id = str(uuid.uuid4()); destination = self.directory(id)
        record = {'id':id,'name':name,'category':job['category'],'seed':job['seed'],
                  'owner_id':owner_id,
                  'image_order':job['manifest'].get('image_order',['person','garment']),
                  'created_at':time.time(),'bytes':size,'hashes':hashes,'source_job_id':job['id']}
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            count, used = db.execute('SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM looks').fetchone()
            stored = sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file() and not p.is_symlink())
            if count>=self.settings.saved_look_capacity or max(used,stored)+size>self.settings.saved_look_bytes:
                raise AppError(429,'LOOK_STORAGE_FULL','Saved-look storage is full. Delete a saved look before saving another.')
            destination.mkdir()
            try:
                for filename, raw in files.items(): (destination/filename).write_bytes(raw)
                db.execute('INSERT INTO looks VALUES (?,?,?)',(id,size,json.dumps(record)))
            except Exception:
                # Only remove this newly created, contained directory; never existing looks.
                if destination.resolve().is_relative_to(self.root.resolve()) and not destination.is_symlink():shutil.rmtree(destination)
                raise
        return record

    def asset(self, id, filename):
        record = self.get(id); path = self.directory(id)/filename
        if filename not in record['hashes']:raise AppError(404,'REFERENCE_NOT_FOUND','This saved look has no photo for that role.')
        if (not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(self.directory(id).resolve())
                or hashlib.sha256(path.read_bytes()).hexdigest()!=record['hashes'][filename]):
            raise AppError(409,'LOOK_ASSET_UNAVAILABLE','A saved photo is missing or changed.')
        return FileResponse(path,media_type='image/png',headers={'Cache-Control':'no-store'},
                            filename=f'comfyfitter-look-{id}.png' if filename=='result.png' else None)

    def delete(self, id):
        self.get(id); path = self.directory(id)
        root = path.resolve()
        if path.exists():
            if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in path.rglob('*')):
                raise AppError(409,'LOOK_LOCATION_CHANGED','The saved look contains an external link; it was preserved.')
            shutil.rmtree(path)
        with self.store.connect() as db: db.execute('DELETE FROM looks WHERE id=?',(id,))

def register_looks(app):
    @app.get('/api/looks')
    async def listing(request:Request): return app.state.looks.listing(user_id(request))
    @app.post('/api/looks',status_code=201)
    async def save(body: SaveLook,request:Request): return app.state.looks.save(body,user_id(request))
    @app.get('/api/looks/{id}/result')
    async def result(id: uuid.UUID,request:Request):
        owned(app.state.looks.get(str(id)),request,'LOOK_NOT_FOUND')
        return app.state.looks.asset(str(id),'result.png')
    @app.get('/api/looks/{id}/inputs/{role}')
    async def source(id: uuid.UUID, role: Literal['person','garment','back','side','detail','outer'],request:Request):
        owned(app.state.looks.get(str(id)),request,'LOOK_NOT_FOUND')
        return app.state.looks.asset(str(id),role+'.png')
    @app.delete('/api/looks/{id}',status_code=204)
    async def delete(id: uuid.UUID,request:Request):
        owned(app.state.looks.get(str(id)),request,'LOOK_NOT_FOUND')
        app.state.looks.delete(str(id)); return Response(status_code=204)
