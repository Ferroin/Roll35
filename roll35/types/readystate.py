# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''A simple mixin class for tracking readiness state for objects.'''

from __future__ import annotations

import asyncio
import logging

from typing import Any, ParamSpec, TypeVar, Literal, Concatenate, TYPE_CHECKING

from .retcode import Ret

if TYPE_CHECKING:
    from collections.abc import Coroutine, Callable

P = ParamSpec('P')
T = TypeVar('T')
RS = TypeVar('RS', bound='ReadyState')


class ReadyState:
    '''Mixin to add infrastructure to track readiness state for an object.'''
    READY_TIMEOUT: float | int = 5.0

    def __init__(self: ReadyState, /) -> None:
        self._ready = asyncio.Event()

    @property
    def ready(self: ReadyState, /) -> bool:
        return self._ready.is_set()

    @ready.setter
    def ready(self: ReadyState, state: bool, /) -> None:
        match state:
            case True:
                self._ready.set()
            case False:
                self._ready.clear()
            case _:
                raise ValueError


def check_ready_async(logger: logging.Logger, /) -> \
        Callable[
            [Callable[Concatenate[RS, P], Coroutine[Any, Any, T]]],
            Callable[Concatenate[RS, P], Coroutine[Any, Any, T | Literal[Ret.NOT_READY]]]
        ]:
    '''Decorate an async method to wait for it’s instance to be ready.

        The method must be part of a class that inherits from ReadyState.

        The maximum time to wait is specified by the READY_TIMEOUT
        class attribute on the class. If the timeout is exceeded,
        Ret.NOT_READY will be returned instead of calling the decorated
        method.'''
    def decorator(func: Callable[Concatenate[RS, P], Coroutine[Any, Any, T]]) -> \
            Callable[Concatenate[RS, P], Coroutine[Any, Any, T | Literal[Ret.NOT_READY]]]:
        async def inner(self: RS, *args: P.args, **kwargs: P.kwargs) -> T | Literal[Ret.NOT_READY]:
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=self.READY_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning('Timed out waiting for data to be ready.')
                return Ret.NOT_READY

            return await func(self, *args, **kwargs)

        return inner

    return decorator


def check_ready(logger: logging.Logger, /) -> \
        Callable[
            [Callable[Concatenate[RS, P], T]],
            Callable[Concatenate[RS, P], T | Literal[Ret.NOT_READY]]
        ]:
    '''Decorate an method to check if it’s instance is be ready.

        The method must be part of a class that inherits from ReadyState.

        Note that this does not wait for the instance to be ready,
        it returns immediately with Ret.NOT_READY if the instance is
        not ready.'''
    def decorator(func: Callable[Concatenate[RS, P], T]) -> \
            Callable[Concatenate[RS, P], T | Literal[Ret.NOT_READY]]:
        def inner(self: RS, *args: P.args, **kwargs: P.kwargs) -> T | Literal[Ret.NOT_READY]:
            if not self.ready:
                logger.warning('Data is not yet ready.')
                return Ret.NOT_READY

            return func(self, *args, **kwargs)

        return inner

    return decorator
