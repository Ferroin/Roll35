# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for armor, shields, and weapons.'''

from __future__ import annotations

import logging
import random

from collections.abc import Mapping, Sequence, Iterable
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING, Callable, cast

from . import agent
from .ranked import process_ranked_itemlist
from .. import types
from ..common import make_weighted_entry, norm_string, did_you_mean, bad_return, rnd, ismapping
from ..log import log_call_async

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from . import DataSet

    EnchantmentTable = types.R35Map[str, dict[int, Sequence[types.WeightedEntry]]]
    SpecificItemList = types.RankedItemList | types.R35Map[str, types.RankedItemList]
    TagData = set[str]
    Bonus = int


@dataclass
class OrdnanceData(agent.AgentData):
    '''Data handled by an OrdnanceAgent.'''
    base: Sequence[types.item.OrdnanceBaseItem]
    tags: TagData
    enchantments: EnchantmentTable
    specific: SpecificItemList
    masterwork: int | float
    enchant_base_cost: int | float


def process_enchantment_table(items: Mapping, /, basevalue: types.item.Cost) -> EnchantmentTable:
    '''Process an armor or weapon enchantment table.'''
    ret: EnchantmentTable = types.R35Map()

    for group in items:
        groupdata: dict[int, Sequence[types.WeightedEntry]] = dict()

        for value in items[group]:
            groupdata[value] = list(
                map(
                    make_weighted_entry,
                    map(
                        lambda x: types.item.OrdnanceEnchant(**x),
                        items[group][value]
                    )
                )
            )

        ret[group] = groupdata

    return ret


def get_enchant_bonus_costs(data: OrdnanceData, base: types.item.OrdnanceBaseItem, /) -> tuple[types.item.Cost, types.item.Cost]:
    '''Compute the enchantment bonus costs for the specified base item.'''
    if 'double' in base.tags:
        masterwork = data.masterwork * 2
        enchant_base_cost = data.enchant_base_cost * 2
    else:
        masterwork = data.masterwork
        enchant_base_cost = data.enchant_base_cost

    return (
        masterwork,
        enchant_base_cost,
    )


def get_costs_and_bonus(enchants: Iterable[types.WeightedEntry], /) -> tuple[types.item.Cost, types.item.Cost, Bonus, Bonus]:
    '''Figure out the range of extra costs that a given list of enchantments might have.'''
    min_cost: types.item.Cost = -1
    max_cost: types.item.Cost = 0
    min_bonus: Bonus = 0
    max_bonus: Bonus = 0
    has_non_bonus = False

    for item in enchants:
        match item.value:
            case types.item.OrdnanceEnchant(bonuscost=None, bonus=None):
                min_cost = 0
                has_non_bonus = True
            case types.item.OrdnanceEnchant(bonuscost=c, bonus=None):
                assert c is not None
                if min_cost == -1:
                    min_cost = c
                else:
                    min_cost = min(min_cost, c)
                max_cost = max(max_cost, c)
                has_non_bonus = True
            case types.item.OrdnanceEnchant(bonuscost=None, bonus=b):
                assert b is not None
                min_cost = 0
                if min_bonus == 0:
                    min_bonus = b
                else:
                    min_bonus = min(min_bonus, b)
                max_bonus = max(max_bonus, b)
            case _:
                raise ValueError(f'{ item } has both bonuscost and bonus keys.')

    if has_non_bonus:
        min_bonus = 0

    return (min_cost, max_cost, min_bonus, max_bonus)


