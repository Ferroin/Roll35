# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for handling magic items.'''

import asyncio
import logging
import random

from nextcord.ext import commands

from .cog import Cog
from .common import ret_async, bad_return
from .data.constants import RANK
from .parser import Parser
from .retcode import Ret

NOT_READY = 'Magic item data is not yet available, please try again later.'
NO_ITEMS_IN_COST_RANGE = 'No items found in requested cost range.'

MAX_REROLLS = 32
MAX_COUNT = 20

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
    'mincost': {
        'type': int,
        'names': [
            'mincost',
            'minc',
            'costmin',
            'cmin',
        ],
    },
    'maxcost': {
        'type': int,
        'names': [
            'maxcost',
            'maxc',
            'costmax',
            'cmax',
        ],
    },
    'count': {
        'type': int,
        'names': [
            'count',
            'co',
            'number',
            'num',
        ],
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
           - `mincost`: Specify a lower limit on the cost of the item.
           - `maxcost`: Specify a upper limit on the cost of the item.
           - `count`: Roll this many items using the same parameters.

           Parameters which are not specified are generated randomly.'''
        match ITEM_PARSER.parse(' '.join(args)):
            case (Ret.FAILED, msg):
                return await ctx.send(
                    'Invalid arguments for command `magicitem`: ' +
                    f'{ msg }\n' +
                    'See `/r35 help magicitem` for supported arguments.'
                )
            case (Ret.OK, a):
                args = a
            case ret:
                self.logger.error(bad_return(ret))
                return await ctx.send('Unknown internal error.')

        if args['count'] is None:
            args['count'] = 1

        match args:
            case {'count': c} if isinstance(c, int) and c > 0:
                items = roll_many(self.ds, c, {
                    k: v for k, v in args.items() if k != 'count'
                })

                await ctx.trigger_typing()

                results = []

                for item in asyncio.as_completed(items):
                    match await item:
                        case (ret, msg) if ret is not Ret.OK:
                            results.append(f'\nFailed to generate remaining items: { msg }')
                            break
                        case (Ret.OK, msg):
                            match await self.render(msg):
                                case (ret, msg) if ret is not Ret.OK:
                                    results.append(f'\nFailed to generate remaining items: { msg }')
                                    break
                                case (Ret.OK, msg):
                                    results.append(msg)
                                case ret:
                                    self.logger.error(bad_return(ret))
                                    results.append('\nFailed to generate remaining items: Unknown internal error.')
                                    break
                        case ret:
                            self.logger.error(bad_return(ret))
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
    async def mi(self, ctx, *args):
        '''Alias for `magicitem`.'''
        await self.magicitem(ctx, *args)

    @commands.command()
    async def categories(self, ctx):
        '''List known magic item categories.'''
        match await self.ds['category'].categories():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case cats:
                await ctx.send(
                    'The following item categories are recognized: ' +
                    f'`{ "`, `".join(sorted(list(cats))) }`'
                )

    @commands.command()
    async def slots(self, ctx):
        '''List known wondrous item slots.'''
        match await self.ds['wondrous'].slots():
            case Ret.NOT_READY:
                await ctx.send(NOT_READY)
            case Ret.NO_MATCH:
                await ctx.send('No slots found for wondrous items.')
            case slots:
                await ctx.send(
                    'The following wobndrous item slots are recognized: ' +
                    f'`{ "`, `".join(sorted(slots)) }`'
                )


async def _reroll(ds, attempt, path, mincost, maxcost):
    '''Reroll a magic item using the specified parameters.'''
    match path:
        case [category, slot, rank, subrank]:
            return await roll(
                ds,
                {
                    'rank': rank,
                    'subrnak': subrank,
                    'category': category,
                    'slot': slot,
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt+1
            )
        case [category, rank, subrank]:
            return await roll(
                ds,
                {
                    'rank': rank,
                    'subrnak': subrank,
                    'category': category,
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt+1
            )
        case _:
            logger.warning('Invalid reroll directive found while rolling for magic item: { path }.')
            return (
                Ret.FAILED,
                "Invalid reroll directive found while rolling for magic item."
            )


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
            case Ret.NOT_READY:
                failed = True
                await asyncio.sleep(1)
                break
            case Ret.NO_MATCH:
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
        if attempt >= 6:
            return (Ret.LIMITED, "Too many failed attempts to select enchantments.")
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
            Ret.OK,
            {
                'name': f'+{ pattern["bonus"] } ' +
                        f'{ etitle }{ base_item["name"] }',
                'cost': item_cost,
            }
        )


def roll_many(ds, count, args):
    '''Roll a number of magic items.

       Returns a list of coroutines that can be awaited to get the
       requested items.'''
    if not ds.ready:
        return [ret_async((Ret.NOT_READY, NOT_READY))]

    if count > MAX_COUNT:
        return [ret_async((Ret.LIMITED, f'Too many items requested, no more than { MAX_COUNT } may be rolled at a time.'))]

    coros = []

    for i in range(0, count):
        coros.append(roll(ds, args))

    return coros


async def roll(
            ds,
            args,
            attempt=0,
          ):
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
        return (Ret.LIMITED, 'Too many rerolls while attempting to generate item.')

    logger.debug(f'Rolling magic item with parameters { args }.')

    slots = await ds['wondrous'].slots()
    categories = await ds['category'].categories()

    if categories is Ret.NOT_READY or slots is Ret.NOT_READY:
        return (Ret.NOT_READY, NOT_READY)

    compound = (ds.types['compound'] | ds.types['compound-spell']) & categories
    compound_spell = ds.types['compound-spell'] & categories
    ordnance = ds.types['ordnance'] & categories
    ranked = ds.types['ranked'] & categories
    mincost = args['mincost']
    maxcost = args['maxcost']

    match args:
        case {'rank': 'minor', 'subrank': 'least', 'category': 'wondrous', 'slot': 'slotless'}:
            item = await ds['slotless'].random(rank='minor', subrank='least', mincost=mincost, maxcost=maxcost)
        case {'subrank': 'least'}:
            item = (Ret.INVALID, 'Only slotless wondrous items have a least subrank.')
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous', 'slot': slot} if slot in slots:
            item = await ds[slot].random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'slot': slot} if slot in slots:
            item = await ds[slot].random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': 'wondrous'}:
            slot = await ds['wondrous'].random()
            item = await ds[slot].random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': None} if category in ordnance:
            agent = ds[category]
            match await agent.random_pattern(rank=rank, subrank=subrank, allow_specific=True, mincost=mincost, maxcost=maxcost):
                case {'specific': specific}:
                    item = await agent.random_specific(*specific, mincost=mincost, maxcost=maxcost)
                case pattern:
                    match await agent.random_base():
                        case Ret.NOT_READY:
                            item = (Ret.NOT_READY, NOT_READY)
                        case base_item:
                            masterwork, bonus_cost = await agent.get_bonus_costs(base_item)
                            item = await _assemble_magic_item(
                                agent, base_item, pattern, masterwork, bonus_cost
                            )
        case {'rank': rank, 'subrank': subrank, 'category': category, 'base': base} if category in ordnance:
            agent = ds[category]
            pattern = await agent.random_pattern(rank=rank, subrank=subrank, allow_specific=False, mincost=mincost, maxcost=maxcost)

            match await agent.get_base(base):
                case Ret.NOT_READY:
                    item = (Ret.NOT_READY, NOT_READY)
                case (ret, msg) if ret is not Ret.OK:
                    item = (ret, msg)
                case (Ret.OK, base_item):
                    masterwork, bonus_cost = await agent.get_bonus_costs(base_item)
                    item = await _assemble_magic_item(
                        agent, base_item, pattern, masterwork, bonus_cost
                    )
                case ret:
                    logger.error(bad_return(ret))
                    item = (Ret.FAILED, 'Unknown internal error.')
        case {'rank': rank, 'subrank': subrank, 'category': category, 'cls': cls} if category in compound_spell:
            classes = await ds['classes'].classes()

            if not classes:
                item = (Ret.NOT_READY, NOT_READY)
            else:
                classes = set(classes) | ds['spell'].EXTRA_CLASS_NAMES
                if cls is None:
                    cls = random.choice(list(classes))

                if cls in classes:
                    item = await ds[category].random(rank=rank, cls=cls, mincost=mincost, maxcost=maxcost)
                else:
                    item = (Ret.FAILED, f'Unknown spellcasting class { cls }. For a list of known classes, use the `classes` command.')
        case {'rank': _, 'subrank': subrank, 'category': category} if category in compound and subrank is not None:
            item = (Ret.INVALID, f'Invalid parmeters specified, { category } does not take a subrank.')
        case {'rank': rank, 'category': category} if category in compound:
            item = await ds[category].random(rank=rank, mincost=mincost, maxcost=maxcost)
        case {'rank': rank, 'subrank': subrank, 'category': category} if category in ranked:
            item = await ds[category].random(rank=rank, subrank=subrank, mincost=mincost, maxcost=maxcost)
        case {'rank': _, 'subrank': _, 'category': None, 'base': base} if base is not None:
            item = (Ret.INVALID, 'Invalid parmeters specified, specifying a base item is only valid if you specify a category of armor or weapon.')
        case {'rank': _, 'subrank': _, 'category': None, 'cls': cls} if cls is not None:
            item = (Ret.INVALID, 'Invalid parmeters specified, specifying a class is only valid if you specify a category of scroll or wand.')
        case {'rank': None, 'subrank': None, 'category': None}:
            return await roll(
                ds,
                {
                    'rank': random.choice(RANK),
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt,
            )
        case {'rank': None, 'subrank': subrank, 'category': None}:
            item = (Ret.INVALID, 'Invalid parmeters specified, must specify a rank for the item.')
        case {'rank': rank, 'subrank': subrank, 'category': None}:
            if rank is None:
                rank = random.choice(RANK)

            category = await ds['category'].random(rank=rank)

            return await roll(
                ds,
                {
                    'rank': rank,
                    'subrank': subrank,
                    'category': category,
                    'mincost': mincost,
                    'maxcost': maxcost,
                },
                attempt,
            )
        case _:
            logger.warning(f'Invalid parameters when rolling magic item: { args }')
            item = (Ret.INVALID, 'Invalid parmeters specified.')

    match item:
        case Ret.NO_MATCH:
            return (Ret.NO_MATCH, NO_ITEMS_IN_COST_RANGE)
        case Ret.NOT_READY:
            return (Ret.NOT_READY, NOT_READY)
        case (ret, msg) if ret is not Ret.OK:
            return (ret, msg)
        case (Ret.OK, item):
            if mincost is not None and item['cost'] < mincost:
                return await roll(ds, args, attempt)
            elif maxcost is not None and item['cost'] > maxcost:
                return await roll(ds, args, attempt)
            else:
                return (Ret.OK, item)
        case {'reroll': reroll}:
            return await _reroll(ds, attempt, reroll, mincost, maxcost)
        case _:
            return (Ret.OK, item)
