# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions for rolling magic items.'''

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Any, cast

from .. import types
from ..common import bad_return, ret_async
from ..data.category import CategoryAgent
from ..data.classes import ClassesAgent
from ..data.compound import CompoundAgent
from ..data.ordnance import OrdnanceAgent
from ..data.ranked import RankedAgent
from ..data.spell import SpellAgent
from ..data.wondrous import WondrousAgent
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Awaitable, Mapping, Sequence
    from concurrent.futures import Executor

    from ..data import DataSet

    MIResult = types.Result[types.Item]

NOT_READY = 'Magic item data is not yet available, please try again later.'
NO_ITEMS_IN_COST_RANGE = 'No items found in requested cost range.'

MAX_REROLLS = 128
MAX_COUNT = 32

logger = logging.getLogger(__name__)


async def _reroll_async(
        pool: Executor,
        /,
        ds: DataSet,
        path: Sequence[str],
        *,
        attempt: int,
        mincost: int | float | None,
        maxcost: int | float | None) -> \
        MIResult:
    '''Reroll a magic item using the specified parameters.'''
    match path:
        case [category, slot, rank, subrank]:
            return await roll(
                pool,
                ds,
                {
                    'rank': types.Rank(rank),
                    'subrnak': types.Subrank(subrank),
                    'category': category,
                    'slot': slot,
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt=attempt+1
            )
        case [category, rank, subrank]:
            return await roll(
                pool,
                ds,
                {
                    'rank': types.Rank(rank),
                    'subrnak': types.Subrank(subrank),
                    'category': category,
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt=attempt+1
            )
        case _:
            logger.warning('Invalid reroll directive found while rolling for magic item: { path }.')
            return (
                types.Ret.FAILED,
                'Invalid reroll directive found while rolling for magic item.'
            )


async def _assemble_magic_item(
        agent: OrdnanceAgent,
        /,
        base_item: types.item.OrdnanceBaseItem,
        pattern: types.item.OrdnancePattern,
        masterwork: int | float,
        bonus_cost: int | float,
        *,
        attempt: int = 0) -> \
        types.Result[types.item.SimpleItem]:
    '''Assemble a magic weapon or armor item.'''
    logger.debug(f'Assembling magic item with parameters: {base_item}, {pattern}, {masterwork}, {bonus_cost}')

    if pattern.bonus is None or pattern.enchants is None:
        raise ValueError('Cannot assemble magic item without bonus or enchants properties.')

    item_cost = cast(types.Cost, base_item.cost) + masterwork
    item_cost += (pattern.bonus ** 2) * bonus_cost
    group = base_item.type
    if base_item.tags is not None and base_item.tags:
        tags = set(base_item.tags)
    else:
        tags = set()
    cbonus = 0
    extra_ecost: float | int = 0
    enchants: list[str] = []
    failed = False

    for ebonus in pattern.enchants:
        match await agent.random_enchant_async(group, ebonus, enchants, tags):
            case types.Ret.NOT_READY:
                failed = True
                await asyncio.sleep(1)
                break
            case types.Ret.NO_MATCH:
                failed = True
                break
            case enchant if isinstance(enchant, types.item.OrdnanceEnchant):
                enchants.append(enchant.name)

                if enchant.bonuscost is not None:
                    extra_ecost += enchant.bonuscost

                if enchant.bonus is not None:
                    cbonus += enchant.bonus
                else:
                    cbonus += ebonus

                if enchant.add is not None:
                    tags = tags | set(enchant.add)

                if enchant.remove is not None:
                    tags = tags - set(enchant.remove)
            case ret:
                logger.error(bad_return(ret))
                failed = True
                break

    if failed:
        if attempt >= 6:
            return (types.Ret.LIMITED, 'Too many failed attempts to select enchantments.')
        else:
            attempt += 1
            logger.debug(
                'Failed to generate valid enchantments for magic item, retrying (attempt { attempt }).'
            )
            return await _assemble_magic_item(
                agent, base_item, pattern, masterwork, bonus_cost,
                attempt=attempt
            )
    else:
        item_cost += ((cbonus ** 2) * bonus_cost) + extra_ecost
        etitle = ''.join(list(map(lambda x: f'{x} ', enchants)))
        return (
            types.Ret.OK,
            types.item.SimpleItem(
                name=f'+{pattern.bonus} {etitle}{base_item.name}',
                cost=item_cost,
            )
        )


def roll_many_async(pool: Executor, ds: DataSet, /, count: int, args: Mapping[str, Any]) -> Sequence[Awaitable[MIResult]]:
    '''Roll a number of magic items.

       Returns a list of coroutines that can be awaited to get the
       requested items.'''
    if not ds.ready:
        return [ret_async((types.Ret.NOT_READY, NOT_READY))]

    if count > MAX_COUNT:
        return [ret_async((types.Ret.LIMITED, f'Too many items requested, no more than {MAX_COUNT} may be rolled at a time.'))]

    coros = []

    for i in range(0, count):
        coros.append(roll(pool, ds, args))

    return coros


@log_call_async(logger, 'roll magic item')
async def roll(pool: Executor, ds: DataSet, /, args: Mapping[str, Any], *, attempt: int = 0) -> MIResult:
    '''Roll a magic item.'''
    args = {
        'rank': args.get('rank', None),
        'subrank': args.get('subrank', None),
        'category': args.get('category', None),
        'slot': args.get('slot', None),
        'base': args.get('base', None),
        'cls': args.get('cls', None),
        'level': args.get('level', None),
        'mincost': args.get('mincost', 0),
        'maxcost': args.get('maxcost', float('inf')),
        'o_args': args.get('o_args', args),
    }
    ret: Any = None

    if attempt >= MAX_REROLLS:
        logger.warning(f'Recursion limit hit while rolling magic item: {args}')
        return (types.Ret.LIMITED, 'Too many rerolls while attempting to generate item.')

    slots = await cast(WondrousAgent, ds['wondrous']).slots_async()
    categories = await cast(CategoryAgent, ds['category']).categories_async()

    if categories is types.Ret.NOT_READY or slots is types.Ret.NOT_READY:
        return (types.Ret.NOT_READY, NOT_READY)

    compound = ds.types['compound'] & categories
    ordnance = ds.types['ordnance'] & categories
    ranked = ds.types['ranked'] & categories
    mincost = args['mincost']
    maxcost = args['maxcost']
    item: MIResult | types.item.BaseItem | types.Ret = types.Ret.FAILED

    match args:
        case {'rank': types.Rank.MINOR, 'subrank': types.Subrank.LEAST, 'category': 'wondrous', 'slot': 'slotless'}:
            item = await cast(RankedAgent, ds['slotless']).random_async(
                rank=types.Rank.MINOR,
                subrank=types.Subrank.LEAST,
                mincost=mincost,
                maxcost=maxcost,
            )
        case {'subrank': types.Subrank.LEAST}:
            item = (types.Ret.INVALID, 'Only slotless wondrous items have a least subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous', 'slot': slot} if slot in slots:
            item = await cast(RankedAgent, ds[slot]).random_async(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'slot': slot} if slot in slots:
            item = await cast(RankedAgent, ds[slot]).random_async(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous'}:
            match await cast(WondrousAgent, ds['wondrous']).random_async():
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case str() as slot:
                    item = await cast(RankedAgent, ds[slot]).random_async(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
                case ret:
                    logger.warning(bad_return(ret))
                    item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': None} if category in ordnance:
            agent = cast(OrdnanceAgent, ds[category])
            match await agent.random_pattern_async(rank=rank, subrank=subrank, allow_specific=True, mincost=mincost, maxcost=maxcost):
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case types.Ret.NO_MATCH:
                    item = types.Ret.NO_MATCH
                case types.item.OrdnancePattern(specific=specific) if specific is not None:
                    item = await agent.random_specific_async(specific, mincost=mincost, maxcost=maxcost)
                case types.item.OrdnancePattern() as pattern:
                    match await agent.random_base_async():
                        case types.Ret.NOT_READY:
                            item = (types.Ret.NOT_READY, NOT_READY)
                        case types.item.OrdnanceBaseItem() as base_item:
                            match await agent.get_bonus_costs_async(base_item):
                                case types.Ret.NOT_READY:
                                    item = (types.Ret.NOT_READY, NOT_READY)
                                case (masterwork, bonus_cost):
                                    item = await _assemble_magic_item(
                                        agent, base_item, pattern, masterwork, bonus_cost
                                    )
                case ret:
                    logger.warning(bad_return(ret))
                    item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': base} if category in ordnance:
            agent = cast(OrdnanceAgent, ds[category])

            match await agent.get_base_async(pool, base):
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case (types.Ret() as r1, str() as msg) if r1 is not types.Ret.OK:
                    item = (r1, msg)
                case (types.Ret.OK, types.item.OrdnanceBaseItem() as base_item):
                    match await agent.random_pattern_async(rank=rank, subrank=subrank, allow_specific=False, mincost=mincost, maxcost=maxcost):
                        case types.Ret.NOT_READY:
                            item = (types.Ret.NOT_READY, NOT_READY)
                        case types.Ret.NO_MATCH:
                            item = types.Ret.NO_MATCH
                        case types.item.OrdnancePattern() as pattern:
                            match await agent.get_bonus_costs_async(base_item):
                                case types.Ret.NOT_READY:
                                    item = (types.Ret.NOT_READY, NOT_READY)
                                case (masterwork, bonus_cost):
                                    item = await _assemble_magic_item(
                                        agent, base_item, pattern, masterwork, bonus_cost
                                    )
                        case ret:
                            logger.error(bad_return(ret))
                            item = (types.Ret.FAILED, 'Unknown internal error.')
                case ret:
                    logger.error(bad_return(ret))
                    item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': _, 'subrank': subrank, 'category': category} if category in compound and subrank is not None:
            item = (types.Ret.INVALID, f'Invalid parmeters specified, {category} does not take a subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': category, 'cls': cls, 'level': level} if cls is not None or level is not None:
            match await cast(ClassesAgent, ds['classes']).classes_async():
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case classes:
                    valid = set(cast(set[types.item.ClassEntry], classes)) | cast(SpellAgent, ds['spell']).EXTRA_CLASS_NAMES

                    if cls in valid or cls is None:
                        match await cast(CompoundAgent, ds[category]).random_async(rank=rank, cls=cls, level=level, mincost=mincost, maxcost=maxcost):
                            case types.item.BaseItem() as i1:
                                item = (types.Ret.OK, i1)
                            case types.Ret.NO_MATCH:
                                item = types.Ret.NO_MATCH
                            case types.Ret.NOT_READY:
                                item = (types.Ret.NOT_READY, NOT_READY)
                            case ret:
                                logger.error(bad_return(ret))
                                item = (types.Ret.FAILED, 'Unknown internal error.')
                    else:
                        item = (types.Ret.FAILED, f'Unknown spellcasting class {cls}. For a list of known classes, use the `classes` command.')
        case {'rank': rank, 'category': category} if category in compound:
            item = await cast(CompoundAgent, ds[category]).random_async(rank=rank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': category} if category in ranked:
            item = await cast(RankedAgent, ds[category]).random_async(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': _, 'subrank': _, 'category': None, 'base': base} if base is not None:
            item = (
                types.Ret.INVALID,
                'Invalid parmeters specified, specifying a base item is only valid if you specify a category of armor or weapon.'
            )
        case {'rank': None, 'subrank': None, 'category': None}:
            while item is types.Ret.FAILED:
                args['rank'] = (await ds['category'].random_rank_async(mincost=mincost, maxcost=maxcost))
                attempt += 1

                match await roll(pool, ds, args, attempt=attempt):
                    case (types.Ret.OK, types.item.BaseItem() as i1):
                        item = i1
                    case (types.Ret.NO_MATCH, _):
                        continue
                    case (types.Ret.NOT_READY, _):
                        item = (types.Ret.NOT_READY, NOT_READY)
                    case (types.Ret.INVALID, str() as msg):
                        item = (types.Ret.INVALID, msg)
                    case (types.Ret.LIMITED, str() as msg):
                        item = (types.Ret.LIMITED, msg)
                    case (types.Ret.FAILED, str() as msg):
                        item = (types.Ret.FAILED, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': None, 'subrank': subrank, 'category': None}:
            item = (types.Ret.INVALID, 'Invalid parmeters specified, must specify a rank for the item.')
        case {'rank': rank, 'subrank': subrank, 'category': None}:
            while item is types.Ret.FAILED:
                args['category'] = await cast(CategoryAgent, ds['category']).random_async(rank=rank)

                attempt += 1

                match await roll(pool, ds, args, attempt=attempt):
                    case (types.Ret.OK, types.item.BaseItem() as i1):
                        item = i1
                    case (types.Ret.NO_MATCH, _):
                        continue
                    case (types.Ret.NOT_READY, _):
                        item = (types.Ret.NOT_READY, NOT_READY)
                    case (types.Ret.INVALID, str() as msg):
                        item = (types.Ret.INVALID, msg)
                    case (types.Ret.LIMITED, str() as msg):
                        item = (types.Ret.LIMITED, msg)
                    case (types.Ret.FAILED, str() as msg):
                        item = (types.Ret.FAILED, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        item = (types.Ret.FAILED, 'Unknown internal error.')
        case _:
            logger.warning(f'Invalid parameters when rolling magic item: {args}')
            item = (types.Ret.INVALID, 'Invalid parmeters specified.')

    match item:
        case types.Ret.NO_MATCH:
            return (types.Ret.NO_MATCH, NO_ITEMS_IN_COST_RANGE)
        case types.Ret.NOT_READY:
            return (types.Ret.NOT_READY, NOT_READY)
        case (types.Ret.OK, types.item.BaseItem() as i1):
            if i1.reroll is not None:
                return await _reroll_async(pool, ds, i1.reroll, mincost=mincost, maxcost=maxcost, attempt=attempt)
            elif mincost is not None and ((isinstance(i1.cost, str) and mincost == 0) or (not isinstance(i1.cost, str) and i1.cost < mincost)):
                return await roll(pool, ds, args['o_args'], attempt=attempt+1)
            elif maxcost is not None and (isinstance(i1.cost, str) or i1.cost > maxcost):
                return await roll(pool, ds, args['o_args'], attempt=attempt+1)
            else:
                return (types.Ret.OK, i1)
        case types.item.BaseItem() as i2:
            if i2.reroll is not None:
                return await _reroll_async(pool, ds, i2.reroll, mincost=mincost, maxcost=maxcost, attempt=attempt)
            elif i2.cost is None:
                logger.error(bad_return(i2))
                return (types.Ret.FAILED, 'Unknown internal error.')
            elif mincost is not None and ((isinstance(i2.cost, str) and mincost == 0) or (not isinstance(i2.cost, str) and i2.cost < mincost)):
                return await roll(pool, ds, args['o_args'], attempt=attempt+1)
            elif maxcost is not None and (isinstance(i2.cost, str) or i2.cost > maxcost):
                return await roll(pool, ds, args['o_args'], attempt=attempt+1)
            else:
                return (types.Ret.OK, i2)
        case (types.Ret() as r1, str() as msg) if r1 is not types.Ret.OK:
            return (r1, msg)
        case r2:
            logger.error(bad_return(r2))
            return (types.Ret.FAILED, 'Unknown internal error.')
