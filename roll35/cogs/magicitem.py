# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import asyncio
import logging

from typing import Any, cast

from nextcord.ext import commands

from .. import types
from ..common import bad_return
from ..data.category import CategoryAgent
from ..data.wondrous import WondrousAgent
from ..parser import Parser, ParserEntry
from ..roller.magicitem import NOT_READY, roll_many_async

NO_ITEMS_IN_COST_RANGE = 'No items found in requested cost range.'

MAX_REROLLS = 128
MAX_COUNT = 32

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
    'level': ParserEntry(
        type=int,
        names=[
            'level',
            'lvl',
            'l',
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
                await ctx.send(
                    'Invalid arguments for command `magicitem`: ' +
                    f'{msg}\n' +
                    'See `/r35 help magicitem` for supported arguments.'
                )
            case (types.Ret.OK, a):
                parsed = cast(dict[str, Any], a)
            case ret:
                logger.error(bad_return(ret))
                await ctx.send('Unknown internal error.')

        match parsed:
            case {'count': c} if isinstance(c, int) and c > 0:
                items = roll_many_async(self.pool, self.ds, c, {
                    k: v for k, v in parsed.items() if k != 'count'
                })

                await ctx.trigger_typing()

                results = []

                for item in asyncio.as_completed(items):
                    match await item:
                        case (types.Ret.OK, msg):
                            match await self.render(cast(types.item.BaseItem, msg)):
                                case (r1, msg) if r1 is not types.Ret.OK:
                                    results.append(f'\nFailed to generate remaining items: {msg}')
                                    break
                                case (types.Ret.OK, msg) if isinstance(msg, str):
                                    results.append(msg)
                                case r2:
                                    logger.error(bad_return(r2))
                                    results.append('\nFailed to generate remaining items: Unknown internal error.')
                                    break
                        case (r1, msg) if isinstance(r1, types.Ret) and r1 is not types.Ret.OK and isinstance(msg, str):
                            results.append(f'\nFailed to generate remaining items: {msg}')
                            break
                        case r2:
                            logger.error(bad_return(r2))
                            results.append('\nFailed to generate remaining items: Unknown internal error.')
                            break

                await ctx.trigger_typing()

                msg = '\n'.join(results)

                await ctx.send(f'{len(results)} results: \n{msg}')
            case {'count': c} if c < 1:
                await ctx.send('Count must be an integer greater than 0.')
            case _:
                await ctx.send('Unrecognized value for count.')

    @commands.command()  # type: ignore
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
           - `level`: Specify the spell level to use when rolling wands
             or scrolls.
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

    @commands.command()  # type: ignore
    async def mi(self, ctx, *args):
        '''Alias for `magicitem`.'''
        await self._roll_magic_item(ctx, *args)

    async def _categories(self: MagicItem, ctx: commands.Context, /) -> None:
        match await cast(CategoryAgent, self.ds['category']).categories_async():
            case types.Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case set() as cats:
                await ctx.send(
                    'The following item categories are recognized: ' +
                    f'`{"`, `".join(sorted(list(cats)))}`'
                )
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    @commands.command()  # type: ignore
    async def categories(self, ctx, /):
        '''List known magic item categories.'''
        await self._categories(ctx)

    async def _slots(self: MagicItem, ctx: commands.Context, /) -> None:
        match await cast(WondrousAgent, self.ds['wondrous']).slots_async():
            case types.Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case list() as slots:
                await ctx.send(
                    'The following wobndrous item slots are recognized: ' +
                    f'`{"`, `".join(sorted(slots))}`'
                )
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    @commands.command()  # type: ignore
    async def slots(self, ctx, /) -> None:
        '''List known wondrous item slots.'''
        await self._slots(ctx)
