# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling spells.'''

import asyncio
import logging

from nextcord.ext import commands

from .cog import Cog
from .parser import Parser

NOT_READY = 'Spell data is not yet available, please try again later.'

MAX_COUNT = 20

SPELL_PARSER = Parser({
    'cls': {
        'names': [
            'class',
            'cls',
            'c',
        ],
    },
    'level': {
        'type': int,
        'names': [
            'level',
            'lvl',
            'l',
        ],
    },
    'tag': {
        'names': [
            'tag',
            't',
        ],
    },
    'count': {
        'type': int,
        'names': [
            'cost',
            'co',
            'number',
            'num',
        ],
    },
})

logger = logging.getLogger(__name__)


class Spell(Cog):
    def __init__(self, bot, ds, renderer, logger=logger):
        super().__init__(bot, ds, renderer, logger)

    @commands.command()
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
        match SPELL_PARSER.parse(' '.join(args)):
            case (False, msg):
                await ctx.send(
                    'Invalid arguments for command `spell`: ' +
                    f'{ msg }\n' +
                    'See `/r35 help spell` for supported arguments.'
                )
                return
            case (True, a):
                args = a

        if args['count'] is None:
            args['count'] = 1

        match args:
            case {'count': c} if isinstance(c, int) and c > 0:
                if c > MAX_COUNT:
                    await ctx.send(f'Too many spells requested, no more than { MAX_COUNT } may be rolled at a time.')
                    return

                coros = []

                for i in range(0, c):
                    coros.append(roll_spell(self.ds, {
                        'level': args['level'],
                        'cls': args['cls'],
                        'tag': args['tag'],
                    }))

                await ctx.trigger_typing()

                results = []

                for item in asyncio.as_completed(coros):
                    match await item:
                        case (False, msg):
                            results.append(f'\nFailed to generate remaining items: { msg }')
                            break
                        case (True, msg):
                            match await self.render(msg):
                                case (True, msg):
                                    results.append(msg)
                                case (False, msg):
                                    results.append(f'\nFailed to generate remaining items: { msg }')
                                    break

                await ctx.trigger_typing()

                msg = '\n'.join(results)

                await ctx.send(f'{ len(results) } results: \n{ msg }')
            case {'count': c} if c < 1:
                await ctx.send('Count must be an integer greater than 0.')
            case _:
                await ctx.send('Unrecognized value for count.')

    @commands.command()
    async def spelltags(self, ctx):
        '''List known spell tags.'''
        match await self.ds['spell'].tags():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No tags found for spells.')
            case tags:
                await ctx.send(
                    'The following spell tags are recognized: ' +
                    f'`{ "`, `".join(sorted(tags)) }`'
                )

    @commands.command()
    async def classes(self, ctx):
        '''List known classes for spells.'''
        match await self.ds['classes'].classes():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No classes found for spells.')
            case classes:
                await ctx.send(
                    'The following spellcasting classes are recognized: ' +
                    f'`{ "`, `".join(sorted(classes)) }`\n\n' +
                    'Additionally, the following special terms are recognized in places of a class name: \n' +
                    '- `minimum`: The class with the lowest level for each spell.\n' +
                    '- `random`: Select a class at random.\n' +
                    '- `arcane`: Select a random arcane class.\n' +
                    '- `divine`: Select a random divine class.\n' +
                    '- `spellpage`: Use spellpage evaluation rules when determining level.\n' +
                    '- `spellpage_arcane`: Same as `spellpage`, but only consider arcane classes.\n' +
                    '- `spellpage_divine`: Same as `spellpage`, but only consider divine classes.\n'
                )


def roll_spell(ds, args):
    '''Return a coroutine that will return a spell.'''
    return ds['spell'].random(**args)
