'''Cog for handling spells.'''

import logging

from pathlib import Path

from nextcord.ext import commands

from .cog import Cog
from .data.spell import SpellAgent
from .parser import Parser

NOT_READY = 'Spell data is not yet available, please try again later.'

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
})

logger = logging.getLogger(__name__)


class Spell(Cog):
    def __init__(self, bot, pool, renderer, logger=logger):
        db_path = Path.cwd() / 'spells.db'
        self.agent = SpellAgent(pool, db_path)

        super().__init__(bot, renderer, logger)

    @commands.command()
    async def spell(self, ctx, *args):
        '''Roll a random spell.

           Possible outcomes can be limited using the following options:

           - `class`: Only consider spells for the specified class. To
             list recognized classes, run `/r35 classes`.
           - `level`: Only consider spells for the specified level.
           - `tag`: Only consider spells with the specified school,
             subschool or descriptor. To list recognized tags, run
             `/r35 spelltags`.'''
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

        await ctx.trigger_typing()

        match await self.agent.random(
            level=args['level'],
            cls=args['cls'],
            tag=args['tag'],
        ):
            case False:
                await ctx.send(NOT_READY)
            case (False, msg):
                await ctx.send(msg)
            case (True, msg):
                match await self.render(msg):
                    case (True, msg):
                        await ctx.send(msg)
                    case (False, msg):
                        await ctx.send(msg)

    @commands.command()
    async def spelltags(self, ctx):
        '''List known spell tags.'''
        match await self.agent.tags():
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
        match await self.agent.classes():
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