def get_costs(bonus: Bonus, base: types.item.Cost, enchants: list[Bonus], enchantments: EnchantmentTable, /) -> \
        tuple[types.item.Cost, types.item.Cost]:
    '''Determine the range of possible costs for a set of enchantments.'''
    min_cost: types.item.Cost = float('inf')
    max_cost: types.item.Cost = 0

    for group in enchantments.values():
        minc_possible = []
        maxc_possible = []
        minb_possible = []
        maxb_possible = []

        for e in enchants:
            c1, c2, b1, b2 = get_costs_and_bonus(group[e])
            minc_possible.append(0 if c1 == 'varies' else c1)
            maxc_possible.append(0 if c2 == 'varies' else c2)
            minb_possible.append(max([b1, e]))
            maxb_possible.append(max([b2, e]))

        min_cost = min(
            min_cost,
            min(minc_possible) + (((min(minb_possible) + bonus) ** 2) * base),
        )

        max_cost = max(
            max_cost,
            min(maxc_possible) + (((min(maxb_possible) + bonus) ** 2) * base),
        )

    return min_cost, max_cost


def create_xform(base: int | float, enchantments: EnchantmentTable, specific: SpecificItemList, /) -> \
        Callable[[types.item.OrdnancePattern], types.item.OrdnancePattern]:
    '''Produce a mapping function for adding costs to enchantment combos.'''
    def xform(x: types.item.OrdnancePattern) -> types.item.OrdnancePattern:
        min_cost: types.item.Cost = 0
        max_cost: types.item.Cost = float('inf')
        match x:
            case types.item.OrdnancePattern(bonus=bonus, enchants=[]) if bonus is not None:
                min_cost = (bonus ** 2) * base
                max_cost = (bonus ** 2) * base
            case types.item.OrdnancePattern(bonus=bonus, enchants=[*enchants]) if bonus is not None:
                min_cost, max_cost = get_costs(bonus, base, enchants, enchantments)
            case types.item.OrdnancePattern(specific=[group, rank, subrank]):
                min_cost = cast(Mapping[str, types.RankedItemList], specific)[group][types.Rank(rank)][types.Subrank(subrank)].costs.min
                max_cost = cast(Mapping[str, types.RankedItemList], specific)[group][types.Rank(rank)][types.Subrank(subrank)].costs.max
            case types.item.OrdnancePattern(specific=[rank, subrank]):
                min_cost = cast(types.RankedItemList, specific)[types.Rank(rank)][types.Subrank(subrank)].costs.min
                max_cost = cast(types.RankedItemList, specific)[types.Rank(rank)][types.Subrank(subrank)].costs.max
            case _:
                ValueError(f'{ x } is not a valid enchantment combination entry.')

        if min_cost == 'varies':
            min_cost = 0

        if max_cost == 'varies':
            max_cost = float('inf')

        x.costrange = (
            min_cost,
            max_cost,
        )

        return x

    return xform


def generate_tags_entry(items: Sequence[types.item.OrdnanceBaseItem], /) -> set[str]:
    '''Generate a list of tags based on a list of items.'''
    taglist = list(map(lambda x: set(x.tags), items))
    tags = reduce(lambda x, y: x | y, taglist)
    return tags | {x.type for x in items}


