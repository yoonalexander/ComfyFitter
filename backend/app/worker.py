import asyncio
import copy
import hashlib
import json
import time
from io import BytesIO

import httpx
from PIL import Image

from .errors import AppError
from .settings import ROOT
from .references import References
from .comfy import same_graph


class Worker:
    def __init__(self, store, comfy, workflow, settings, cleanup,protection=None):
        self.store, self.comfy, self.workflow, self.settings = store, comfy, workflow, settings
        self.cleanup = cleanup
        self.protection=protection

    async def run(self):
        next_cleanup = time.monotonic() + self.settings.cleanup_interval_seconds
        while True:
            if time.monotonic() >= next_cleanup:
                self.cleanup.sweep()
                next_cleanup = time.monotonic() + self.settings.cleanup_interval_seconds
            pending = self.store.pending()
            if pending:
                job = next((j for j in pending if j.get('upstream_active')), pending[0])
                try:
                    await self.advance(job)
                except (httpx.HTTPError, ValueError, OSError):
                    # A transport failure proves neither rejection nor termination.
                    if job.get('upstream_active') and await self.recover_png(job):
                        continue
                    if job['submission'] == 'intent':
                        job['submission'] = 'uncertain'
                        job['stage'] = 'reconciling_submission'
                    elif job['state'] == 'queued':
                        job['stage'] = 'waiting_for_image_service'
                    else:
                        job['stage'] = 'reconnecting'
                    self.store.save(job)
                except AppError as error:
                    if error.code == 'INVALID_WORKFLOW' or job.get('execution_verified_terminal'):
                        job['upstream_active'] = False  # Native 400 definitively rejected submission.
                    job.update(state='failed', stage='failed',
                               error={'code': error.code, 'message': error.message},
                               expires_at=None if job['upstream_active'] else time.time() + self.settings.retention_seconds)
                    self.store.save(job)
            await asyncio.sleep(self.settings.poll_seconds)

    async def advance(self, job):
        if (job['state'] == 'processing' and job.get('started_at')
                and time.time() - job['started_at'] > self.settings.deadline_seconds):
            job.update(state='failed', stage='tracking_after_deadline',
                       error={'code': 'GENERATION_DEADLINE', 'message': 'Waiting deadline exceeded. GPU work is still being tracked.'})
            job['manifest']['deadline_exceeded'] = True
            self.store.save(job)
        if job['state'] == 'queued':
            queue = await self.comfy.queue()
            if queue['queue_running'] or queue['queue_pending']:
                return  # Respect evaluation jobs and other work already using this GPU.
            self.store.validate_inputs(job)
            config = self.workflow.config
            directory = self.store.directory(job['id'])
            uploaded_images={}
            for role in job['manifest']['images']:
                filename = f"cf_{job['id']}_{role}.png"
                asset = {'type': 'input', 'filename': filename,
                         'sha256': job['manifest']['images'][role]['sha256']}
                assets = job['manifest'].setdefault('upstream_assets', [])
                if asset not in assets:
                    assets.append(asset)  # Retain ownership even if upload acknowledgement is lost.
                self.store.save(job)
                uploaded = await self.comfy.upload(filename, (directory / f'{role}.png').read_bytes())
                uploaded_images[role]=uploaded
            graph=References.graph(self.workflow.graph,config,uploaded_images)
            graph[config['prompt_node']]['inputs']['prompt'] = job['manifest']['prompt']
            graph[config['sampler_node']]['inputs']['seed'] = job['seed']
            graph[config['output_node']]['inputs']['filename_prefix'] = f"cf_{job['id']}_result"
            encoded = json.dumps(graph, indent=2).encode()
            (directory / 'workflow.api.json').write_bytes(encoded)
            environment = json.loads((ROOT / 'evaluation/environment.json').read_text())
            job['manifest'].update(api_graph_sha256=hashlib.sha256(encoded).hexdigest(),
                prompt_template_hashes=self.workflow.prompt_hashes,
                environment_sha256=hashlib.sha256((ROOT / 'evaluation/environment.json').read_bytes()).hexdigest(),
                sampler=graph[config['sampler_node']]['inputs'], inference_environment=environment)
            # This durable intent precedes POST; restart never blindly resubmits it.
            job.update(state='processing', stage='submitting', submission='intent', started_at=time.time(), upstream_active=True)
            self.store.save(job)
            prompt_id = await self.comfy.submit(graph, job['id'])
            job.update(prompt_id=prompt_id, submission='acknowledged', stage='generating')
            self.store.save(job)
            return
        if not job.get('prompt_id'):
            graph = json.loads((self.store.directory(job['id']) / 'workflow.api.json').read_bytes())
            prompt_id = await self.comfy.find_submission(job['id'], graph)
            if prompt_id:
                job.update(prompt_id=prompt_id, submission='reconciled', stage='generating')
                self.store.save(job)
            else:
                await self.recover_png(job)
            return  # Absence from history never proves POST was rejected or inference stopped.
        history = await self.comfy.history(job['prompt_id'])
        if not history or not history.get('status', {}).get('completed'):
            if not history:
                await self.recover_png(job)
            return
        directory = self.store.directory(job['id'])
        graph = json.loads((directory / 'workflow.api.json').read_bytes())
        prompt = history.get('prompt')
        if not isinstance(prompt, list) or len(prompt) < 4 or prompt[1]!=job['prompt_id'] or not isinstance(prompt[3],dict) or prompt[3].get('client_id')!=job['id'] or not same_graph(prompt[2],graph):
            raise AppError(502, 'RESULT_MISMATCH', 'The image service result does not match this job.')
        job['execution_verified_terminal'] = True
        if history['status'].get('status_str') != 'success':
            raise AppError(502, 'INFERENCE_FAILED', 'The image service could not complete this generation.')
        outputs=history.get('outputs');node=outputs.get(self.workflow.config['output_node']) if isinstance(outputs,dict) else None
        images=node.get('images') if isinstance(node,dict) else None
        if not isinstance(images,list) or len(images)!=1 or not isinstance(images[0],dict):
            raise AppError(502, 'RESULT_MISSING', 'The image service did not return one result image.')
        image = images[0]
        if (image.get('type') != 'output' or image.get('subfolder', '') or
                not isinstance(image.get('filename'),str) or not image['filename'].startswith(f"cf_{job['id']}_result") or
                '/' in image['filename'] or '\\' in image['filename']):
            raise AppError(502, 'RESULT_MISMATCH', 'The image service returned an unexpected result location.')
        data = await self.comfy.output(image)
        await self.finish(job, data, image, history)

    async def recover_png(self, job):
        try:
            return await self._recover_png(job)
        except (ValueError, OSError, Image.DecompressionBombError):
            return False  # Missing/partial evidence never authorizes resubmission or deletion.

    async def _recover_png(self, job):
        directory = self.store.directory(job['id'])
        graph = json.loads((directory / 'workflow.api.json').read_bytes())

        def clean(value):
            return {key: {k: v for k, v in node.items() if k != 'is_changed'} for key, node in value.items()}

        for role in job['manifest']['images']:
            root = self.settings.comfy_input_dir.resolve()
            uploaded = (root / f"cf_{job['id']}_{role}.png").resolve()
            if not uploaded.is_relative_to(root) or not uploaded.exists():
                return False
            if hashlib.sha256(uploaded.read_bytes()).hexdigest() != job['manifest']['images'][role]['sha256']:
                return False
        root = self.settings.comfy_output_dir.resolve()
        matches = []
        for candidate in root.glob(f"cf_{job['id']}_result*.png"):
            if not candidate.resolve().is_relative_to(root) or candidate.stat().st_size > 40 * 1024 * 1024:
                continue
            try:
                with Image.open(candidate) as image:
                    embedded = json.loads(image.info.get('prompt', '{}'))
                    if clean(embedded) != clean(graph):
                        continue
                    if image.width * image.height > self.settings.max_image_pixels:
                        continue
                    image.load()
                matches.append(candidate)
            except (ValueError, OSError, TypeError, AttributeError):
                continue
        if len(matches) != 1:
            return False
        candidate = matches[0]
        job['manifest']['recovery'] = {'kind': 'png_embedded_graph',
            'note': 'Exact graph and uploaded input hashes verified. Original GPU timing is unavailable.'}
        job['execution_verified_terminal']=True
        await self.finish(job, candidate.read_bytes(), {'filename': candidate.name, 'subfolder': '', 'type': 'output'}, None)
        return True

    async def finish(self, job, data, image, history):
        directory = self.store.directory(job['id'])
        asset = {'type': 'output', 'filename': image['filename'], 'sha256': hashlib.sha256(data).hexdigest()}
        if asset not in job['manifest']['upstream_assets']:
            job['manifest']['upstream_assets'].append(asset)
        self.store.save(job)
        try:
            with Image.open(BytesIO(data)) as result:
                if result.format != 'PNG' or getattr(result, 'n_frames', 1) != 1:
                    raise AppError(502, 'RESULT_INVALID', 'The image service did not return a single PNG image.')
                if result.width * result.height > self.settings.max_image_pixels:
                    raise AppError(502, 'RESULT_TOO_LARGE', 'The image service returned excessive result dimensions.')
                result.load()
                size = list(result.size)
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            raise AppError(502, 'RESULT_INVALID', 'The completed preview could not be decoded. Try another preview.') from error
        if job['manifest'].get('protect_regions') and self.protection:
            job.update(state='processing',stage='protecting_source');self.store.save(job)
            data,metrics=await self.protection.apply(job,directory,data)
            job['manifest']['protection']=metrics
        (directory / 'result.png').write_bytes(data)
        if history:
            (directory / 'history.json').write_text(json.dumps(history))
        stamps = {}
        for message in history.get('status', {}).get('messages', []) if history else []:
            if (isinstance(message, (list, tuple)) and len(message) == 2
                    and isinstance(message[1], dict) and isinstance(message[1].get('timestamp'), (int, float))):
                stamps[message[0]] = message[1]['timestamp']
        finish_stamp = stamps.get('execution_success')
        gpu_seconds = ((finish_stamp - stamps['execution_start']) / 1000
                       if finish_stamp is not None and stamps.get('execution_start') is not None else None)
        job['manifest'].update(result_sha256=hashlib.sha256(data).hexdigest(),
                               output_size=size, upstream_result=image, prompt_id=job.get('prompt_id'),
                               gpu_execution_seconds=gpu_seconds,
                               retrieval_wall_seconds=time.time() - job['started_at'])
        (directory / 'manifest.json').write_text(json.dumps(job['manifest'], indent=2))
        job.update(state='complete', stage='complete', expires_at=time.time() + self.settings.retention_seconds,
                   upstream_active=False, error=None)
        self.store.save(job)
