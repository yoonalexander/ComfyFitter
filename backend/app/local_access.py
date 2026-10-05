from urllib.parse import urlsplit

from starlette.responses import JSONResponse


class LocalAccess:
    """Protect the loopback application from browser cross-origin and DNS-rebinding requests."""
    def __init__(self, app, allowed_origins, public_origin=''):
        self.app, self.allowed_origins = app, set(allowed_origins)
        self.public_origin=public_origin

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {k.decode('latin1').lower(): v.decode('latin1') for k, v in scope['headers']}
        host = headers.get('host', '')
        try:
            local_host = urlsplit('//' + host).hostname in ('localhost', '127.0.0.1', '::1')
        except ValueError:
            local_host = False
        origin = headers.get('origin')
        same_origin = origin == scope.get('scheme', 'http') + '://' + host
        foreign_origin = origin is not None and not same_origin and origin not in self.allowed_origins
        if self.public_origin:
            local_host = host == urlsplit(self.public_origin).netloc
            # Direct loopback health probes are read-only; public API still requires a token.
            if scope['path']=='/api/health' and host in ('127.0.0.1','localhost','127.0.0.1:8000'):local_host=True
            foreign_origin=origin is not None and origin!=self.public_origin
        if not local_host or foreign_origin:
            return await JSONResponse(status_code=403, content={'error': {
                'code': 'LOCAL_ACCESS_DENIED', 'message': 'Open ComfyFitter through its local application address.'}})(scope, receive, send)
        await self.app(scope, receive, send)
