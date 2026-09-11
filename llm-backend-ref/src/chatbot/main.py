from __future__ import annotations

from api.helper import LoggingMiddleware
from api.routers.chat import router as chat_api
from api.routers.height_cal_pred import height_api
from asgi_correlation_id import CorrelationIdMiddleware
from common.logs import get_logger
from common.logs import setup_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from api.routers.sign_up import sign_up_endpoint

setup_logging(json_logs=False)
logger = get_logger('api')

app = FastAPI(title='Chatbot API', version='2.0.0')


# add middleware to generate correlation id
app.add_middleware(LoggingMiddleware, logger=logger)
app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(
    height_api,
)
app.include_router(
    chat_api,
)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=5001, reload=True)
