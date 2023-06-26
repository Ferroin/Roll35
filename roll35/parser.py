# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Provides basic command parameter parsing functionality.'''

from __future__ import annotations

import shlex

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import StringIO
from typing import Any, Callable, Generic, TypeVar

from .types import Result, Ret

T = TypeVar('T')


@dataclass
class ParserEntry(Generic[T]):
    '''Describes a parameter for a parser schema.

       `type` is a callable that transforms a string into the required
       parameter type.

       `name` is a sequence of strings that define what names to recognize
       for the parameter.

       `default` defines the default value to return for the parameter
       if it was not specified by the user.'''
    type: Callable[[str], T]
    names: Sequence[str]
    default: T | None


class Parser:
    '''A simple class for parsing commands into a dictionary.

       Takes a schema consisting of a mapping of strings to
       roll35.parser.ParserEntry instances.

       Behavior if a schema contains multiple parameters that have the
       same name is undefined.'''
    def __init__(self: Parser, schema: Mapping[str, ParserEntry], /):
        self._schema = schema
        self._rindex = dict()

        for key in schema.keys():
            for name in schema[key].names:
                self._rindex[name] = key

    def parse(self: Parser, data: str, /) -> Result[dict[str, Any]]:
        '''Parse a string using the schema.

           Returns either a tuple of roll35.types.Ret.OK and the
           dictionary produced by the parser, or roll35.types.Ret.FAILED
           and an error message.'''
        ret: dict[str, Any] = {k: v.default for k, v in self._schema.items()}

        lexer = shlex.shlex(StringIO(data), posix=True)

        while True:
            match lexer.get_token():
                case lexer.eof:
                    return (Ret.OK, ret)
                case token if token is not None and token.casefold() in self._rindex:
                    key = self._rindex[token]
                    value = lexer.get_token()
                    schema = self._schema[key]

                    if value == lexer.eof:
                        return (Ret.FAILED, f'Unexpected end of arguments after `{token}`.')
                    elif value is None:
                        return (Ret.FAILED, 'Failed to parse arguments, Unknown internal error.')

                    try:
                        ret[key] = schema.type(value.casefold())
                    except Exception:
                        return (Ret.FAILED, f'Failed to parse `{value}` as value for `{token}`.')
                case token:
                    return (Ret.FAILED, f'Unrecognized token `{token}`.')
