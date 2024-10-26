from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.bad_request_exception import BadRequestException
from app.exceptions.cameras_listener_exception import CamerasListenerException
from app.exceptions.conflict_request_exception import ConflictException
from app.exceptions.internal_error_exception import InternalErrorException
from app.exceptions.not_found_exception import NotFoundException
from app.exceptions.not_implemented_exception import NotImplementedException
from app.exceptions.reeds_listener_exception import ReedsListenerException
from app.exceptions.unupdateable_data_exception import UnupdateableDataException
from app.exceptions.validation_exception import ValidationException


async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={"message": exc.message},
    )

async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )

async def unupdateable_data_exception_handler(request: Request, exc: UnupdateableDataException):
    return JSONResponse(
        status_code=409,
        content={"message": exc.message},
    )

async def internal_error_exception_handler(request: Request, exc: InternalErrorException):
    return JSONResponse(
        status_code=500,
        content={"message": exc.message},
    )

async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )

async def cameras_listener_exception_handler(request: Request, exc: CamerasListenerException):
    return JSONResponse(
        status_code=500,
        content={"message": exc.message},
    )

async def reeds_listener_exception_handler(request: Request, exc: ReedsListenerException):
    return JSONResponse(
        status_code=500,
        content={"message": exc.message},
    )

async def not_implemented_exception_handler(request: Request, exc: NotImplementedException):
    return JSONResponse(
        status_code=501,
        content={"message": exc.message},
    )

async def conflict_exception_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=409,
        content={"message": exc.message},
    )

# This returns tuples of handler function name and exception type that it handles given all the functions in this file
# except obviously this one.
# Yeah, reflection bad, yadda yadda... but this only perform reflection on itself so there is no risk of other code
# breaking, and it is always implementable with a manual return of the list of tuples; I just find this easier than
# writing manually a potentially very long list and having to modify it every time I add a handler.
def get_exception_handlers():
    import inspect
    current_module = inspect.getmodule(inspect.currentframe())
    exception_handlers = []
    for name, func in inspect.getmembers(current_module, inspect.isfunction):
        if func.__name__ == 'get_exception_handlers':
            continue
        params = list(inspect.signature(func).parameters.values())
        if len(params) >= 2:
            exc_type = params[1].annotation
            if isinstance(exc_type, type) and issubclass(exc_type, Exception):
                exception_handlers.append((exc_type, func))
    return exception_handlers