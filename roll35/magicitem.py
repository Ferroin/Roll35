# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling magic items.'''

import asyncio
import logging
import random

from nextcord.ext import commands

from .cog import Cog
from .data.types import RANK
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


class MagicItem(Cog):
    def __init__(self, bot, ds, renderer, logger=logger):
        super().__init__(bot, ds, renderer, logger)

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

        match await roll(self.ds, **args):
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
        match await self.ds['wondrous'].slots():
            case False:
                await ctx.send(NOT_READY)
            case []:
                await ctx.send('No slots found for wondrous items.')
            case slots:
                await ctx.send(
                    'The following wobndrous item slots are recognized: ' +
                    f'`{ "`, `".join(sorted(slots)) }`'
                )


async def _reroll(ds, path):
    '''Reroll a magic item using the specified parameters.'''
    match path:
        case [category, slot, rank, subrank]:
            return await roll(ds, category=category, slot=slot, rank=rank, subrank=subrank)
        case [category, rank, subrank]:
            return await roll(ds, category=category, rank=rank, subrank=subrank)
        case _:
            return (
                False,
                "Invalid reroll directive found while rolling for magic item."
            )


async def _finalize_roll(ds, item):
    '''Handle rerolls and ensure item is the right format.'''
    match item:
        case (False, msg):
            return (False, msg)
        case (True, item):
            return (True, item)
        case {'reroll': reroll}:
            return await _reroll(ds, reroll)
        case _:
            return (True, item)


async def _assemble_magic_item(agent, base_item, pattern, masterwork, bonus_cost, attempt=0):
    '''Assemble a magic weapon or armor item.'''
    logger.debug(f'Assembling magic item with parameters: { base_item }, { pattern }, { masterwork }, { bonus_cost }')

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

                if 'bonuscost' in enchant:
                    extra_ecost += enchant['bonuscost']

                if 'bonus' in enchant:
                    cbonus += enchant['bonus']
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
            True,
            {
                'name': f'+{ pattern["bonus"] } ' +
                        f'{ etitle }{ base_item["name"] }',
                'cost': item_cost,
            }
        )


async def roll(ds, rank=None, subrank=None, category=None,
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

    logger.debug(f'Rolling magic item with parameters { kwargs }.')

    slots = await ds['wondrous'].slots()

    if not slots:
        return await _finalize_roll(ds, (False, NOT_READY))

    match kwargs:
        case {'rank': 'minor', 'subrank': 'least', 'category': 'wondrous', 'slot': 'slotless'}:
            item = await ds['slotless'].random('minor', 'least')
        case {'subrank': 'least'}:
            item = (False, 'Only slotless wondrous items have a least subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous', 'slot': slot} if slot in slots:
            item = await ds[slot].random(rank, subrank)
        case {'rank': rank, 'subrank': subrank, 'slot': slot} if slot in slots:
            item = await ds[slot].random(rank, subrank)
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous'}:
            slot = await ds['wondrous'].random()
            item = await ds[slot].random(rank, subrank)
        case {'rank': rank, 'subrank': subrank, 'category': ('armor' | 'weapon') as category, 'base': None}:
            agent = ds[category]
            match await agent.random_pattern(rank, subrank, allow_specific=True):
                case {'specific': specific}:
                    item = await agent.random_specific(*specific)
                case pattern:
                    match await agent.random_base():
                        case False:
                            item = (False, NOT_READY)
                        case base_item:
                            match await agent.get_bonus_costs(base_item):
                                case False:
                                    item = (False, NOT_READY)
                                case (masterwork, bonus_cost):
                                    item = await _assemble_magic_item(
                                        agent, base_item, pattern, masterwork, bonus_cost
                                    )
        case {'rank': rank, 'subrank': subrank, 'category': ('armor' | 'weapon') as category, 'base': base}:
            agent = ds[category]
            pattern = await agent.random_pattern(rank, subrank, allow_specific=False)

            match await agent.get_base(base):
                case False:
                    item = (False, NOT_READY)
                case (False, msg):
                    item = (False, msg)
                case (True, base_item):
                    match await agent.get_bonus_costs(base_item):
                        case False:
                            item = (False, NOT_READY)
                        case (masterwork, bonus_cost):
                            item = await _assemble_magic_item(
                                agent, base_item, pattern, masterwork, bonus_cost
                            )
        case {'rank': rank, 'subrank': subrank, 'category': ('wand' | 'scroll') as category, 'cls': cls}:
            classes = await ds['classes'].classes()

            if not classes:
                item = (False, NOT_READY)
            else:
                classes = set(classes) | ds['spell'].EXTRA_CLASS_NAMES
                if cls is None:
                    cls = random.choice(list(classes))

                if cls in classes:
                    item = await ds[category].random(rank, cls)

                    if not item:
                        item = (False, NOT_READY)
                else:
                    item = (False, f'Unknown spellcasting class { cls }. For a list of known classes, use the `classes` command.')
        case {'rank': _, 'subrank': subrank, 'category': category} if category in COMPOUND_AGENTS and subrank is not None:
            item = (False, f'Invalid parmeters specified, { category } does not take a subrank.')
        case {'rank': rank, 'category': category} if category in COMPOUND_AGENTS:
            item = await ds[category].random(rank)
        case {'rank': rank, 'subrank': subrank, 'category': category} if category in RANKED_AGENTS:
            item = await ds[category].random(rank, subrank)
        case {'rank': _, 'subrank': _, 'category': None, 'base': base} if base is not None:
            item = (False, 'Invalid parmeters specified, specifying a base item is only valid if you specify a category of armor or weapon.')
        case {'rank': _, 'subrank': _, 'category': None, 'cls': cls} if cls is not None:
            item = (False, 'Invalid parmeters specified, specifying a class is only valid if you specify a category of scroll or wand.')
        case {'rank': None, 'subrank': None, 'category': None}:
            return await roll(ds, rank=random.choice(RANK))
        case {'rank': None, 'subrank': subrank, 'category': None}:
            item = (False, 'Invalid parmeters specified, must specify a rank for the item.')
        case {'rank': rank, 'subrank': subrank, 'category': None}:
            if rank is None:
                rank = random.choice(RANK)

            category = await ds['category'].random(rank)

            return await roll(
                ds,
                rank=rank,
                subrank=subrank,
                category=category,
            )
        case _:
            item = (False, 'Invalid parmeters specified.')

    if not item:
        item = (False, NOT_READY)

    return await _finalize_roll(ds, item)
