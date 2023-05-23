# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions and classes for accessing item data.

   Data agents are used to encapsulate the data processed from our data
   files, as well as providing the baasic functions needed by the bot
   code to work with that data. '''

from __future__ import annotations

import asyncio
import logging

from collections.abc import Iterable, Mapping, Sequence, Callable
from dataclasses import dataclass, KW_ONLY
from typing import TypeVar, ParamSpec, cast, TYPE_CHECKING

from . import constants
from .. import types
from ..common import rnd, yaml, bad_return
from ..log import log_call

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from . import DataSet

logger = logging.getLogger(__name__)

T = TypeVar('T')
P = ParamSpec('P')

DEFAULT_MINCOST = 0
DEFAULT_MAXCOST = float('inf')


def ensure_costs(func: Callable[P, T], /) -> Callable[P, T]:
    '''Decorate an async method to ensure that the mincost and maxcost arguments are valid.'''
    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        if getattr(kwargs, 'mincost', None) is None:
            kwargs['mincost'] = DEFAULT_MINCOST

        if getattr(kwargs, 'maxcost', None) is None:
            kwargs['maxcost'] = DEFAULT_MAXCOST

        return func(*args, **kwargs)

    return inner


def _cost_in_range(item: types.Item, /, *, mincost: types.Cost, maxcost: types.Cost) -> bool:
    return item.cost is not None and item.cost in types.R35Range([mincost, maxcost])


def _costrange_in_range(item: types.Item, /, *, mincost: types.Cost, maxcost: types.Cost) -> bool:
    return item.costrange is not None and types.R35Range(item.costrange).overlaps(types.R35Range([mincost, maxcost]))


def create_spellmult_xform(classes: types.item.ClassMap, /) -> Callable[[types.Item], types.Item]:
    '''Create a costmult handler function based on spell levels.'''
    def xform(x: types.Item) -> types.Item:
        levels = [x.levels for x in classes.values()]

        match x:
            case types.item.SpellItem(spell={'level': level, 'class': 'minimum'}, costmult=costmult) if costmult is not None:
                filtered = filter(lambda x: len(x) > level and x[level] is not None, levels)
                mapped = set(map(lambda x: cast(int, x[level]), filtered))
                minlevel = min(mapped)
                x.cost = minlevel * costmult
            case types.item.SpellItem(spell={'level': level}, costmult=costmult) if costmult is not None:
                filtered = filter(lambda x: len(x) > level and x[level] is not None, levels)
                mapped = set(map(lambda x: cast(int, x[level]), filtered))
                minlevel = min(mapped)
                maxlevel = max(mapped)
                x.costrange = (
                    minlevel * costmult,
                    maxlevel * costmult,
                )
            case _:
                pass

        return x

    return xform


def costfilter(items: Iterable[T], /, *, mincost: types.Cost | None, maxcost: types.Cost | None) -> list[T]:
    '''Filter a list of items by cost.'''
    ret: list[T] = []

    if mincost is None:
        mincost = DEFAULT_MINCOST

    if maxcost is None:
        maxcost = DEFAULT_MAXCOST

    for item in items:
        if isinstance(item, types.item.BaseItem):
            if (_cost_in_range(item, mincost=mincost, maxcost=maxcost) or
               _costrange_in_range(item, mincost=mincost, maxcost=maxcost) or
               (item.cost is None and item.costrange is None)):
                ret.append(cast(T, item))
        else:
            ret.append(item)

    return ret


@dataclass
class AgentData:
    '''Base class for agent data entries.'''
    _: KW_ONLY
    ranked: types.RankedItemList | None = None
    compound: types.CompoundItemList | Mapping[types.Rank, Sequence[types.WeightedValue]] | None = None


class Agent(types.ReadyState):
    '''Abstract base class for data agents.'''
    def __init__(self: Agent, /, dataset: DataSet, name: str) -> None:
        self._ds = dataset
        self._data = AgentData()
        self._ready = asyncio.Event()
        self.name = name

    def __repr__(self: Agent, /) -> str:
        return f'roll35.data.Agent[{ self.name }, ready: { self._ready.is_set() }]'

    @staticmethod
    def _process_data(data: Mapping | Sequence, /) -> AgentData:
        '''Callback to take the raw data for the agent and make it usable.

           Subclasses need to either override this, or provide their
           own implementation of Agent.load_data().

           This will be called when loading data for the agent. It
           should be a static method that accepts a single argument,
           consisting of the data to be processed. The return value will
           be assigned to the agent’s `_data` attribute.'''
        return NotImplemented

    def _valid_rank(self: Agent, rank: types.Rank, /) -> bool:
        if self._data.ranked is not None:
            return rank in self._data.ranked
        elif self._data.compound is not None:
            return rank in self._data.compound
        else:
            return False

    def _valid_subrank(self: Agent, rank: types.Rank, subrank: types.Subrank, /) -> bool:
        if self._data.ranked is not None:
            return rank in self._data.ranked and subrank in self._data.ranked[rank]
        else:
            return False

    async def _process_async(self: Agent, pool: Executor, func: Callable[..., T], args: Iterable, /) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(pool, func, *args)

    async def load_data(self: Agent, pool: Executor, /) -> types.Ret:
        '''Load data for this agent.'''
        if not self._ready.is_set():
            logger.info(f'Loading { self.name } data')

            with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            self._data = await self._process_async(pool, self._process_data, [data])

            logger.info(f'Finished loading { self.name } data')

            self._ready.set()

        return types.Ret.OK

    @ensure_costs
    @log_call(logger, 'roll random rank')
    @types.check_ready(logger)
    async def random_rank(self: Agent, /, *, mincost: types.Cost | None = None, maxcost: types.Cost | None = None) -> types.Rank | types.Ret:
        '''Return a random rank, possibly within the cost limits.'''
        if self._data.ranked is not None:
            if isinstance(self._data.ranked, types.R35Map):
                d1 = cast(types.RankedItemList, self._data.ranked)
                match [x for x in d1 if d1[x].costs.overlaps(types.R35Range([mincost, maxcost]))]:
                    case [*ranks]:
                        return cast(types.Rank, rnd(ranks))
        elif self._data.compound is not None:
            if isinstance(self._data.compound, types.R35Map):
                d3 = cast(types.CompoundItemList, self._data.compound)
                match [x for x in d3 if d3[x].costs.overlaps(types.R35Range([mincost, maxcost]))]:
                    case [*ranks]:
                        return cast(types.Rank, rnd(ranks))
            else:
                d4 = [x for x in self._data.compound if x in {y for y in types.Rank}]
                return rnd(d4)

        return types.Ret.NO_MATCH

    @ensure_costs
    @log_call(logger, 'roll random subrank')
    @types.check_ready(logger)
    async def random_subrank(self: Agent, /, rank: types.Rank, *, mincost: types.Cost | None = None, maxcost: types.Cost | None = None) -> \
            types.Subrank | types.Ret:
        '''Return a random subrank for the given rank, possibly within the cost limits.'''
        if self._data.ranked is not None:
            data = self._data.ranked
        else:
            return types.Ret.NO_MATCH

        d = {k: v for k, v in data[rank].items() if k in {x for x in types.Subrank}}
        match [x for x in d if d[x].costs.overlaps(types.R35Range([mincost, maxcost]))]:
            case [*subranks]:
                return cast(types.Subrank, rnd(subranks))

        return types.Ret.NO_MATCH

    @ensure_costs
    @log_call(logger, 'roll random ranked item')
    @types.check_ready(logger)
    async def random_ranked(
            self: Agent,
            /, *,
            rank: types.Rank | None = None,
            subrank: types.Subrank | None = None,
            mincost: types.Cost | None = None,
            maxcost: types.Cost | None = None) -> \
            types.item.BaseItem | types.Ret:
        '''Roll a random item for the given rank and subrank, possibly within the specified cost range.'''
        if self._data.ranked is None:
            return types.Ret.NO_MATCH

        if rank is None:
            match await self.random_rank(mincost=mincost, maxcost=maxcost):
                case types.Ret.NO_MATCH:
                    return types.Ret.NO_MATCH
                case types.Rank() as r:
                    rank = r
                case r1:
                    logger.error(bad_return(r1))
                    raise RuntimeError

        if subrank is None and self._valid_rank(rank):
            match await self.random_subrank(rank, mincost=mincost, maxcost=maxcost):
                case types.Ret.NO_MATCH:
                    return types.Ret.NO_MATCH
                case types.Subrank() as s:
                    subrank = s
                case r2:
                    logger.error(bad_return(r2))
                    raise RuntimeError
        else:
            raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if not self._valid_subrank(rank, subrank):
            raise ValueError(f'Invalid subrank for { self.name }: { subrank }')

        return cast(types.item.BaseItem, rnd(costfilter(self._data.ranked[rank][subrank], mincost=mincost, maxcost=maxcost)))

    @ensure_costs
    @log_call(logger, 'roll random compound item')
    @types.check_ready(logger)
    async def random_compound(
            self: Agent,
            /, *,
            rank: types.Rank | None = None,
            mincost: types.Cost | None = None,
            maxcost: types.Cost | None = None) -> \
            types.item.CompoundItem | str | types.Ret:
        '''Roll a random item for the given rank, possibly within the specified cost range.'''
        if self._data.compound is None:
            return types.Ret.NO_MATCH

        match rank:
            case None:
                match await self.random_rank(mincost=mincost, maxcost=maxcost):
                    case types.Ret.NO_MATCH:
                        return types.Ret.NO_MATCH
                    case types.Rank() as r:
                        rank = r
                    case r1:
                        logger.error(bad_return(r1))
                        raise RuntimeError
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        return cast(types.item.CompoundItem | str, rnd(costfilter(self._data.compound[rank], mincost=mincost, maxcost=maxcost)))
