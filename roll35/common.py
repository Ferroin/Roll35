# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Common functions used throughout the module.'''

from __future__ import annotations

import itertools
import logging
import random
import unicodedata

from collections.abc import Callable, Iterable, Mapping
from functools import lru_cache
from typing import Any, Generator, TypeGuard, TypeVar, cast, overload

from jaro import jaro_winkler_metric as jwm
from ruamel.yaml import YAML

from . import types
from .log import log_call

VERSION = (7, 2, 0)

yaml = YAML(typ='safe')
logger = logging.getLogger(__name__)

T = TypeVar('T')


async def ret_async(value: T) -> T:
    '''Simple async wrapper to directly return a value.

       This is used in a couple of places where we are passing around
       coroutines, but need to also be able to return explicit values
       instead of a full coroutine.'''
    return value


def ismapping(item: Any, /) -> TypeGuard[Mapping]:
    '''Quick type guard to check if something appears to be a mapping.

       This is not exhaustive, but is good enough for the type checking
       we need to do.'''
    try:
        item['']
    except KeyError:
        pass
    except Exception:
        return False

    return True


def bad_return(value: Any, /) -> str:
    '''Produce a log message indicating a bad return code, including call site info.

       This does not actually log the message, it simply returns the
       string to be used as the message.'''
    import inspect
    frame = inspect.getframeinfo(inspect.stack()[1][0])
    return f'Unexpected return code {value} at {frame.filename}:{frame.lineno}'


@lru_cache(maxsize=256)
def norm_string(string: str, /) -> str:
    '''Normalize a string.

       This utilizes a LRU cache to speed up repeated operations.'''
    return unicodedata.normalize('NFD', string).casefold()


@overload
def expand_weighted_list(items: Iterable[types.WeightedValue]) -> list[str]: ...


@overload
def expand_weighted_list(items: Iterable[types.Item]) -> list[types.Item]: ...


def expand_weighted_list(items: Iterable[types.WeightedValue] | Iterable[types.Item]) -> list[str] | list[types.Item]:
    '''Transform a list of items with weights into a list of items usable with random.choice().

       `items` must be either a list of roll35.types.WeightedValue
       instances or a list of roll35.types.item.BaseItem instances
       (or subclasses of instances).'''
    if all(map(lambda x: isinstance(x, types.WeightedValue), items)):
        return list(flatten([itertools.repeat(x.value, x.weight) for x in cast(Iterable[types.WeightedValue], items)]))
    elif all(map(lambda x: isinstance(x, types.item.BaseItem), items)):
        return list(flatten([itertools.repeat(x, x.weight) for x in cast(Iterable[types.Item], items)]))
    else:
        raise ValueError(items)


@overload
def make_weighted_entry(entry: Mapping[str, Any], *, costmult_handler: Callable[[types.Item], types.Item] = lambda x: x) -> types.WeightedValue: ...


@overload
def make_weighted_entry(entry: types.Item, *, costmult_handler: Callable[[types.Item], types.Item] = lambda x: x) -> types.Item: ...


def make_weighted_entry(
        entry: Mapping[str, Any] | types.Item,
        *,
        costmult_handler: Callable[[types.Item], types.Item] = lambda x: x) -> \
        types.WeightedValue | types.Item:
    '''Create a weighted item entry understandable by expand_weighted_list().

       costmult_handler is an optional callback that adds an appropriate
       costrange or cost entry to items that have a costmult property.'''
    if isinstance(entry, types.item.BaseItem) and entry.costmult is not None:
        entry = costmult_handler(entry)

    match entry:
        case {'weight': int(), 'value': str()}:
            return types.WeightedValue(**cast(Mapping[str, Any], entry))
        case item if isinstance(item, types.item.BaseItem):
            return item
        case _:
            raise ValueError(entry)

    # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
    #
    # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
    raise RuntimeError


@overload
def rnd(items: Iterable[types.WeightedValue], /) -> str | types.Ret: ...


@overload
def rnd(items: Iterable[types.Item], /) -> types.Item | types.Ret: ...


@overload
def rnd(items: Iterable[types.Rank], /) -> types.Rank | types.Ret: ...


@overload
def rnd(items: Iterable[types.Subrank], /) -> types.Subrank | types.Ret: ...


@overload
def rnd(items: Iterable[str], /) -> str | types.Ret: ...


def rnd(items: Iterable[types.WeightedValue] | Iterable[T], /) -> str | T | types.Ret:
    '''Select a random item from items.

       If the items are roll35.types.WeightedValue or roll35.types.Item instances, return one of their values
       based on their weights. Otherwise, act like random.choice(items).'''
    ret: str | T | types.Ret = types.Ret.NO_MATCH

    if not list(items):
        pass
    elif all(map(lambda x: isinstance(x, types.WeightedValue), items)):
        i1 = expand_weighted_list(cast(Iterable[types.WeightedValue], items))
        ret = random.choice(i1)  # nosec # Not used for crypto purposes
    else:
        i2 = cast(list[T], list(items))
        ret = random.choice(i2)  # nosec # Not used for crypto purposes

    return ret


def chunk(items: Iterable[T], /, *, size: int) -> Generator[list[T], None, None]:
    '''Split a list into chunks of a given size.

       The final chunk will be less than the requested size if the total
       number of items is not an exact multiple of the requested size.'''
    data = []

    for item in items:
        data.append(item)

        if len(data) == size:
            yield data
            data = []

    if data:
        yield data


def flatten(items: Iterable[Iterable[T]], /) -> Generator[T, None, None]:
    '''Flatten a list of lists.

       Only flattens one level.'''
    for i in items:
        for j in i:
            yield j


@log_call(logger, 'typo alternatives check')
def did_you_mean(items: list[str], name: str) -> types.Result[str]:
    '''Construct a message when an item is not found.

       This searches for items that fit one of four criteria:

       1. Items whose name starts with the specified name.
       2. Items whose name ends with the specified name.
       3. Items whose name contains the specified name.
       4. Items whose name is at least 80% similar to the specified name.

       The similarity check uses the Jaro-Winkler metric.

       The five highest ranking items are listed as possibilites
       if any are found, with prefix and suffix matches outranking
       substring matches, and substring matches outranking similar
       names.

       This is an expensive and computationally intensive operation,
       so it should be avoided in latency-sensitive contexts.'''
    possible = []

    for idx, item in enumerate(norm_string(x) for x in items):
        if item.startswith(name):
            possible.append((items[idx], 1.2))
        elif item.endswith(name):
            possible.append((items[idx], 1.2))
        elif name in item:
            possible.append((items[idx], 1.1))
        else:
            jaro = jwm(item, name)
            if jaro >= 0.8:
                possible.append((items[idx], jaro))

    if possible:
        possible1 = sorted(possible, key=lambda x: x[1], reverse=True)
        possible2 = [x[0] for x in possible1][0:5]
        possible3 = ', '.join(possible2)

        return (
            types.Ret.OK,
            f'Did you possibly mean one of: {possible3}'
        )
    else:
        return (types.Ret.NO_MATCH, 'No matching items found.')
