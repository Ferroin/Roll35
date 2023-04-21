'''Common functions used throughout the module.'''

import itertools
import random
import unicodedata

from functools import lru_cache
from pathlib import Path

from ruamel.yaml import YAML

DATA_ROOT = Path(__file__).parent / 'data' / 'files'

yaml = YAML(typ='safe')


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
