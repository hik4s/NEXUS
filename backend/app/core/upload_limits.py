"""Bound upload bodies before Starlette can spool multipart files to disk."""
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BoundedUploadMiddleware:
    def __init__(self, app: ASGIApp, *, path: str, max_body_bytes: int):
        self.app = app
        self.path = path
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'].rstrip('/') != self.path:
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > self.max_body_bytes:
                await JSONResponse(status_code=413, content={'detail': {
                    'code': 'upload_body_too_large', 'message': 'O corpo do upload excede o limite permitido.'}}
                )(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get('more_body', False):
                break

        replayed = False
        async def bounded_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, bounded_receive, send)
