from __future__ import annotations

from enum import Enum
from typing import Optional

from common.bases import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse
from structlog.stdlib import BoundLogger


class ResponseMessage(str, Enum):
    INTERNAL_SERVER_ERROR = 'Server might meet some errors. Please try again later !!!'
    SUCCESS = 'Process successfully !!!'
    NOT_FOUND = 'Resource not found !!!'
    BAD_REQUEST = 'Invalid request !!!'
    UNPROCESSABLE_ENTITY = 'Input is not allowed !!!'


class ExceptionHandler(BaseModel):
    logger: BoundLogger
    service_name: str

    def _format_error(self, err_msg: str) -> str:
        return f'[{self.service_name}] error: {err_msg}'

    def _build_response(
        self,
        msg: str,
        payload: Optional[dict] = None,
        code: int = status.HTTP_200_OK,
    ) -> JSONResponse:
        """Create a response object

        Args:
            msg (str): message to be returned
            payload (Optional[dict], optional): data to be returned. Defaults to None.
            code (int, optional): status code of the response. Defaults to status.HTTP_200_OK.

        Returns:
            Response: response object
        """
        response_data = {'message': msg}
        if payload:
            response_data.update(payload)

        return JSONResponse(content=response_data, status_code=code)

    def handle_exception(self, err_msg: str, extra: dict) -> JSONResponse:
        """Handle exception

        Args:
            err_msg (str): exception message
            extra (dict): extra information

        Returns:
            Response: response object
        """
        self.logger.exception(err_msg, extra=extra)

        return self._build_response(
            ResponseMessage.INTERNAL_SERVER_ERROR.value,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def handle_not_found_error(self, err_msg: str, extra: dict) -> JSONResponse:
        """Handle not found error

        Args:
            err_msg (str): message
            extra (dict): extra information

        Returns:
            Response: response object
        """
        self.logger.error(err_msg, extra=extra)

        return self._build_response(
            ResponseMessage.NOT_FOUND.value,
            code=status.HTTP_404_NOT_FOUND,
        )

    def handle_success(self, result: dict) -> JSONResponse:
        """Handle success

        Args:
            result (dict): output

        Returns:
            Response: response object
        """
        data = {'info': result}

        return self._build_response(
            ResponseMessage.SUCCESS.value,
            payload=data,
            code=status.HTTP_200_OK,
        )

    def handle_bad_request(self, err_msg: str, extra: dict) -> JSONResponse:
        self.logger.error(err_msg, extra=extra)
        return self._build_response(
            ResponseMessage.BAD_REQUEST.value,
            code=status.HTTP_400_BAD_REQUEST,
        )

    def handle_unprocessable_entity(self, err_msg: str, extra: dict) -> JSONResponse:
        self.logger.error(err_msg, extra=extra)
        return self._build_response(
            ResponseMessage.UNPROCESSABLE_ENTITY.value,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
