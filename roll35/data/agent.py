# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions and classes for accessing item data.

   Data agents are used to encapsulate the data processed from our data
   files, as well as providing the baasic functions needed by the bot
   code to work with that data. '''

import abc
import asyncio
import logging

from . import constants
from . import types
from ..common import check_ready, rnd, make_weighted_entry, yaml
from ..retcode import Ret

logger = logging.getLogger(__name__)


def ensure_costs(func):
    '''Decorate an async method to ensure that the mincost and maxcost arguments are valid.'''
    async def f(self, *args, mincost=None, maxcost=None, **kwargs):
        if mincost is None:
            mincost = 0

        if maxcost is None:
            maxcost = float('inf')

        return await func(self, *args, mincost=mincost, maxcost=maxcost, **kwargs)

    return f


def process_compound_itemlist(items, costmult_handler=lambda x: x):
    '''Process a compound list of weighted values.

       Each list entry must be a dict with keys coresponding to the
       possible values for `roll35.data.constants.RANK` with each such key
       bearing a weight to use for the entry when rolling a random item
       of the corresponding rank.'''
    ret = types.R35Map()

    for rank in constants.RANK:
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
    ranks = constants.RANK

    if constants.RANK[0] not in items:
        ranks = constants.LIMITED_RANK

    for rank in ranks:
        ret[rank] = process_subranked_itemlist(items[rank], xform)

    return ret


def process_subranked_itemlist(items, xform=lambda x: x):
    '''Process a subranked list of weighted values.

       This takes a dict of subranks to lists of dicts of weighted items
       and processes them into the format used by our weighted random
       selection in various data agent modules.'''
    ret = types.R35Map()
    subranks = constants.SUBRANK

    if constants.SLOTLESS_SUBRANK[0] in items:
        subranks = constants.SLOTLESS_SUBRANK

    for rank in subranks:
        ret[rank] = types.R35List(
            map(
                lambda x: make_weighted_entry(xform(x)),
                items[rank]
            )
        )

    return ret


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


class Agent(abc.ABC):
    '''Abstract base class for data agents.'''
    def __init__(self, dataset, pool, name):
        self._ds = dataset
        self._data = dict()
        self._ready = asyncio.Event()
        self._pool = pool
        self.name = name

    @staticmethod
    @abc.abstractmethod
    def _process_data(data):
        '''Callback to take the raw data for the agent and make it usable.

           Must be overridden by subclasses.

           This will be called when loading data for the agent. It
           should be a static method that accepts a single argument,
           consisting of the data to be processed. The return value will
           be assigned to the agent’s `_data` attribute.'''
        return NotImplemented

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
            logger.info(f'Loading { self.name } data.')

            with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            self._data = await self._process_async(self._process_data, [data])
            logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return Ret.OK

    @check_ready
    async def random_rank(self, mincost, maxcost):
        d = self._data
        match [x for x in d if d[x].costs.min >= mincost and d[x].costs.max <= maxcost]:
            case []:
                return Ret.NO_MATCH
            case [*ranks]:
                return rnd(ranks)

    @check_ready
    async def random_subrank(self, rank, mincost, maxcost):
        d = self._data[rank]
        match [x for x in d if d[x].costs.min >= mincost and d[x].costs.max <= maxcost]:
            case []:
                return Ret.NO_MATCH
            case [*subranks]:
                return rnd(subranks)

    @check_ready
    @ensure_costs
    async def random_ranked(self, rank=None, subrank=None, mincost=None, maxcost=None):
        match (rank, subrank):
            case (None, None):
                rank = await self.random_rank(mincost, maxcost)
                if rank is Ret.NO_MATCH:
                    return Ret.NO_MATCH
                subrank = await self.random_subrank(rank, mincost, maxcost)
                if subrank is Ret.NO_MATCH:
                    return Ret.NO_MATCH
            case (rank, None) if self._valid_rank(rank):
                subrank = await self.random_subrank(rank, mincost, maxcost)
                if subrank is Ret.NO_MATCH:
                    return Ret.NO_MATCH
            case (rank, subrank) if self._valid_subrank(rank, subrank):
                pass
            case (rank, subrank) if self._valid_rank(rank):
                raise ValueError(f'Invalid subrank for { self.name }: { subrank }')
            case (rank, _):
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        return rnd(costfilter(self._data[rank][subrank], mincost, maxcost))

    @check_ready
    @ensure_costs
    async def random_compound(self, rank=None, mincost=None, maxcost=None):
        match rank:
            case None:
                rank = await self.random_rank(mincost, maxcost)
                if rank is Ret.NO_MATCH:
                    return Ret.NO_MATCH
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        return rnd(costfilter(self._data[rank], mincost, maxcost))
