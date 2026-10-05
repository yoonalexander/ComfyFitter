from starlette.responses import JSONResponse


class BodyLimit:
    """Bound multipart bytes before parsing or disk spooling, including chunked input."""
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/try-on':
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > self.limit:
                response = JSONResponse(status_code=413, content={'error': {
                    'code': 'REQUEST_TOO_LARGE', 'message': 'The total upload exceeds the request limit.'}})
                return await response(scope, receive, send)
            if not message.get('more_body', False):
                break
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
