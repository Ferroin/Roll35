# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Common functions used throughout the module.'''

import asyncio
import itertools
import logging
import random
import unicodedata

from functools import lru_cache
from pathlib import Path

from jaro import jaro_winkler_metric as jwm
from ruamel.yaml import YAML

DATA_ROOT = Path(__file__).parent / 'data' / 'files'

VERSION = (3, 3, 0)

READINESS_TIMEOUT = 5.0

yaml = YAML(typ='safe')
logger = logging.getLogger(__name__)


async def prepare_cog(cog):
    '''Load any data needed for the cog.'''
    await cog.load_agent_data()


@lru_cache(maxsize=256)
def norm_string(string):
    '''Normalize a string.

       This utilizes a LRU cache to speed up repeated operations.'''
    return unicodedata.normalize('NFD', string).casefold()


def get_item_value(item):
    match item:
        case {'value': value}:
            return value
        case _:
            return {k: v for (k, v) in item.items() if k != 'weight'}


def expand_weighted_list(items):
    ret = []

    for item in items:
        ret.extend(itertools.repeat(
            get_item_value(item),
            item['weight']
        ))

    return ret


def rnd(items):
    '''Select a random item from a list of items.

       If the list is a list of dicts with `weight` and `value` keys, then
       we make a weighted selection based on that info and return the
       value. Otherwise, this is the same as `random.choice(items)`.'''
    match items:
        case [{'weight': _, 'value': _}, *_]:
            return random.choice(expand_weighted_list(items))
        case _:
            return random.choice(list(items))


def chunk(items, size):
    '''Split a list into chunks.'''
    data = []

    for item in items:
        data.append(item)

        if len(data) == size:
            yield data
            data = []

    if data:
        yield data


def flatten(items):
    '''Flatten a list of lists.'''
    for i in items:
        for j in i:
            yield j


def did_you_mean(items, name, flat_items=False):
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
       names.'''
    possible = []

    if not flat_items:
        items = [x['name'] for x in items]

    logger.debug(f'Evaluating possible typos for { name } in { items }')

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
        possible = sorted(possible, key=lambda x: x[1], reverse=True)
        possible = [x[0] for x in possible][0:5]
        possible = ', '.join(possible)

        return (
            True,
            f'Did you possibly mean one of: { possible }'
        )
    else:
        return (False, 'No matching items found.')


def check_ready(func):
    '''Decorate an async method to wait for it’s instance to be ready.

       This expects the instance to have an asyncio.Event() object under
       the _ready property that will be set when the instance is ready
       for methods with this decorator to run.

       The decorated method will wait up to
       `roll35.common.READINESS_TIMEOUT` seconds for the event to
       be set before running the method. If it times out while waiting,
       it will log a warning and return `False`.'''
    async def f(self, *args, **kwargs):
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=READINESS_TIMEOUT)
        except asyncio.TimeoutError:
            self.logger.warning('Timed out waiting for data to be ready.')
            return False

        return await func(self, *args, **kwargs)

    return f
