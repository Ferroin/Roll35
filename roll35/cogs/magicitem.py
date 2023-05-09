# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Any, cast

from nextcord.ext import commands

from .. import types
from ..common import ret_async, bad_return
from ..data.category import CategoryAgent
from ..data.classes import ClassesAgent
from ..data.compound import CompoundAgent
from ..data.ordnance import OrdnanceAgent
from ..data.ranked import RankedAgent
from ..data.spell import SpellAgent
from ..data.wondrous import WondrousAgent
from ..log import log_call_async
from ..parser import Parser, ParserEntry

if TYPE_CHECKING:
    from collections.abc import Sequence, Mapping, Awaitable
    from concurrent.futures import Executor

    from ..data import DataSet

    MIResult = types.Result[types.Item]

NOT_READY = 'Magic item data is not yet available, please try again later.'
NO_ITEMS_IN_COST_RANGE = 'No items found in requested cost range.'

MAX_REROLLS = 32
MAX_COUNT = 20

ITEM_PARSER = Parser({
    'base': ParserEntry(
        type=str,
        names=[
            'base',
            'ba',
            'b',
        ],
        default=None,
    ),
    'category': ParserEntry(
        type=str,
        names=[
            'category',
            'cat',
            'ca',
            'c'
        ],
        default=None,
    ),
    'cls': ParserEntry(
        type=str,
        names=[
            'class',
            'cls',
            'cl',
        ],
        default=None,
    ),
    'rank': ParserEntry(
        type=types.Rank,
        names=[
            'rank',
            'ra',
            'r',
        ],
        default=None,
    ),
    'subrank': ParserEntry(
        type=types.Subrank,
        names=[
            'subrank',
            'subr',
            'srank',
            'sra',
            'sr',
            'su',
            's',
        ],
        default=None,
    ),
    'slot': ParserEntry(
        type=str,
        names=[
            'slot',
            'sl',
        ],
        default=None,
    ),
    'mincost': ParserEntry(
        type=int,
        names=[
            'mincost',
            'minc',
            'costmin',
            'cmin',
        ],
        default=0,
    ),
    'maxcost': ParserEntry(
        type=int,
        names=[
            'maxcost',
            'maxc',
            'costmax',
            'cmax',
        ],
        default=float('inf')
    ),
    'count': ParserEntry(
        type=int,
        names=[
            'count',
            'co',
            'number',
            'num',
        ],
        default=1,
    ),
})

logger = logging.getLogger(__name__)


