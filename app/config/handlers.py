from fastapi.responses import JSONResponse
from fastapi import Request
from .exceptions import NotFoundException, BadRequestException

async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found"},
    )

async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return JSONResponse(
        status_code=400,
        content={"message": "Bad request"},
    )
