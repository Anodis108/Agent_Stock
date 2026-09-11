from __future__ import annotations

import cv2
import numpy as np
from api.helper.exception_handler import ExceptionHandler
from api.helper.exception_handler import ResponseMessage
from app.height_cal_pred import HeightInput
from app.height_cal_pred import HeightOutput
from app.height_cal_pred import HeightService
from common.logs import get_logger
from common.utils import get_settings
from fastapi import APIRouter
from fastapi import File
from fastapi import status
from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder

# Khởi tạo router
height_api = APIRouter(prefix='/v1')
logger = get_logger(__name__)
settings = get_settings()


@height_api.post(
    '/height',
    response_model=HeightOutput,  # Optional: dùng nếu muốn FastAPI auto gen schema
    responses={
        status.HTTP_200_OK: {
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.SUCCESS,
                        'info': {
                            'results': [170.2],
                        },
                    },
                },
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            'description': 'Bad Request',
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.BAD_REQUEST,
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
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            'description': 'Unprocessable Entity - Format is not supported',
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.UNPROCESSABLE_ENTITY,
                    },
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {
            'description': 'Destination Not Found',
            'content': {
                'application/json': {
                    'example': {
                        'message': ResponseMessage.NOT_FOUND,
                    },
                },
            },
        },
    },
)
async def predict_height(file: UploadFile = File(...)):
    exception_handler = ExceptionHandler(
        logger=logger.bind(), service_name=__name__,
    )

    try:
        logger.info(
            'Received height prediction request',
            extra={'file_name': file.filename},
        )
        contents = await file.read()

        nparr = np.frombuffer(contents, np.uint8)
        img_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_array is None:
            raise ValueError('Failed to decode image - result is None')
    except Exception as e:
        return exception_handler.handle_exception(
            err_msg=f'Error while reading and decoding file: {e}',
            extra={'file_name': file.filename},
        )

    # Initialize model
    try:
        logger.info(
            'Initializing HeightService model...',
            extra={'file_name': file.filename},
        )
        height_model = HeightService(settings=settings)
        logger.info(
            'HeightService model initialized successfully',
            extra={'file_name': file.filename},
        )
    except Exception as e:
        return exception_handler.handle_exception(
            f'Failed to initialize HeightService model: {e}',
            extra={'file_name': file.filename},
        )

    # Inference
    try:
        logger.info(
            'Running height prediction...',
            extra={'file_name': file.filename},
        )
        height_result = await height_model.process(
            inputs=HeightInput(
                image=img_array,
                img_name=file.filename,
            ),
        )
        api_output = HeightOutput(
            results=height_result.results,
            out_path=height_result.out_path,
        )
        logger.info('Height calculate prediction completed.')
        return exception_handler.handle_success(jsonable_encoder(api_output))

    except Exception as e:
        return exception_handler.handle_exception(
            f'Height prediction failed: {e}',
            extra={'file_name': file.filename},
        )
