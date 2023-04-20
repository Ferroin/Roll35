'''Cog for handling magic items.'''

import asyncio
import logging
import random

from nextcord.ext import commands

from .cog import Cog
from .data.category import CategoryAgent
from .data.compound import CompoundAgent
from .data.ranked import RankedAgent
from .data.types import RANK
from .data.wondrous import WondrousAgent
from .parser import Parser

NOT_READY = 'Magic item data is not yet available, please try again later.'

RANKED_AGENTS = [
    'ring',
    'rod',
    'staff',
]

COMPOUND_AGENTS = [
    'potion',
    'scroll',
    'wand',
]

ITEM_PARSER = Parser({
    'base': {
        'names': [
            'base',
            'ba',
            'b',
        ],
    },
    'category': {
        'names': [
            'category',
            'cat',
            'ca',
            'c'
        ],
    },
    'cls': {
        'names': [
            'class',
            'cls',
            'cl',
        ],
    },
    'rank': {
        'names': [
            'rank',
            'ra',
            'r',
        ],
    },
    'subrank': {
        'names': [
            'subrank',
            'subr',
            'srank',
            'sra',
            'sr',
            'su',
            's',
        ],
    },
    'slot': {
        'names': [
            'slot',
            'sl',
        ]
    },
})

logger = logging.getLogger(__name__)


def get_bonus_costs(category, base):
    match category:
        case 'armor':
            return (150, 1000)
        case 'weapon':
            if 'double' in base['tags']:
                return (600, 4000)
            else:
                return (300, 2000)


