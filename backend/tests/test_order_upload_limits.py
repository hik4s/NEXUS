import asyncio

from app.core.upload_limits import BoundedUploadMiddleware


def test_upload_is_stopped_before_multipart_processing_without_content_length():
    calls = 0
    downstream_called = False
    responses = []
    async def receive():
        nonlocal calls
        calls += 1
        return {'type': 'http.request', 'body': b'x'*8, 'more_body': True}
    async def send(message):
        responses.append(message)
    async def app(scope, receive, send):
        nonlocal downstream_called
        downstream_called = True
    scope = {'type': 'http', 'method': 'POST', 'path': '/api/v1/order-imports', 'headers': []}
    asyncio.run(BoundedUploadMiddleware(app, path='/api/v1/order-imports', max_body_bytes=16)(scope, receive, send))
    assert calls == 3 and not downstream_called
    assert responses[0]['status'] == 413


def test_bounded_body_is_replayed_exactly_and_other_routes_stream():
    responses = []
    parts = iter([{'type': 'http.request', 'body': b'abc', 'more_body': True},
                  {'type': 'http.request', 'body': b'def', 'more_body': False}])
    async def receive():
        return next(parts)
    async def send(message):
        responses.append(message)
    async def app(scope, receive, send):
        body = b''
        while True:
            message = await receive()
            body += message.get('body', b'')
            if not message.get('more_body'):
                break
        assert body == b'abcdef'
    scope = {'type': 'http', 'method': 'POST', 'path': '/api/v1/order-imports', 'headers': []}
    asyncio.run(BoundedUploadMiddleware(app, path=scope['path'], max_body_bytes=6)(scope, receive, send))

    untouched = []
    async def streaming_app(scope, original_receive, send):
        untouched.append(original_receive is receive)
    scope['path'] = '/api/v1/sales/orders'
    asyncio.run(BoundedUploadMiddleware(streaming_app, path='/api/v1/order-imports', max_body_bytes=6)(scope, receive, send))
    assert untouched == [True]