class OrdnanceAgent(agent.Agent):
    '''Data agent for weapon or armor item data.'''
    def __init__(self: OrdnanceAgent, /, dataset: DataSet, name: str) -> None:
        super().__init__(dataset, name)
        self._data: OrdnanceData = OrdnanceData(
            base=[],
            tags=set(),
            specific=cast(types.RankedItemList, types.R35Map()),
            enchantments=types.R35Map(),
            masterwork=0,
            enchant_base_cost=0,
        )

    @staticmethod
    def _process_data(data: Mapping | Sequence, /) -> OrdnanceData:
        if not ismapping(data):
            raise ValueError('Ordnance data must be a mapping.')

        enchantments = process_enchantment_table(data['enchantments'], data['enchant_base_cost'])

        d_specific = data['specific']

        if types.Rank.MEDIUM.value not in d_specific:
            specific: SpecificItemList = types.R35Map({
                k: process_ranked_itemlist(v, typ=lambda x: types.item.OrdnanceSpecific(**x)) for k, v in d_specific.items()
            })
        else:
            specific = process_ranked_itemlist(d_specific, typ=lambda x: types.item.OrdnanceSpecific(**x))

        patterns = process_ranked_itemlist(
            data,
            typ=lambda x: types.item.OrdnancePattern(**x),
            xform=create_xform(
                data['enchant_base_cost'],
                enchantments,
                specific,
            ),
        )

        base: types.R35List[types.item.OrdnanceBaseItem] = types.R35List()

        for item in data['base']:
            try:
                base.append(types.item.OrdnanceBaseItem(**item))
            except TypeError:
                raise RuntimeError(f'Invalid ordnance base item entry: { item }')

        tags = generate_tags_entry(base)

        return OrdnanceData(
            base=base,
            tags=tags,
            specific=specific,
            enchantments=enchantments,
            ranked=patterns,
            masterwork=data['masterwork'],
            enchant_base_cost=data['enchant_base_cost'],
        )

    async def random(
            self: OrdnanceAgent,
            /,
            rank: types.Rank,
            subrank: types.Subrank,
            *,
            allow_specific: bool = True,
            mincost: types.item.Cost | None = None,
            maxcost: types.item.Cost | None = None) -> \
            types.item.OrdnancePattern | types.Ret:
        '''Alias of random_pattern.'''
        return await self.random_pattern(
            rank=rank,
            subrank=subrank,
            allow_specific=allow_specific,
            mincost=mincost,
            maxcost=maxcost,
        )

    @agent.ensure_costs
    @log_call_async(logger, 'roll random ordnance pattern')
    @types.check_ready(logger)
    async def random_pattern(
            self: OrdnanceAgent,
            /,
            rank: types.Rank | None,
            subrank: types.Subrank | None,
            *,
            allow_specific: bool = True,
            mincost: types.item.Cost | None = None,
            maxcost: types.item.Cost | None = None) -> \
            types.item.OrdnancePattern | types.Ret:
        '''Return a random item pattern to use to generate a random item from.'''
        match rank:
            case None:
                match await self.random_rank(mincost=mincost, maxcost=maxcost):
                    case r1 if isinstance(r1, types.Ret):
                        return r1
                    case r2:
                        rank = cast(types.Rank, r2)
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        assert rank is not None

        if subrank is None:
            match await self.random_subrank(rank, mincost=mincost, maxcost=maxcost):
                case r3 if isinstance(r3, types.Ret):
                    return r3
                case r4:
                    subrank = cast(types.Subrank, r4)
        elif not self._valid_subrank(rank, subrank):
            raise ValueError(f'Invalid subrank for { self.name }: { subrank }')

        assert subrank is not None

        items = agent.costfilter(cast(types.RankedItemList, self._data.ranked)[rank][subrank], mincost=mincost, maxcost=maxcost)

        if allow_specific:
            if items:
                return rnd(items)
            else:
                return types.Ret.NO_MATCH
        else:
            match list(filter(lambda x: 'specific' not in x.value, items)):
                case []:
                    return types.Ret.NO_MATCH
                case [*items]:
                    return rnd(items)
                case ret:
                    logger.error(bad_return(ret))
                    return types.Ret.FAILED

    @log_call_async(logger, 'get base ordnance item')
    @types.check_ready(logger)
    async def get_base(self: OrdnanceAgent, pool: Executor, /, name: str) -> \
            types.Result[types.item.OrdnanceBaseItem]:
        '''Get a base item by name.

           On a mismatch, returns a list of possible names that might
           have been intended.'''
        items = self._data.base
        norm_name = norm_string(name)

        match next((x for x in items if norm_string(x.name) == norm_name), None):
            case item if item is not None:
                return (types.Ret.OK, item)
            case _:
                match await self._process_async(pool, did_you_mean, [[x.name for x in items], norm_name]):
                    case (types.Ret.OK, msg):
                        return (
                            types.Ret.FAILED,
                            f'{ name } is not a recognized item.\n { msg }'
                        )
                    case (types.Ret() as ret, str() as msg) if ret is not types.Ret.OK:
                        return (ret, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        return (types.Ret.FAILED, 'Unknown internal error.')

        # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
        #
        # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
        raise RuntimeError

    @log_call_async(logger, 'roll random base ordnance item')
    @types.check_ready(logger)
    async def random_base(self: OrdnanceAgent, /, tags: Sequence[str] = []) -> types.item.OrdnanceBaseItem | types.Ret:
        '''Get a base item at random.'''
        items = self._data.base

        match tags:
            case []:
                pass
            case [*tags]:
                items = list(filter(
                    lambda x: all(
                        map(
                            lambda y: y == x.type or y in x.tags,
                            tags
                        )
                    ), items
                ))
            case _:
                raise ValueError('Tags must be a list.')

        if items:
            return random.choice(items)
        else:
            return types.Ret.NO_MATCH

    @log_call_async(logger, 'roll random ordnance enchantment')
    @types.check_ready(logger)
    async def random_enchant(
            self: OrdnanceAgent,
            /,
            group: str,
            bonus: Bonus,
            enchants: Sequence[str] = [],
            tags: set[str] = set()) -> \
            types.item.OrdnanceEnchant | types.Ret:
        '''Roll a random enchantment.'''
        items = self._data.enchantments[group][bonus]

        def _efilter(x: types.WeightedEntry[types.item.OrdnanceEnchant]) -> bool:
            result = True

            match x.value:
                case types.item.OrdnanceEnchant(exclude=list() as excluded):
                    result = result and not any(map(lambda y: y in excluded, enchants))

            match x.value:
                case types.item.OrdnanceEnchant(limit={'only': list() as limit}):
                    result = result and bool(set(limit) & tags)
                case types.item.OrdnanceEnchant(limit={'not': list() as limit}):
                    result = result and not bool(set(limit) & tags)

            return result

        match list(filter(_efilter, items)):
            case []:
                return types.Ret.NO_MATCH
            case [*opts]:
                return cast(types.item.OrdnanceEnchant | types.Ret, rnd(opts))
            case _:
                raise ValueError

    @agent.ensure_costs
    @log_call_async(logger, 'roll random specific ordnance item.')
    @types.check_ready(logger)
    async def random_specific(
            self: OrdnanceAgent,
            /,
            args: Sequence[str],
            *,
            mincost: types.item.Cost | None = None,
            maxcost: types.item.Cost | None = None) -> \
            types.item.OrdnanceSpecific | types.Ret:
        '''Roll a random specific item.'''
        match args:
            case [_, _, _]:
                group = args[0]
                rank = types.Rank(args[1])
                subrank = types.Subrank(args[2])
            case [_, _]:
                group = ''
                rank = types.Rank(args[0])
                subrank = types.Subrank(args[1])
            case _:
                raise ValueError(f'Invalid arguments for { self.name }.random_specific: { args }')

        match rank:
            case rank if self._valid_rank(rank):
                pass
            case _:
                raise ValueError(f'Invalid rank for { self.name }: { rank }')

        if not self._valid_subrank(rank, subrank):
            raise ValueError(f'Invalid subrank for { self.name }: { subrank }')

        items = self._data.specific

        if group:
            if group not in items:
                raise ValueError(f'Unrecognized item type for { self.name }: { rank }')

            items = cast(Mapping[str, types.RankedItemList], items)[group]

        possible = agent.costfilter(cast(types.RankedItemList, items)[rank][subrank], mincost=mincost, maxcost=maxcost)

        if possible:
            return rnd(possible)
        else:
            return types.Ret.NO_MATCH

    @log_call_async(logger, 'get ordnance bonus costs')
    @types.check_ready(logger)
    async def get_bonus_costs(self: OrdnanceAgent, /, base: types.item.OrdnanceBaseItem) -> tuple[types.item.Cost, types.item.Cost]:
        '''Get the bonus costs associated with the given item.'''
        return get_enchant_bonus_costs(self._data, base)

    @log_call_async(logger, 'get ordnance tags')
    @types.check_ready(logger)
    async def tags(self: OrdnanceAgent, /) -> Sequence[str] | types.Ret:
        '''Get a list of recognized tags.'''
        if self._data.tags:
            return list(self._data.tags)
        else:
            return types.Ret.NO_MATCH