class MagicItem(Cog):
    def __init__(self, bot, pool, renderer, logger=logger):
        self.agents = {
            'category': CategoryAgent(pool),
            'wondrous': WondrousAgent(pool),
        }

        for agent in RANKED_AGENTS:
            self.agents[agent] = RankedAgent(pool, agent)

        for agent in COMPOUND_AGENTS:
            self.agents[agent] = CompoundAgent(pool, agent)

        self.agents['wondrous'].early_load()

        for slot in self.agents['wondrous'].sslots():
            self.agents[slot] = RankedAgent(pool, slot)

        super().__init__(bot, renderer, logger)

    async def _reroll(self, path):
        '''Reroll a magic item using the specified parameters.'''
        match path:
            case [category, slot, rank, subrank]:
                return await self.roll(category=category, slot=slot, rank=rank, subrank=subrank)
            case [category, rank, subrank]:
                return await self.roll(category=category, rank=rank, subrank=subrank)
            case _:
                return (
                    False,
                    "Invalid reroll directive found while rolling for magic item."
                )

    async def _finalize_roll(self, item):
        '''Handle rerolls and ensure item is the right format.'''
        match item:
            case (False, msg):
                return (False, msg)
            case (True, item):
                return (True, item)
            case {'reroll': reroll}:
                return await self.reroll(reroll)
            case _:
                return (True, item)

    async def _assemble_magic_item(self, agent, base_item, pattern, masterwork, bonus_cost, attempt=0):
        '''Assemble a magic weapon or armor item.'''
        self.logger.debug(f'Assembling magic item with parameters: { base_item }, { pattern }, { masterwork }, { bonus_cost }')

        item_cost = base_item['cost'] + masterwork
        item_cost += (pattern['bonus'] ** 2) * bonus_cost
        group = base_item['type']
        if 'tags' in base_item:
            tags = set(base_item['tags'])
        else:
            tags = set()
        cbonus = 0
        extra_ecost = 0
        enchants = []
        failed = False

        for ebonus in pattern['enchants']:
            match await agent.random_enchant(group, ebonus, enchants, tags):
                case False:
                    failed = True
                    await asyncio.sleep(1)
                    break
                case None:
                    failed = True
                    break
                case enchant:
                    enchants.append(enchant['name'])

                    if 'cost' in enchant:
                        extra_ecost += enchant['cost']
                    else:
                        cbonus += ebonus

                    if 'add' in enchant:
                        tags = tags | set(enchant['add'])

                    if 'remove' in enchant:
                        tags = tags - set(enchant['remove'])

        if failed:
            if attempt >= 3:
                return (False, "Too many failed attempts to select enchantments.")
            else:
                attempt += 1
                self.logger.debug(
                    'Failed to generate valid enchantments for magic item, retrying (attempt { attempt }).'
                )
                return await self._assemble_magic_item(
                    agent, base_item, pattern, masterwork, bonus_cost,
                    attempt=attempt
                )
        else:
            item_cost += ((cbonus ** 2) * bonus_cost) + extra_ecost
            etitle = ''.join(list(map(lambda x: f'{ x } ', enchants)))
            return (
                True,
                {
                    'name': f'+{ pattern["bonus"] } ' +
                            f'{ etitle }{ base_item["name"] }',
                    'cost': item_cost,
                }
            )

    async def roll(self, rank=None, subrank=None, category=None,
                   slot=None, base=None, cls=None):
        '''Roll a magic item.'''
        kwargs = {
            'rank': rank,
            'subrank': subrank,
            'category': category,
            'slot': slot,
            'base': base,
            'cls': cls,
        }

        self.logger.debug(f'Rolling magic item with parameters { kwargs }.')

        slots = await self.agents['wondrous'].slots()

        if not slots:
            return await self._finalize_roll((False, NOT_READY))

        match kwargs:
            case {'rank': 'minor', 'subrank': 'least', 'category': 'wondrous', 'slot': 'slotless'}:
                item = await self.agents['slotless'].random('minor', 'least')
            case {'subrank': 'least'}:
                item = (False, 'Only slotless wondrous items have a least subrank.')
            case {'rank': rank, 'subrank': subrank, 'category': 'wondrous', 'slot': slot} if slot in slots:
                item = await self.agents[slot].random(rank, subrank)
            case {'rank': rank, 'subrank': subrank, 'slot': slot} if slot in slots:
                item = await self.agents[slot].random(rank, subrank)
            case {'rank': rank, 'subrank': subrank, 'category': 'wondrous'}:
                slot = await self.agents['wondrous'].random()
                item = await self.agents[slot].random(rank, subrank)
            case {'rank': 'minor', 'category': ('rod' | 'staff') as category}:
                item = (False, f'{ category } items do not have a minor rank.')
            case {'rank': rank, 'subrank': subrank, 'category': ('armor' | 'weapon') as category, 'base': None}:
                agent = self.bot.get_cog(category.capitalize()).agent
                match await agent.random_pattern(rank, subrank, allow_specific=True):
                    case {'specific': specific}:
                        item = await agent.random_specific(*specific)
                    case pattern:
                        match await agent.random_base():
                            case False:
                                item = (False, NOT_READY)
                            case base_item:
                                masterwork, bonus_cost = get_bonus_costs(category, base_item)

                                item = await self._assemble_magic_item(
                                    agent, base_item, pattern, masterwork, bonus_cost
                                )
            case {'rank': rank, 'subrank': subrank, 'category': ('armor' | 'weapon') as category, 'base': base}:
                agent = self.bot.get_cog(category.capitalize()).agent
                pattern = await agent.random_pattern(rank, subrank, allow_specific=False)

                match await agent.get_base(base):
                    case False:
                        item = (False, NOT_READY)
                    case (False, msg):
                        item = (False, msg)
                    case (True, base_item):
                        masterwork, bonus_cost = get_bonus_costs(category, base_item)

                        item = await self._assemble_magic_item(
                            agent, base_item, pattern, masterwork, bonus_cost
                        )
            case {'rank': rank, 'subrank': subrank, 'category': ('wand' | 'scroll') as category, 'cls': cls}:
                spell_agent = self.bot.get_cog('Spell').agent
                classes = await spell_agent.classes()

                if not classes:
                    item = (False, NOT_READY)
                else:
                    if cls is None:
                        cls = random.choice(classes)

                    if cls in classes:
                        item = await self.agents[category].random(rank)

                        if not item:
                            item = (False, NOT_READY)
                        else:
                            item['spell']['cls'] = cls
                    else:
                        item = (False, f'Unknown spellcasting class { cls }. For a list of known classes, use the `classes` command.')
            case {'rank': _, 'subrank': subrank, 'category': category} if category in COMPOUND_AGENTS and subrank is None:
                item = (False, f'Invalid parmeters specified, { category } does not take a subrank.')
            case {'rank': rank, 'category': category} if category in COMPOUND_AGENTS:
                item = await self.agents[category].random(rank)
            case {'rank': rank, 'subrank': subrank, 'category': category} if category in RANKED_AGENTS:
                item = await self.agents[category].random(rank, subrank)
            case {'rank': _, 'subrank': _, 'category': None, 'base': base} if base is not None:
                item = (False, 'Invalid parmeters specified, specifying a base item is only valid if you specify a category of armor or weapon.')
            case {'rank': _, 'subrank': _, 'category': None, 'cls': cls} if cls is not None:
                item = (False, 'Invalid parmeters specified, specifying a class is only valid if you specify a category of scroll or wand.')
            case {'rank': None, 'subrank': None, 'category': None}:
                return await self.roll(rank=random.choice(RANK))
            case {'rank': None, 'subrank': subrank, 'category': None}:
                item = (False, 'Invalid parmeters specified, must specify a rank for the item.')
            case {'rank': rank, 'subrank': subrank, 'category': None}:
                if rank is None:
                    rank = random.choice(RANK)

                category = await self.agents['category'].random(rank)

                return await self.roll(
                    rank=rank,
                    subrank=subrank,
                    category=category,
                )
            case _:
                item = (False, 'Invalid parmeters specified.')

        if not item:
            item = (False, NOT_READY)

        return await self._finalize_roll(item)

    async def load_agent_data(self):
        coros = []

        for agent in self.agents:
            coros.append(self.agents[agent].load_data())

        await asyncio.gather(*coros)

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

           Parameters which are not specified are generated randomly.'''
        match ITEM_PARSER.parse(' '.join(args)):
            case (False, msg):
                await ctx.send(
                    'Invalid arguments for command `magicitem`: ' +
                    f'{ msg }\n' +
                    'See `/r35 help magicitem` for supported arguments.'
                )
                return
            case (True, a):
                args = a

        match await self.roll(**args):
            case (False, msg):
                await ctx.send(msg)
            case (True, msg):
                match await self.render(msg):
                    case (True, msg):
                        await ctx.send(msg)
                    case (False, msg):
                        await ctx.send(msg)

    @commands.command()
    async def mi(self, ctx, *args):
        '''Alias for `magicitem`.'''
        await self.magicitem(ctx, *args)

    @commands.command()
    async def categories(self, ctx):
        '''List known magic item categories.'''
        await ctx.send('The following item categories are recognized: ' +
                       '`armor`, `weapon`, `potion`, `ring`, `rod`, ' +
                       '`scroll`, `staff`, `wand`, `wondrous`')

    @commands.command()
    async def slots(self, ctx):
        '''List known wondrous item slots.'''
        match await self.agents['wondrous'].slots():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No slots found for wondrous items.')
            case slots:
                await ctx.send(
                    'The following wobndrous item slots are recognized: ' +
                    f'`{ "`, `".join(sorted(slots)) }`'
                )
