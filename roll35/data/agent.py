# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions and classes for accessing item data.

   Data agents are used to encapsulate the data processed from our data
   files, as well as providing the baasic functions needed by the bot
   code to work with that data. '''

import asyncio
import logging
import random

from . import types
from ..common import check_ready, norm_string, rnd, did_you_mean, make_weighted_entry

logger = logging.getLogger(__name__)


def process_compound_itemlist(items, costmult_handler=lambda x: x):
    '''Process a compound list of weighted values.

       Each list entry must be a dict with keys coresponding to the
       possible values for `roll35.data.types.RANK` with each such key
       bearing a weight to use for the entry when rolling a random item
       of the corresponding rank.'''
    ret = types.R35Map()

    for rank in types.RANK:
        ilist = types.R35List()

        for item in items:
            if item[rank]:
                ilist.append({
                    'weight': item[rank],
                    'value': costmult_handler({k: v for k, v in item.items() if k != 'weight'})
                })

        ret[rank] = ilist

    return ret


def process_ranked_itemlist(items, xform=lambda x: x):
    '''Process ranked list of weighted values.

       This takes a dict of ranks to dicts of subranks to lists of dicts
       of weighted items, and processes them into the format used by
       our weighted random selection in various data agent modules.'''
    ret = types.R35Map()
    ranks = types.RANK

    if types.RANK[0] not in items:
        ranks = types.LIMITED_RANK

    for rank in ranks:
        ret[rank] = process_subranked_itemlist(items[rank], xform)

    return ret


def process_subranked_itemlist(items, xform=lambda x: x):
    '''Process a subranked list of weighted values.

       This takes a dict of subranks to lists of dicts of weighted items
       and processes them into the format used by our weighted random
       selection in various data agent modules.'''
    ret = types.R35Map()
    subranks = types.SUBRANK

    if types.SLOTLESS_SUBRANK[0] in items:
        subranks = types.SLOTLESS_SUBRANK

    for rank in subranks:
        ret[rank] = types.R35List(
            map(
                lambda x: make_weighted_entry(xform(x)),
                items[rank]
            )
        )

    return ret


def generate_tags_entry(items):
    '''Generate a list of tags based on a list of items.'''
    tags = map(lambda x: set(x['tags']), items)
    tags = set.union(*tags)
    return tags | {x['type'] for x in items}


def _cost_in_range(item, mincost, maxcost):
    match maxcost:
        case float('inf'):
            return 'cost' in item and item['cost'] >= mincost
        case _:
            return 'cost' in item and item['cost'] in types.R35Range([mincost, maxcost])


def _costrange_in_range(item, mincost, maxcost):
    return 'costrange' in item and types.R35Range(item['costrange']).overlaps(types.R35Range([mincost, maxcost]))


def costfilter(items, mincost, maxcost):
    '''Filter a list of items by cost.'''
    ret = []

    for item in items:
        match item:
            case {'weight': _, 'value': v}:
                value = v
            case {'weight': _, **v}:
                value = v
            case v:
                value = v

        if _cost_in_range(value, mincost, maxcost) or \
           _costrange_in_range(value, mincost, maxcost) or \
           ('cost' not in value and 'costrange' not in value):
            ret.append(item)

    return ret


class Agent:
    '''Abstract base class for data agents.'''
    def __init__(self, dataset, pool, name, logger=logger):
        self._ds = dataset
        self._data = dict()
        self._ready = asyncio.Event()
        self._pool = pool
        self.name = name
        self.logger = logger

    def _valid_rank(self, rank):
        return rank in self._data

    def _valid_subrank(self, rank, subrank):
        return rank in self._data and subrank in self._data[rank]

    async def _process_async(self, func, args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, func, *args)

    async def load_data(self):
        '''Load data for this agent.'''
        if not self._ready.is_set():
            self.logger.info(f'Loading { self.name } data.')
            self._data = await self._process_async(self._loader, [self.name])
            self.logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return True

    @check_ready
    async def random_rank(self, mincost=0, maxcost=float('inf')):
        d = self._data
        match [x for x in d if d[x].costs.min >= mincost and d[x].costs.max <= maxcost]:
            case []:
                return None
            case [*ranks]:
                return rnd(ranks)

    @check_ready
    async def random_subrank(self, rank, mincost=0, maxcost=float('inf')):
        d = self._data[rank]
        match [x for x in d if d[x].costs.min >= mincost and d[x].costs.max <= maxcost]:
            case []:
                return None
            case [*subranks]:
                return rnd(subranks)

    @check_ready
    async def random_ranked(self, rank=None, subrank=None, mincost=0, maxcost=float('inf')):
        match (rank, subrank):
            case (None, None):
                rank = await self.random_rank(mincost, maxcost)
                if rank is None:
                    return None
                subrank = await self.random_subrank(rank, mincost, maxcost)
                if subrank is None:
                    return None
            case (rank, None) if self._valid_rank(rank):
                subrank = await self.random_subrank(rank, mincost, maxcost)
                if subrank is None:
                    return None
            case (rank, subrank) if self._valid_subrank(rank, subrank):
                pass
            case (rank, subrank) if self._valid_rank(rank):
                raise ValueError(f'Invalid subrank for { self.name }: { subrank }')
            case (rank, _):
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        return rnd(costfilter(self._data[rank][subrank], mincost, maxcost))

    @check_ready
    async def random_compound(self, rank=None, mincost=0, maxcost=float('inf')):
        match rank:
            case None:
                rank = await self.random_rank(mincost, maxcost)
                if rank is None:
                    return None
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        return rnd(costfilter(self._data[rank], mincost, maxcost))

    @check_ready
    async def get_base(self, name):
        items = self._data['base']
        norm_name = norm_string(name)

        match next((x for x in items if norm_string(x['name']) == norm_name), None):
            case None:
                match await self._process_async(
                    did_you_mean,
                    [items, norm_name],
                ):
                    case (True, msg):
                        return (
                            False,
                            f'{ name } is not a recognized item.\n { msg }'
                        )
                    case (False, msg):
                        return (False, msg)
            case item:
                return (True, item)

    @check_ready
    async def random_base(self, tags=[]):
        items = self._data['base']

        match tags:
            case []:
                pass
            case [*tags]:
                items = list(filter(
                    lambda x: all(
                        map(
                            lambda y: y == x['type'] or y in x['tags'],
                            tags
                        )
                    ), items
                ))
            case _:
                raise ValueError('Tags must be a list.')

        if items:
            return random.choice(items)
        else:
            return None

    @check_ready
    async def random_enchant(self, group, bonus, enchants=[], tags=[]):
        items = self._data['enchantments'][group][bonus]

        def _efilter(x):
            result = True

            match x:
                case {'exclude': excluded}:
                    result = result and not any(lambda y: y in excluded, enchants)

            match x:
                case {'limit': {'only': limit}}:
                    result = result and any(lambda y: y in limit, tags)
                case {'limit': {'not': limit}}:
                    result = result and not any(lambda y: y in limit, tags)

            return result

        match list(filter(_efilter, items)):
            case []:
                return None
            case [*opts]:
                return random.choice(opts)['value']

    @check_ready
    async def random_pattern(self, rank, subrank, allow_specific=True, mincost=0, maxcost=float('inf')):
        match rank:
            case None:
                rank = random.choice(types.RANK)
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if subrank is None:
            subrank = random.choice(types.SUBRANK)

        items = costfilter(self._data[rank][subrank], mincost, maxcost)

        if allow_specific:
            return random.choice(items)['value']
        else:
            return random.choice(list(filter(
                lambda x: 'specific' not in x['value'],
                items
            )))['value']

    @check_ready
    async def random_specific(self, *args, mincost=0, maxcost=float('inf')):
        match args:
            case [_, _, _]:
                group = args[0]
                rank = args[1]
                subrank = args[2]
            case [_, _]:
                group = False
                rank = args[0]
                subrank = args[1]

        match rank:
            case None:
                rank = random.choice(types.RANK)
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if subrank is None:
            subrank = random.choice(types.SUBRANK)

        items = self._data['specific']

        if group:
            if group not in items:
                raise ValueError(f'Unrecognized item type for { self.name }: { rank }')

            return random.choice(items[group][rank][subrank])['value']
        else:
            return random.choice(items[rank][subrank])['value']

    @check_ready
    async def tags(self):
        if 'tags' in self._data:
            return list(self._data['tags'])
        else:
            return []
