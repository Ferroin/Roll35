# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Return values used by functions throughout the module.

   This exists to provide concise symbolic names for various expected
   return statuses that do not warrant exceptions so that return value
   checking is more clearly meaningful.'''

from __future__ import annotations

from typing import Literal, TypeVar

import enum


class Ret(enum.Enum):
    '''Enum of return values.

       Ret.OK indicates success.

       Ret.FAILED indicates a generic failure that does not warrant an
       exception, but is also not covered by more specific codes.

       Ret.NOT_READY indicates that required data was not ready.

       Ret.NO_MATCH indicates that no matching items were found.

       Ret.LIMITED indicates some internal limit was encountered.

       Ret.INVALID indicates invalid parameters were provided.'''
    OK = enum.auto()
    FAILED = enum.auto()
    NOT_READY = enum.auto()
    NO_MATCH = enum.auto()
    LIMITED = enum.auto()
    INVALID = enum.auto()


T = TypeVar('T')
Result = (
    tuple[Literal[Ret.OK], T] |
    tuple[Literal[
        Ret.FAILED,
        Ret.NOT_READY,
        Ret.NO_MATCH,
        Ret.LIMITED,
        Ret.INVALID,
    ], str]
)
