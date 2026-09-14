from __future__ import annotations

from fastapi import APIRouter
from fastapi import status
from fastapi.encoders import jsonable_encoder

from src.chatbot.api.helper.exception_handler import ExceptionHandler
from src.chatbot.api.helper.exception_handler import ResponseMessage
from src.chatbot.app.chat import ChatInput
from src.chatbot.app.chat import ChatOutput
from src.chatbot.app.chat import ChatService
from src.chatbot.common.logs import get_logger
from src.chatbot.common.utils import get_settings

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