class MagicItem(types.R35Cog):
    '''Roll35 cog for handling magic items.'''
    async def _roll_magic_item(self: MagicItem, ctx: commands.Context, *args: str) -> None:
        match ITEM_PARSER.parse(' '.join(args)):
            case (types.Ret.FAILED, msg):
                return await ctx.send(
                    'Invalid arguments for command `magicitem`: ' +
                    f'{ msg }\n' +
                    'See `/r35 help magicitem` for supported arguments.'
                )
            case (types.Ret.OK, a):
                parsed = cast(dict[str, Any], a)
            case ret:
                logger.error(bad_return(ret))
                return await ctx.send('Unknown internal error.')

        match parsed:
            case {'count': c} if isinstance(c, int) and c > 0:
                items = roll_many(self.bot.pool, self.ds, c, {
                    k: v for k, v in parsed.items() if k != 'count'
                })

                await ctx.trigger_typing()

                results = []

                for item in asyncio.as_completed(items):
                    match await item:
                        case (types.Ret.OK, msg):
                            match await self.render(cast(types.item.Item, msg)):
                                case (r1, msg) if r1 is not types.Ret.OK:
                                    results.append(f'\nFailed to generate remaining items: { msg }')
                                    break
                                case (types.Ret.OK, msg) if isinstance(msg, str):
                                    results.append(msg)
                                case r2:
                                    logger.error(bad_return(r2))
                                    results.append('\nFailed to generate remaining items: Unknown internal error.')
                                    break
                        case (r1, msg) if isinstance(r1, types.Ret) and r1 is not types.Ret.OK and isinstance(msg, str):
                            results.append(f'\nFailed to generate remaining items: { msg }')
                            break
                        case r2:
                            logger.error(bad_return(r2))
                            results.append('\nFailed to generate remaining items: Unknown internal error.')
                            break

                await ctx.trigger_typing()

                msg = '\n'.join(results)

                await ctx.send(f'{ len(results) } results: \n{ msg }')
            case {'count': c} if c < 1:
                await ctx.send('Count must be an integer greater than 0.')
            case _:
                await ctx.send('Unrecognized value for count.')

    @commands.command()
    async def magicitem(self, ctx, *args):
        '''Roll a random magic item.

           Possible outcomes can be limited using the following options:

           - `rank`: Specify the rank of the item to roll, one of
             `major`, `medium`, or `minor`.
           - `subrank`: Specify the sub-rank of the item to roll,
             one of `least`, `lsser`, or `greater`.
           - `category`: Specify the category of the item to roll. For
             a list of recognized values, run `/r35 categories`.
           - `slot`: Specify the slot of the item to roll for wondrous
             items. For a list of recognized values, run `/r35 slots`.
           - `class`: Specify the spellcasting class to use when
             rolling wands or scrolls. For a list of recognized classes,
             run `/r35 classes`. Only accepted if `category wand` or
             `category scroll` is specified.
           - `base`: Specify the base item to use when rolling magic
             armor or a magic weapon. Base items should be quoted
             if their names contain spaces (for example: `‘studded
             leather’` instead of `studded leather`). Only accepted if
             `category armor` or `category weapon` is specified. See also
             the `/r35 armor` and `/r35 weapon` commands for generating
             random mundane armor and weapons.
           - `mincost`: Specify a lower limit on the cost of the item.
           - `maxcost`: Specify a upper limit on the cost of the item.
           - `count`: Roll this many items using the same parameters.

           Parameters which are not specified are generated randomly.'''
        await self._roll_magic_item(ctx, *args)

    @commands.command()
    async def mi(self, ctx, *args):
        '''Alias for `magicitem`.'''
        await self._roll_magic_item(ctx, *args)

    async def _categories(self: MagicItem, ctx: commands.Context) -> None:
        match await cast(CategoryAgent, self.ds['category']).categories():
            case types.Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case cats:
                await ctx.send(
                    'The following item categories are recognized: ' +
                    f'`{ "`, `".join(sorted(list(cats))) }`'
                )

    @commands.command()
    async def categories(self, ctx):
        '''List known magic item categories.'''
        await self._categories(ctx)

    async def _slots(self: MagicItem, ctx: commands.Context) -> None:
        match await cast(WondrousAgent, self.ds['wondrous']).slots():
            case types.Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case types.Ret.NO_MATCH:
                await ctx.send('No slots found for wondrous items.')
            case slots:
                await ctx.send(
                    'The following wobndrous item slots are recognized: ' +
                    f'`{ "`, `".join(sorted(slots)) }`'
                )

    @commands.command()
    async def slots(self, ctx) -> None:
        '''List known wondrous item slots.'''
        await self._slots(ctx)


async def _reroll(
        pool: Executor,
        ds: DataSet,
        attempt: int,
        path: Sequence[str],
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
                attempt+1
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
                attempt+1
            )
        case _:
            logger.warning('Invalid reroll directive found while rolling for magic item: { path }.')
            return (
                types.Ret.FAILED,
                "Invalid reroll directive found while rolling for magic item."
            )


async def _assemble_magic_item(
        agent: OrdnanceAgent,
        base_item: types.item.OrdnanceBaseItem,
        pattern: types.item.OrdnancePattern,
        masterwork: int,
        bonus_cost: int,
        attempt: int = 0) -> \
        types.Result[types.item.SimpleItem]:
    '''Assemble a magic weapon or armor item.'''
    logger.debug(f'Assembling magic item with parameters: { base_item }, { pattern }, { masterwork }, { bonus_cost }')

    if pattern.bonus is None or pattern.enchants is None:
        raise ValueError('Cannot assemble magic item without bonus or enchants properties.')

    item_cost = cast(int | float, base_item.cost) + masterwork
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
        match await agent.random_enchant(group, ebonus, enchants, tags):
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
            return (types.Ret.LIMITED, "Too many failed attempts to select enchantments.")
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
        etitle = ''.join(list(map(lambda x: f'{ x } ', enchants)))
        return (
            types.Ret.OK,
            types.item.SimpleItem(
                name=f'+{ pattern.bonus } { etitle }{ base_item.name }',
                cost=item_cost,
            )
        )


def roll_many(pool: Executor, ds: DataSet, count: int, args: Mapping[str, Any]) -> Sequence[Awaitable[MIResult]]:
    '''Roll a number of magic items.

       Returns a list of coroutines that can be awaited to get the
       requested items.'''
    if not ds.ready:
        return [ret_async((types.Ret.NOT_READY, NOT_READY))]

    if count > MAX_COUNT:
        return [ret_async((types.Ret.LIMITED, f'Too many items requested, no more than { MAX_COUNT } may be rolled at a time.'))]

    coros = []

    for i in range(0, count):
        coros.append(roll(pool, ds, args))

    return coros


