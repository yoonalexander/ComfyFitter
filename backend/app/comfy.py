import httpx
from .errors import AppError

def same_graph(actual,expected):
    def clean(graph):
        if not isinstance(graph,dict) or any(not isinstance(node,dict) for node in graph.values()):return None
        return {key:{k:v for k,v in node.items() if k!='is_changed'} for key,node in graph.items()}
    canonical=clean(expected)
    return canonical is not None and clean(actual)==canonical


class ComfyClient:
    """Own the external inference HTTP boundary; browser clients never access it."""

    def __init__(self, base_url, *, transport=None):
        self.http = httpx.AsyncClient(base_url=base_url.rstrip('/'), timeout=5, transport=transport)

    async def readiness(self, graph=None):
        reachable = False
        try:
            response = await self.http.get('/system_stats')
            response.raise_for_status()
            stats = response.json()
            reachable = True
            if not isinstance(stats, dict) or not isinstance(stats.get('system'), dict):
                raise ValueError('Invalid inference system information')
            if graph is not None:
                response = await self.http.get('/object_info')
                response.raise_for_status()
                catalog = response.json()
                if not isinstance(catalog, dict):
                    raise ValueError('Invalid inference node catalog')
                required = {node['class_type'] for node in graph.values()}
                missing = sorted(required - catalog.keys())
                models = []
                for node in graph.values():
                    for field in ('unet_name', 'clip_name', 'vae_name'):
                        if field not in node['inputs']:
                            continue
                        options = catalog.get(node['class_type'], {}).get('input', {}).get('required', {}).get(field, [])
                        choices = options[0] if options and isinstance(options[0], list) else []
                        if node['inputs'][field] not in choices:
                            models.append(node['inputs'][field])
                if missing or models:
                    return {'ready': False, 'reachable': True, 'error': {
                        'code': 'COMFYUI_NOT_CONFIGURED',
                        'message': 'Install the configured workflow nodes and model files before generating.',
                        'missing_nodes': missing, 'missing_models': sorted(set(models))}}
            return {'ready': True, 'reachable': True, 'error': None}
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return {'ready': False, 'reachable': reachable, 'error': {
                'code': 'COMFYUI_READINESS_UNAVAILABLE' if reachable else 'COMFYUI_OFFLINE',
                'message': 'The local image service readiness could not be verified.'}}

    async def close(self):
        await self.http.aclose()

    async def queue(self):
        response = await self.http.get('/queue')
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get('queue_running'), list) or not isinstance(data.get('queue_pending'), list):
            raise ValueError('Invalid inference queue response')
        return data

    async def upload(self, filename, data):
        response = await self.http.post('/upload/image', files={'image': (filename, data, 'image/png')},
                                        data={'type': 'input', 'overwrite': 'true'})
        response.raise_for_status()
        uploaded = response.json()
        if not isinstance(uploaded, dict) or uploaded.get('name') != filename or uploaded.get('subfolder', '') or uploaded.get('type') != 'input':
            raise AppError(502, 'INVALID_UPLOAD_RESPONSE', 'The image service returned an unexpected upload location.')
        return filename

    async def submit(self, graph, client_id):
        response = await self.http.post('/prompt', json={'prompt': graph, 'client_id': client_id})
        if response.status_code == 400:
            raise AppError(422, 'INVALID_WORKFLOW', 'The image service rejected the configured workflow.')
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get('node_errors') or not isinstance(result.get('prompt_id'), str) or not result['prompt_id']:
            raise ValueError('Invalid inference submission acknowledgement')
        return result['prompt_id']

    async def history(self, prompt_id):
        response = await self.http.get('/history/' + prompt_id)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError('Invalid inference history response')
        history = data.get(prompt_id)
        if history is not None and (not isinstance(history, dict) or not isinstance(history.get('status'), dict)):
            raise ValueError('Invalid inference execution status')
        return history

    async def find_submission(self, client_id, graph):
        def matches(prompt):
            return (isinstance(prompt, list) and len(prompt) >= 4 and same_graph(prompt[2],graph)
                    and isinstance(prompt[3], dict) and prompt[3].get('client_id') == client_id)

        queue = await self.queue()
        found = {p[1] for p in queue['queue_running'] + queue['queue_pending'] if matches(p)}
        response = await self.http.get('/history', params={'max_items': 200})
        response.raise_for_status()
        histories = response.json()
        if not isinstance(histories, dict) or any(not isinstance(h, dict) for h in histories.values()):
            raise ValueError('Invalid inference reconciliation response')
        found.update(prompt_id for prompt_id, history in histories.items()
                     if matches(history.get('prompt')))
        if len(found) > 1:
            raise ValueError('Multiple upstream prompts match one job; manual reconciliation required')
        return next(iter(found), None)

    async def output(self, image):
        async with self.http.stream('GET', '/view', params=image) as response:
            response.raise_for_status()
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > 40 * 1024 * 1024:
                    raise AppError(502, 'RESULT_TOO_LARGE', 'The image service returned an oversized result.')
        return bytes(data)
