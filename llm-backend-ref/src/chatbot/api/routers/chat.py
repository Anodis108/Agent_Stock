from __future__ import annotations

from api.helper.exception_handler import ExceptionHandler
from api.helper.exception_handler import ResponseMessage
from app.chat import ChatInput
from app.chat import ChatOutput
from app.chat import ChatService
from common.logs import get_logger
from common.utils import get_settings
from domain.service.optimization.cache import SemanticCache
from fastapi import APIRouter
from fastapi import status
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix='/chat', tags=['chat'])
logger = get_logger(__name__)
settings = get_settings()


@router.post(
    '/chat',
    response_model=ChatOutput,
    responses={
        status.HTTP_200_OK: {
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.SUCCESS,
                        'info': {'answer': '...', 'model': 'gpt-4o-mini'},
                    },
                },
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            'description': 'Internal Server Error',
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.INTERNAL_SERVER_ERROR,
                    },
                },
            },
        },
    },
)
async def chat_endpoint(req: ChatInput) -> ChatOutput:
    exception_handler = ExceptionHandler(
        logger=logger.bind(), service_name=__name__,
    )

    # Define application
    try:
        logger.info('Initializing ChatService...')
        chat_model = ChatService()
    except Exception as e:
        return exception_handler.handle_exception(
            f'Failed to initialize ChatService: {e}',
            extra={'question': req.question},
        )

    # Infer
    try:
        chat_result: ChatOutput = chat_model.process(inputs=req)
        return exception_handler.handle_success(jsonable_encoder(chat_result))
    except Exception as e:
        return exception_handler.handle_exception(
            f'Chat pipeline failed: {e}',
            extra={'question': req.question},
        )
