# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Extra functions and classes for supporting logging.'''

from __future__ import annotations

import contextlib
import logging
import time

from typing import Callable, TypeVar, ParamSpec, Awaitable

T = TypeVar('T')
P = ParamSpec('P')


class LogRun(contextlib.AbstractContextManager, contextlib.AbstractAsyncContextManager):
    '''Log entry and exit for a block of code.

       Logging is done at the DEBUG level.

       Takes two parameters, the logger instance to use, and the message
       to use for the section of code.

       This is usable as either a regular context manager, or an async
       context manager.'''
    def __init__(self: LogRun, logger: logging.Logger, level: int, msg: str) -> None:
        self.level = level
        self.logger = logger
        self.msg = msg

    def __enter__(self: LogRun) -> LogRun:
        self.logger.log(self.level, f'Starting: { self.msg }')
        return self

    def __exit__(self: LogRun, *_args) -> None:
        self.logger.log(self.level, f'Finished: { self.msg }')
        return None

    async def __aenter__(self: LogRun) -> LogRun:
        return self.__enter__()

    async def __aexit__(self: LogRun, *_args) -> None:
        return self.__exit__()


def log_call(logger: logging.Logger, msg: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    '''Decorate a function to log calls to that function.

       Function arguments are logged on entry, and the return value is
       logged on exit.'''
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        def inner(*args, **kwargs) -> T:
            seq = time.monotonic_ns()
            logger.debug(f'{ msg }, seq: { seq }, called with: { args } and { kwargs }')
            ret = func(*args, **kwargs)
            logger.debug(f'{ msg }, seq: { seq }, returned: { ret }')
            return ret

        return inner

    return decorator


def log_call_async(logger: logging.Logger, msg: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    '''Decorate an async function to log calls to that function.

       Function arguments are logged on entry, and the return value is
       logged on exit.'''
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        async def inner(*args, **kwargs) -> T:
            seq = time.monotonic_ns()
            logger.debug(f'{ msg }, seq: { seq }, called with: { args } and { kwargs }')
            ret = await func(*args, **kwargs)
            logger.debug(f'{ msg }, seq: { seq }, returned: { ret }')
            return ret

        return inner

    return decorator
