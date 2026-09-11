from __future__ import annotations

import time

import structlog
from asgi_correlation_id.context import correlation_id
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from structlog.stdlib import BoundLogger
from uvicorn.protocols.utils import get_path_with_query_string


def truncate_body(content: bytes) -> bytes:
    """Truncate body when logging to avoid stressing path operations

    Args:
        content (bytes): request body

    Returns:
        bytes: truncated request body
    """

    def format_size(byte_size: int) -> str:
        if byte_size >= 1024 * 1024 * 1024:
            return f'{byte_size / (1024 * 1024 * 1024):.2f} GB'
        elif byte_size >= 1024 * 1024:
            return f'{byte_size / (1024 * 1024):.2f} MB'
        elif byte_size >= 1024:
            return f'{byte_size / 1024:.2f} KB'
        else:
            return f'{byte_size} bytes'

    if len(content) > 100:
        return content[:100] + f'... Truncated {format_size(len(content))}'.encode()
    return content


class LoggingMiddleware:
    def __init__(self, app: ASGIApp, logger: BoundLogger) -> None:
        self.app = app
        self.logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        structlog.contextvars.clear_contextvars()
        req_id = correlation_id.get()
        structlog.contextvars.bind_contextvars(request_id=req_id)

        start_time = time.perf_counter_ns()

        client_ip = None
        client_port = None
        if 'client' in scope:
            client_ip = scope['client'][0]
            client_port = scope['client'][1]
        req_url = get_path_with_query_string(scope)  # type: ignore
        req_method = scope['method']
        req_version = scope['http_version']
        req_body = b''
        res_status = 500
        duration = 0

        async def receive_log():
            nonlocal req_body
            req_msg = await receive()
            assert req_msg['type'] == 'http.request'
            req_body = truncate_body(req_msg['body'])
            return req_msg

        async def send_log(res_msg: Message) -> None:
            nonlocal start_time
            nonlocal duration
            nonlocal res_status
            duration = time.perf_counter_ns() - start_time
            if res_msg['type'] == 'http.response.start':
                res_status = res_msg['status']
                headers = MutableHeaders(scope=res_msg)
                headers.append(
                    key='X-Process-Time',
                    value=str(duration / 10**9),
                )
            await send(res_msg)

        try:
            await self.app(scope, receive_log, send_log)
        except Exception:
            structlog.stdlib.get_logger(
                'api.error',
            ).exception('Uncaught exception')
            raise
        finally:
            self.logger.info(
                f"{client_ip}:{client_port} - \"{req_method} {req_url} HTTP/{req_version}\" {res_status}",
                http={
                    'url': req_url,
                    'status_code': res_status,
                    'method': req_method,
                    'request_id': req_id,
                    'version': req_version,
                    'body': req_body,
                },
                duration=duration,
            )
