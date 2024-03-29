# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, Any, Literal, cast

from nextcord.ext import commands

from ..common import bad_return
from ..data.spell import SpellAgent
from ..data.classes import ClassesAgent
from ..log import log_call
from ..parser import Parser, ParserEntry
from ..types import R35Cog, Ret, Result
from ..types import Spell as SpellEntry

if TYPE_CHECKING:
    from collections.abc import Mapping, Awaitable

    from ..data import DataSet

NOT_READY = 'Spell data is not yet available, please try again later.'

MAX_COUNT = 32

SPELL_PARSER = Parser({
    'cls': ParserEntry(
        type=str,
        names=[
            'class',
            'cls',
            'c',
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
    'tag': ParserEntry(
        type=int,
        names=[
            'tag',
            't',
        ],
        default=None,
    ),
    'count': ParserEntry(
        type=int,
        names=[
            'cost',
            'co',
            'number',
            'num',
        ],
        default=1,
    ),
})

logger = logging.getLogger(__name__)


class Spell(R35Cog):
    '''Roll35 cog for handling spells.'''
    async def _spell(self: Spell, ctx: commands.Context, *args: str) -> None:
        match SPELL_PARSER.parse(' '.join(args)):
            case (Ret.FAILED, msg):
                await ctx.send(
                    'Invalid arguments for command `spell`: ' +
                    f'{ msg }\n' +
                    'See `/r35 help spell` for supported arguments.'
                )
                return
            case (Ret.OK, a):
                parsed = cast(dict[str, Any], a)
            case ret:
                logger.error(bad_return(ret))
                await ctx.send('Unknown internal error.')
                return

        match parsed:
            case {'count': c} if isinstance(c, int) and c > 0:
                if c > MAX_COUNT:
                    await ctx.send(f'Too many spells requested, no more than { MAX_COUNT } may be rolled at a time.')
                    return

                coros = []

                for i in range(0, c):
                    coros.append(roll_spell(self.ds, {
                        'level': parsed['level'],
                        'cls': parsed['cls'],
                        'tag': parsed['tag'],
                    }))

                await ctx.trigger_typing()

                results: list[str] = []

                for item in asyncio.as_completed(coros):
                    match await item:
                        case (Ret.OK, SpellEntry() as msg):
                            match await self.render(msg):
                                case (Ret.OK, str() as msg):
                                    results.append(msg)
                                case (r1, msg) if r1 is not Ret.OK:
                                    results.append(f'\nFailed to generate remaining items: { msg }')
                                    break
                                case r2:
                                    logger.error(bad_return(r2))
                                    results.append('\nFailed to generate remaining items: Unknown internal error.')
                                    break
                        case (r3, msg) if r3 is not Ret.OK:
                            results.append(f'\nFailed to generate remaining items: { msg }')
                            break
                        case r4:
                            logger.error(bad_return(r4))
                            results.append('\nFailed to generate remaining items: Unknown internal error.')
                            break

                await ctx.trigger_typing()

                msg = '\n'.join(results)

                await ctx.send(f'{ len(results) } results: \n{ msg }')
            case {'count': c} if c < 1:
                await ctx.send('Count must be an integer greater than 0.')
            case _:
                await ctx.send('Unrecognized value for count.')

    @commands.command()  # type: ignore
    async def spell(self, ctx, *args):
        '''Roll a random spell.

           Possible outcomes can be limited using the following options:

           - `class`: Only consider spells for the specified class. To
             list recognized classes, run `/r35 classes`.
           - `level`: Only consider spells for the specified level.
           - `tag`: Only consider spells with the specified school,
             subschool or descriptor. To list recognized tags, run
             `/r35 spelltags`.
           - `count`: Roll this many spells at once.'''
        await self._spell(ctx, *args)

    async def _spelltags(self: Spell, ctx: commands.Context, /) -> None:
        match await cast(SpellAgent, self.ds['spell']).tags_async():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No tags found for spells.')
            case list() as tags:
                await ctx.send(
                    'The following spell tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    @commands.command()  # type: ignore
    async def spelltags(self, ctx, /):
        '''List known spell tags.'''
        await self._spelltags(ctx)

    async def _classes(self: Spell, ctx: commands.Context, /) -> None:
        match await cast(ClassesAgent, self.ds['classes']).classes_async():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case list() as classes:
                await ctx.send(
                    'The following spellcasting classes are recognized: ' +
                    f'`{ "`, `".join(sorted(classes)) }`\n\n' +
                    'Additionally, the following special terms are recognized in places of a class name: \n' +
                    '- `minimum`: The class with the lowest level for each spell.\n' +
                    '- `random`: Select a class at random.\n' +
                    '- `arcane`: Select a random arcane class.\n' +
                    '- `divine`: Select a random divine class.\n' +
                    '- `occult`: Select a random occult class.\n' +
                    '- `spellpage`: Use spellpage evaluation rules when determining level.\n' +
                    '- `spellpage_arcane`: Same as `spellpage`, but only consider arcane classes.\n' +
                    '- `spellpage_divine`: Same as `spellpage`, but only consider divine classes.\n'
                )
            case ret:
                logger.warning(bad_return(ret))
                await ctx.send('Unknown internal error.')

    @commands.command()  # type: ignore
    async def classes(self, ctx, /):
        '''List known classes for spells.'''
        await self._classes(ctx)


@log_call(logger, 'roll spell')
def roll_spell(ds: DataSet, /, args: Mapping[str, Any]) -> Awaitable[Result[SpellEntry] | Literal[Ret.NOT_READY]]:
    '''Return a coroutine that will return a spell.'''
    return cast(SpellAgent, ds['spell']).random_async(**args)
