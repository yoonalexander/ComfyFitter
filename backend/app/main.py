from contextlib import asynccontextmanager
import asyncio
import time
import os
from contextlib import suppress
from typing import Literal

from fastapi import FastAPI, File, Form, UploadFile, Header, Request
from starlette.datastructures import UploadFile as MultipartFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .comfy import ComfyClient
from .settings import Settings, ROOT
from .errors import AppError
from .images import read_image
from .store import JobStore, public_job
from .workflow import Workflow
from .worker import Worker
from .cleanup import Cleanup
from .body_limit import BodyLimit
from .worker_lock import WorkerLock
from .local_access import LocalAccess
from .looks import Looks, register_looks
from .identity import Identity, IdentityAccess, user_id, scoped_key, owned
from .references import ROLES
from .conditional_coat_outfits import ConditionalCoatReferences as OutfitReferences
from .protection import Protection


def create_app(settings=None, *, transport=None, identity_transport=None,protection_adapter=None):
    settings = settings or Settings.from_env()
    identity = Identity(settings,identity_transport)

    @asynccontextmanager
    async def lifespan(app):
        with WorkerLock(settings.data_dir):
            app.state.comfy = ComfyClient(settings.comfy_url, transport=transport)
            task = None
            try:
                app.state.store = JobStore(settings)
                identity.store = app.state.store
                app.state.looks = Looks(app.state.store, settings)
                app.state.store.reconcile_queued_files()
                app.state.workflow = Workflow(settings)
                app.state.references = OutfitReferences(settings,app.state.workflow)
                app.state.protection = protection_adapter if protection_adapter is not None else Protection(settings,app.state.workflow)
                app.state.cleanup = Cleanup(app.state.store, settings)
                app.state.cleanup.sweep()
                worker = Worker(app.state.store, app.state.comfy, app.state.workflow, settings, app.state.cleanup,app.state.protection)
                task = asyncio.create_task(worker.run())
                yield
            finally:
                if task is not None:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
                await app.state.comfy.close()
                await identity.close()

    app = FastAPI(title='ComfyFitter', version='0.1.0', lifespan=lifespan)
    app.add_middleware(BodyLimit, limit=5 * settings.max_image_bytes + 64 * 1024)
    app.add_middleware(LocalAccess, allowed_origins=settings.allowed_origins,
                       public_origin=settings.public_origin if settings.deployment_mode=='hosted' else '')
    app.add_middleware(IdentityAccess,identity=identity)
    app.state.settings = settings

    @app.exception_handler(AppError)
    async def app_error(request, error):
        return JSONResponse(status_code=error.status,
                            content={'error': {'code': error.code, 'message': error.message}})

    @app.get('/api/health')
    async def health():
        return {'app': 'ok', 'application': 'comfyfitter', 'version': '0.1.0', 'process_id': os.getpid(),
                'deployment_mode': settings.deployment_mode,
                'comfyui': await app.state.comfy.readiness(app.state.workflow.graph),
                'supported_categories': app.state.workflow.supported,
                'reference_modes':app.state.references.modes,
                'spatial_protection_available':app.state.protection.available}

    @app.post('/api/try-on', status_code=202)
    async def try_on(request: Request, person: UploadFile = File(...), garment: UploadFile = File(...),
                     category: str = Form(...), seed: int = Form(0, ge=0, le=2**63-1),
                     back:UploadFile|None=File(None),side:UploadFile|None=File(None),detail:UploadFile|None=File(None),
                     outer:UploadFile|None=File(None),outer_category:str|None=Form(None),
                     protect_regions:bool=Form(False),
                     source_has_bag:bool=Form(False),
                     idempotency_key: str | None = Header(None, max_length=128)):
        form = await request.form()
        uploads={role:file for role,file in zip(ROLES,(person,garment,back,side,detail,outer)) if file is not None}
        if (any(len(form.getlist(role))>1 for role in ROLES)
                or sum(isinstance(value, MultipartFile) for _, value in form.multi_items()) != len(uploads)
                or len(uploads)>5):
            raise AppError(422, 'INVALID_REFERENCE_COUNT', 'Use one photo per reference role, with at most five photos including the person.')
        images = [await read_image(file, settings) for file in uploads.values()]
        plan=app.state.references.plan(category,uploads,outer_category,source_has_bag)
        if protect_regions and plan['mode']!='single_reference':raise AppError(422,'PROTECTION_MODE_UNSUPPORTED','Source protection is available only for one-reference previews.')
        if protect_regions and not app.state.protection.available:raise AppError(503,'PROTECTION_NOT_VALIDATED','Source protection has not passed its quality and runtime checks.')
        prompt = plan['prompt']
        manifest = {'version': 1, 'category': category, 'seed': seed, 'prompt': prompt,
                    'workflow_template_sha256': app.state.workflow.config['graph_sha256'],
                    'quality_manifest_sha256': app.state.workflow.quality_sha256,
                    'protect_regions':protect_regions,'protection_manifest_sha256':app.state.protection.report_hash if protect_regions else None,
                    **plan,
                    'images': {role: {k: v for k, v in image.items() if k != 'bytes'}
                               for role, image in zip(plan['image_order'], images)}}
        record = app.state.store.enqueue(category, seed, images, scoped_key(request,idempotency_key), manifest,owner_id=user_id(request))
        return public_job(record)

    @app.get('/api/try-on/{job_id}')
    async def job_status(job_id: str,request:Request):
        return public_job(owned(app.state.store.get(job_id),request))

    @app.get('/api/try-on/{job_id}/result')
    async def job_result(job_id: str,request:Request):
        record = owned(app.state.store.get(job_id),request)
        if record['expires_at'] and record['expires_at'] <= time.time() and not record['upstream_active']:
            record = app.state.cleanup.delete(record)
        if record['assets_expired']:
            raise AppError(410, 'RESULT_EXPIRED', 'This job’s temporary images were deleted.')
        if record['state'] != 'complete':
            raise AppError(409, 'RESULT_NOT_READY', 'This job has no completed result yet.')
        app.state.store.validate_result(record)
        return FileResponse(app.state.store.directory(job_id) / 'result.png',
                            media_type='image/png', filename=f'comfyfitter-{job_id}.png',
                            headers={'Cache-Control': 'no-store'})

    @app.delete('/api/try-on/{job_id}')
    async def delete_job(job_id: str,request:Request):
        record = owned(app.state.store.get(job_id),request)
        if record['state'] in ('queued', 'processing') or record['upstream_active']:
            raise AppError(409, 'JOB_ACTIVE', 'Images cannot be deleted while GPU work may still be active.')
        return public_job(app.state.cleanup.delete(record))

    @app.get('/api/try-on/{job_id}/inputs/{role}')
    async def job_input(job_id: str, role: Literal['person', 'garment','back','side','detail','outer'],request:Request):
        record = owned(app.state.store.get(job_id),request)
        if record['expires_at'] and record['expires_at'] <= time.time() and not record['upstream_active']:
            record = app.state.cleanup.delete(record)
        if record['assets_expired']:
            raise AppError(410, 'INPUT_EXPIRED', 'This job’s temporary images were deleted. Upload them again.')
        if role not in record['manifest']['images']:raise AppError(404,'REFERENCE_NOT_FOUND','This job has no photo for that reference role.')
        app.state.store.validate_inputs(record)
        return FileResponse(app.state.store.directory(job_id) / f'{role}.png', media_type='image/png',
                            headers={'Cache-Control': 'no-store'})

    @app.get('/api/submissions/{key}')
    async def submission_status(key: str,request:Request):
        if len(key) > 128:
            raise AppError(422, 'INVALID_REQUEST_KEY', 'The request key exceeds 128 characters.')
        return public_job(owned(app.state.store.by_request_key(scoped_key(request,key)),request))

    register_looks(app)
    frontend = ROOT / 'frontend/dist'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
    return app


app = create_app()
