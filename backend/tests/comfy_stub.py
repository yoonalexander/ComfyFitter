"""Controlled external HTTP service; no network or GPU inference in API tests."""
import json
from email.parser import BytesParser

import httpx


class ComfyService:
    def __init__(self):
        self.submissions = []
        self.finished = False
        self.input_dir = None
        self.output_dir = None

    def __call__(self, request):
        path = request.url.path
        if path == '/upload/image':
            message = BytesParser().parsebytes(('Content-Type: ' + request.headers['content-type'] + '\r\n\r\n').encode() + request.read())
            part = next(p for p in message.walk() if p.get_filename())
            if self.input_dir:
                (self.input_dir / part.get_filename()).write_bytes(part.get_payload(decode=True))
            return httpx.Response(200, json={'name': part.get_filename(), 'subfolder': '', 'type': 'input'})
        if path == '/queue':
            running = [] if not self.submissions or self.finished else [self.prompt()]
            return httpx.Response(200, json={'queue_running': running, 'queue_pending': []})
        if path == '/prompt':
            self.submissions.append(json.loads(request.read()))
            return httpx.Response(200, json={'prompt_id': 'controlled-prompt', 'node_errors': {}})
        if path.startswith('/history'):
            history = {} if not self.finished else {'controlled-prompt': {
                'prompt': self.prompt(), 'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'461': {'images': [{'filename': 'cf_' + self.submissions[0]['client_id'] + '_result.png',
                                              'subfolder': '', 'type': 'output'}]}}}}
            return httpx.Response(200, json=history)
        if path == '/view':
            from .test_api import image_bytes
            if self.output_dir:
                (self.output_dir / request.url.params['filename']).write_bytes(image_bytes())
            return httpx.Response(200, content=image_bytes())
        raise AssertionError('Unexpected ComfyUI request: ' + path)

    def prompt(self):
        data = self.submissions[0]
        return [0, 'controlled-prompt', data['prompt'], {'client_id': data['client_id']}, ['461']]
