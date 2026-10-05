"""Single-owner research gateway behind an email-protected Cloudflare Quick Tunnel.

Never expose this directly. cloudflared must use one exact --allowed-mail and the
per-launch private --http-host-header from the ignored configuration file.
"""
import contextlib
import hmac
import json
import os
import re
import sqlite3
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

ROOT = Path(__file__).resolve().parents[1]
MAX_BODY = 50 * 1024 * 1024 + 65536
MAX_RESULT = 40 * 1024 * 1024
ID = r'[a-fA-F0-9-]{36}'
ROUTES = {
    'GET': re.compile(r'/(?:|assets/[A-Za-z0-9._-]+|api/health|api/looks|api/looks/'+ID+r'(?:/result|/inputs/person)?|api/try-on/'+ID+r'(?:/result|/inputs/(?:person|garment|back|side|detail|outer))?|api/submissions/[A-Za-z0-9_-]{1,128})\Z'),
    'POST': re.compile(r'/api/(?:try-on|looks)\Z'),
    'DELETE': re.compile(r'/api/(?:try-on|looks)/'+ID+r'\Z'),
}

def valid_origin(value):
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', url.netloc)
                and not url.path and not url.query and not url.fragment)
    except ValueError:
        return False

def create_gateway(config_path, transport=None):
    config_path = Path(config_path)
    config = json.loads(config_path.read_text())
    secret_host = config['private_host']
    if not re.fullmatch(r'[a-f0-9]{64}\.localhost', secret_host):
        raise ValueError('A random private connector host is required')
    upstream = config.get('upstream', 'http://127.0.0.1:8000')
    if upstream != 'http://127.0.0.1:8000':
        raise ValueError('Only the existing loopback application may be proxied')
    attempts_path = config_path.with_name('limits.sqlite3')
    with sqlite3.connect(attempts_path) as database:
        database.execute('CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, day INTEGER NOT NULL)')
    requests = deque()

    def denied(status, code, message):
        return JSONResponse({'error': {'code': code, 'message': message}}, status_code=status,
                            headers={'Cache-Control': 'no-store'})

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(transport=transport, timeout=30, follow_redirects=False,
                                   trust_env=False) as client:
            app.state.client = client
            yield

    async def proxy(request: Request):
        if not hmac.compare_digest(request.headers.get('host', ''), secret_host):
            return denied(403, 'CONNECTOR_REQUIRED', 'Use the protected fitting room link.')
        # Until the authenticated tunnel hostname is recorded, all requests fail closed.
        current = json.loads(config_path.read_text())
        origin = current.get('public_origin', '')
        if not valid_origin(origin):
            return denied(503, 'CONNECTION_PENDING', 'The protected connection is not ready.')
        given_origin = request.headers.get('origin')
        if (given_origin is not None and given_origin != origin
                or request.method not in ('GET', 'HEAD') and given_origin != origin):
            return denied(403, 'ORIGIN_DENIED', 'Open the fitting room through its protected link.')
        method = 'GET' if request.method == 'HEAD' else request.method
        allowed = ROUTES.get(method)
        if not allowed or not allowed.fullmatch(request.url.path) or request.url.query:
            return denied(404, 'NOT_FOUND', 'This address is not available.')
        now = time.monotonic()
        while requests and requests[0] <= now-60:
            requests.popleft()
        if len(requests) >= 120:
            return denied(429, 'REQUEST_RATE_LIMIT', 'Wait a minute before trying again.')
        requests.append(now)
        body = bytearray()
        async for chunk in request.stream():
            if len(body)+len(chunk) > MAX_BODY:
                return denied(413, 'UPLOAD_TOO_LARGE', 'The combined photo upload is too large.')
            body.extend(chunk)
        if request.method == 'POST' and request.url.path == '/api/try-on':
            key = request.headers.get('idempotency-key', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
                return denied(422, 'REQUEST_KEY_REQUIRED', 'Refresh the page before generating a preview.')
            # Persist the single owner's ten-attempt UTC daily limit; retries retain their key.
            with sqlite3.connect(attempts_path) as database:
                database.execute('BEGIN IMMEDIATE')
                if not database.execute('SELECT 1 FROM attempts WHERE key=?', (key,)).fetchone():
                    day = int(time.time()//86400)
                    count = database.execute('SELECT COUNT(*) FROM attempts WHERE day=?', (day,)).fetchone()[0]
                    if count >= 10:
                        return denied(429, 'DAILY_GENERATION_LIMIT', 'Ten new previews per UTC day are allowed. Try again tomorrow.')
                    database.execute('INSERT INTO attempts VALUES (?,?)', (key, day))
        headers = {key: request.headers[key] for key in ('accept', 'content-type', 'idempotency-key') if key in request.headers}
        headers.update(host='127.0.0.1:8000', origin=upstream)
        try:
            async with request.app.state.client.stream(request.method, upstream+request.url.path,
                                                       headers=headers, content=bytes(body)) as result:
                content = bytearray()
                async for chunk in result.aiter_bytes():
                    if len(content)+len(chunk) > MAX_RESULT:
                        return denied(502, 'RESULT_TOO_LARGE', 'The preview could not be transferred safely.')
                    content.extend(chunk)
                response_headers = {key: result.headers[key] for key in ('content-type', 'content-disposition') if key in result.headers}
                response_headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                         'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY'})
                if request.url.path == '/api/health' and result.status_code == 200:
                    health = json.loads(content)
                    health['deployment_mode'] = 'hosted'
                    health.pop('process_id', None)
                    content = json.dumps(health).encode()
                return Response(bytes(content), status_code=result.status_code, headers=response_headers)
        except (httpx.HTTPError, ValueError):
            return denied(503, 'APPLICATION_UNAVAILABLE', 'The GPU PC application is unavailable. Try again when it is running.')

    return Starlette(routes=[Route('/{path:path}', proxy, methods=['GET','HEAD','POST','DELETE','PUT','PATCH','OPTIONS'])], lifespan=lifespan)

def application():
    return create_gateway(os.environ.get('COMFYFITTER_WEB_CONFIG', ROOT / '.local/web/config.json'))