@log_call_async(logger, 'roll magic item')
async def roll(pool: Executor, ds: DataSet, args: Mapping[str, Any], attempt: int = 0) -> MIResult:
    '''Roll a magic item.'''
    args = {
        'rank': args.get('rank', None),
        'subrank': args.get('subrank', None),
        'category': args.get('category', None),
        'slot': args.get('slot', None),
        'base': args.get('base', None),
        'cls': args.get('cls', None),
        'mincost': args.get('mincost', 0),
        'maxcost': args.get('maxcost', float('inf')),
    }

    if attempt >= MAX_REROLLS:
        logger.warning(f'Recursion limit hit while rolling magic item: { args }')
        return (types.Ret.LIMITED, 'Too many rerolls while attempting to generate item.')

    slots = await cast(WondrousAgent, ds['wondrous']).slots()
    categories = await cast(CategoryAgent, ds['category']).categories()

    if categories is types.Ret.NOT_READY or slots is types.Ret.NOT_READY:
        return (types.Ret.NOT_READY, NOT_READY)

    compound = ds.types['compound'] & categories
    ordnance = ds.types['ordnance'] & categories
    ranked = ds.types['ranked'] & categories
    mincost = args['mincost']
    maxcost = args['maxcost']
    item: MIResult | types.Item | types.Ret = types.Ret.FAILED

    match args:
        case {'rank': types.Rank.MINOR, 'subrank': types.Subrank.LEAST, 'category': 'wondrous', 'slot': 'slotless'}:
            item = await cast(RankedAgent, ds['slotless']).random(rank='minor', subrank='least', mincost=mincost, maxcost=maxcost)
        case {'subrank': types.Subrank.LEAST}:
            item = (types.Ret.INVALID, 'Only slotless wondrous items have a least subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous', 'slot': slot} if slot in slots:
            item = await cast(RankedAgent, ds[slot]).random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'slot': slot} if slot in slots:
            item = await cast(RankedAgent, ds[slot]).random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous'}:
            slot = await cast(WondrousAgent, ds['wondrous']).random()
            item = await cast(RankedAgent, ds[slot]).random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': None} if category in ordnance:
            agent = cast(OrdnanceAgent, ds[category])
            match await agent.random_pattern(rank=rank, subrank=subrank, allow_specific=True, mincost=mincost, maxcost=maxcost):
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case types.Ret.NO_MATCH:
                    item = types.Ret.NO_MATCH
                case types.item.OrdnancePattern(specific=specific) if specific is not None:
                    item = await agent.random_specific(specific, mincost=mincost, maxcost=maxcost)
                case pattern:
                    match await agent.random_base():
                        case types.Ret.NOT_READY:
                            item = (types.Ret.NOT_READY, NOT_READY)
                        case base_item:
                            masterwork, bonus_cost = await agent.get_bonus_costs(base_item)
                            item = await _assemble_magic_item(
                                agent, base_item, pattern, masterwork, bonus_cost
                            )
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': base} if category in ordnance:
            agent = cast(OrdnanceAgent, ds[category])
            pattern = await agent.random_pattern(rank=rank, subrank=subrank, allow_specific=False, mincost=mincost, maxcost=maxcost)

            match await agent.get_base(pool, base):
                case types.Ret.NOT_READY:
                    item = (types.Ret.NOT_READY, NOT_READY)
                case (ret, msg) if ret is not types.Ret.OK:
                    item = (ret, msg)
                case (types.Ret.OK, base_item):
                    masterwork, bonus_cost = await agent.get_bonus_costs(base_item)
                    item = await _assemble_magic_item(
                        agent, base_item, pattern, masterwork, bonus_cost
                    )
                case ret:
                    logger.error(bad_return(ret))
                    item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': _, 'subrank': subrank, 'category': category} if category in compound and subrank is not None:
            item = (types.Ret.INVALID, f'Invalid parmeters specified, { category } does not take a subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': category, 'cls': cls} if cls is not None:
            classes = await cast(ClassesAgent, ds['classes']).classes()

            if not classes:
                item = (types.Ret.NOT_READY, NOT_READY)
            else:
                classes = set(classes) | cast(SpellAgent, ds['spell']).EXTRA_CLASS_NAMES

                if cls in classes:
                    match await cast(CompoundAgent, ds[category]).random(rank=rank, cls=cls, mincost=mincost, maxcost=maxcost):
                        case types.item.BaseItem() as i1:
                            item = (types.Ret.OK, i1)
                        case types.Ret.NOT_READY:
                            item = (types.Ret.NOT_READY, NOT_READY)
                        case ret:
                            logger.error(bad_return(ret))
                            item = (types.Ret.FAILED, 'Unknown internal error.')
                else:
                    item = (types.Ret.FAILED, f'Unknown spellcasting class { cls }. For a list of known classes, use the `classes` command.')
        case {'rank': rank, 'category': category} if category in compound:
            item = await cast(CompoundAgent, ds[category]).random(rank=rank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': category} if category in ranked:
            item = await cast(RankedAgent, ds[category]).random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': _, 'subrank': _, 'category': None, 'base': base} if base is not None:
            item = (
                types.Ret.INVALID,
                'Invalid parmeters specified, specifying a base item is only valid if you specify a category of armor or weapon.'
            )
        case {'rank': None, 'subrank': None, 'category': None}:
            while item is types.Ret.FAILED:
                args['rank'] = (await ds['category'].random_rank(mincost=mincost, maxcost=maxcost))
                attempt += 1

                match await roll(pool, ds, args, attempt):
                    case (types.Ret.OK, types.item.BaseItem() as i1):
                        item = i1
                    case (types.Ret.NO_MATCH, _):
                        continue
                    case (types.Ret.NOT_READY, _):
                        item = (types.Ret.NOT_READY, NOT_READY)
                    case (types.Ret.INVALID, msg) if isinstance(msg, str):
                        item = (types.Ret.INVALID, msg)
                    case (types.Ret.LIMITED, msg) if isinstance(msg, str):
                        item = (types.Ret.LIMITED, msg)
                    case (types.Ret.FAILED, msg) if isinstance(msg, str):
                        item = (types.Ret.FAILED, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        item = (types.Ret.FAILED, 'Unknown internal error.')
        case {'rank': None, 'subrank': subrank, 'category': None}:
            item = (types.Ret.INVALID, 'Invalid parmeters specified, must specify a rank for the item.')
        case {'rank': rank, 'subrank': subrank, 'category': None}:
            while item is types.Ret.FAILED:
                args['category'] = await cast(CategoryAgent, ds['category']).random(rank=rank)

                attempt += 1

                match await roll(pool, ds, args, attempt):
                    case (types.Ret.OK, types.item.BaseItem() as i1):
                        item = i1
                    case (types.Ret.NO_MATCH, _):
                        continue
                    case (types.Ret.NOT_READY, _):
                        item = (types.Ret.NOT_READY, NOT_READY)
                    case (types.Ret.INVALID, msg) if isinstance(msg, str):
                        item = (types.Ret.INVALID, msg)
                    case (types.Ret.LIMITED, msg) if isinstance(msg, str):
                        item = (types.Ret.LIMITED, msg)
                    case (types.Ret.FAILED, msg) if isinstance(msg, str):
                        item = (types.Ret.FAILED, msg)
                    case ret:
                        logger.error(bad_return(ret))
                        item = (types.Ret.FAILED, 'Unknown internal error.')
        case _:
            logger.warning(f'Invalid parameters when rolling magic item: { args }')
            item = (types.Ret.INVALID, 'Invalid parmeters specified.')

    match item:
        case types.Ret.NO_MATCH:
            return (types.Ret.NO_MATCH, NO_ITEMS_IN_COST_RANGE)
        case types.Ret.NOT_READY:
            return (types.Ret.NOT_READY, NOT_READY)
        case (types.Ret.OK, types.item.BaseItem() as i1):
            if i1.reroll is not None:
                return await _reroll(pool, ds, attempt, i1.reroll, mincost, maxcost)
            elif mincost is not None and i1.cost < mincost:
                return await roll(pool, ds, args, attempt+1)
            elif maxcost is not None and i1.cost > maxcost:
                return await roll(pool, ds, args, attempt+1)
            else:
                return (types.Ret.OK, i1)
        case types.item.BaseItem() as i2:
            if i2.reroll is not None:
                return await _reroll(pool, ds, attempt, i2.reroll, mincost, maxcost)
            elif mincost is not None and i2.cost < mincost:
                return await roll(pool, ds, args, attempt+1)
            elif maxcost is not None and i2.cost > maxcost:
                return await roll(pool, ds, args, attempt+1)
            else:
                return (types.Ret.OK, cast(types.Item, i2))
        case (r1, msg) if isinstance(r1, types.Ret) and r1 is not types.Ret.OK and isinstance(msg, str):
            return (r1, msg)
        case r2:
            logger.error(bad_return(r2))
            return (types.Ret.FAILED, 'Unknown internal error.')

    # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
    #
    # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
    raise RuntimeError
