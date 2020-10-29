#!/usr/bin/env python3
# SPDX-License-Identifier: MITNFA
'''A discord bot for rolling magic items in Pathfinder 1e.'''

import logging
import os
import random
import sys

from copy import copy
from math import gcd
from types import SimpleNamespace
from typing import TypeVar, Any, Optional, Callable, \
                   Sequence, List, \
                   Mapping, Dict

import jinja2
import yaml

from discord.ext import commands

Item = TypeVar('Item')

TOKEN = os.getenv('DISCORD_TOKEN')
LOGLEVEL = os.getenv('LOG_LEVEL', default='INFO')

logging.basicConfig(level=LOGLEVEL)
logging.captureWarnings(True)

if not TOKEN:
    logging.error('No discord token specified')
    sys.exit(1)

####################
# Static Constants #
####################

KEYS = SimpleNamespace()
ITEMS = dict()
GENERIC_ERROR_LOG = 'Error while processing command {0} from {1} of {2}:'
JENV = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=False,
    enable_async=True,
)


############
# Function #
############

def compose_simple_itemlist(items: Sequence[Dict[str, Any]]) -> List[Item]:
    '''Compose a simple list of items for random.choice().

       This takes a list of {name, weight} pairs or a list of {name,
       cost, weight} triples and converts it to a list of either names
       or {name, cost} pairs where each name appears a number of times
       equal to it's weight.

       These lists allow a simple weighted selection of a random item
       by directly calling random.choice() on the list.'''
    ret = list()

    weights = [x['weight'] for x in items]
    total_slots = sum(weights)
    divisor = gcd(*weights)

    for item in items:
        i = copy(item)

        del i['weight']

        j = [i] * int(item['weight'] / divisor)
        ret += j

    logging.debug(f'Created simple list with {len(items)} items and {len(ret)} slots' +
                  f'(adjusted from {total_slots}).')

    return ret


def compose_compound_itemlist(items: Sequence[Dict[str, Any]]) -> Dict[str, List[Item]]:
    '''Compose a commpound list of items.

      This works similarly to compose_simple_itemlist(), but instead
      of a single weight value, each item is expected to have three
      weight values named minor, medium, and major. The return is a
      dictionary with keys with those names where the value of a key
      is a simple item list weighted by the values found in that key in
      the original items.

      This always assumes there's a 'cost' key, as we only use this for
      lists of items, not all random selection lists.

      This structure is used similarly to the simple lists produced by
      compose_simple_itemlist().'''
    ret = {
        'minor': list(),
        'medium': list(),
        'major': list(),
    }

    total = dict()
    divisor = dict()

    for i in ('minor', 'medium', 'major'):
        weights = [x[i] for x in items]
        total[i] = sum(weights)
        divisor[i] = gcd(*weights)

    for item in items:
        i = copy(item)

        del i['minor']
        del i['medium']
        del i['major']

        for j in ('minor', 'medium', 'major'):
            ret[j] += [i] * int(item[j] / divisor[j])

    logging.debug(f'Created compound list with {len(items)} items, ' +
                  f'{len(ret["minor"])} minor slots ' +
                  f'(adjusted from {total["minor"]}), ' +
                  f'{len(ret["medium"])} medium slots ' +
                  f'(adjusted from {total["medium"]}), ' +
                  f'and {len(ret["major"])} major slots ' +
                  f'(adjusted from {total["major"]}).')

    return ret


def create_flat_selector(data: Sequence[Item]) -> Callable[[], str]:
    '''Return a function that (safely) selects a random item form the `data` list.'''
    items = copy(data)

    if isinstance(items[0], str):
        def sel() -> str:
            '''Select an item.'''
            return random.choice(items)
    else:
        def sel() -> str:
            '''Select an item.'''
            return random.choice(items)['name']

    return sel


def create_grouped_selector(data: Mapping[Any, Item]) -> Callable[[Any], str]:
    '''Return a function that safely selects a random item from the indicated list in `data`.'''
    items = copy(data)

    if isinstance(items[list(items)[0]][0], str):
        def sel(group: Any) -> str:
            '''Select an item.'''
            return random.choice(items[group])
    else:
        def sel(group: Any) -> str:
            '''Select an item.'''
            return random.choice(items[group])['name']

    return sel


# pylint: disable=dangerous-default-value
def path_to_table(path: Sequence[str], _ref=ITEMS) -> Sequence[Item]:
    '''Get a specific table based on a sequence of keys.'''
    if len(path) > 1:
        return path_to_table(path[1:], _ref=_ref[path[0]])

    if len(path) == 1 and isinstance(_ref, list):
        return _ref

    return _ref[path[0]]
# pylint: enable=dangerous-default-value


def get_spell(level, cls="low"):
    '''Pick a random spell.

       Level indicates the spell level.

       cls indicates how to determine the spell level, and is either a
       class or the exact value 'low' (which uses the lowest level among
       all classes), 'high' (which uses the highest), or 'spellpage'
       (which uses the wizard or cleric level if it's one one of those
       lists, or the highest if not).'''
    # TODO: Add proper handling for rolling spells
    return f'<spell:{level}>'


##############
# Coroutines #
##############

async def render(item: str) -> str:
    '''Render the given string as a Jinja2 template.

      This compiles the string as a template, then renders it twice with
      the KEYS object passed in as the value `keys`, returning the result
      of the rendering.'''
    template1 = JENV.from_string(item)
    template2 = JENV.from_string(await template1.render_async(keys=KEYS))
    return await template2.render_async(keys=KEYS)


async def assemble_magic_armor(item: Item) -> str:
    '''Construct a piece of magic armor.'''
    # TODO: Actually roll for enchantments
    base = random.choice(ITEMS['armor']['base'])
    total_mod = item['bonus'] + sum(item['enchants'])
    cost = base['cost'] + ((total_mod ** 2) * 1000)
    ret = f'+{item["bonus"]} {base["name"]}'

    if item['enchants']:
        ret += ' with'
        index = 0

        for i in item['enchants']:
            ret += f' one +{i} enchantment'

            if index > 0:
                ret += ' and'

            index += 1

    ret += f' (cost: {cost}gp)'

    return ret


async def assemble_magic_weapon(item: Item) -> str:
    '''Construct a magic weapon.'''
    # TODO: Actually roll for enchantments and base item.
    total_mod = item['bonus'] + sum(item['enchants'])
    cost = 2000 * (total_mod ** 2)
    ret = f'+{item["bonus"]} Weapon'

    if item['enchants']:
        ret += ' with'
        index = 0

        for i in item['enchants']:
            ret += f' one +{i} enchantment'

            if index > 0:
                ret += ' and'

            index += 1

    ret += f' (cost: +{cost}gp)'

    return ret


async def roll_magic_item(path: Sequence[str]) -> str:
    '''Roll for a magic item.

       This function operates recursively as it walks the tree of items.'''
    item = random.choice(path_to_table(path))

    if 'reroll' in item:
        return await roll_magic_item(item['reroll'].split(':'))

    if 'type' in item:
        if item['type'] == 'armor':
            return await assemble_magic_armor(item)

        if item['type'] == 'weapon':
            return await assemble_magic_weapon(item)

    ret = await render(item['name'])

    if 'cost' in item:
        ret += f' (cost: {item["cost"]}gp)'

    return ret


#################
# Bot callbacks #
#################

BOT = commands.Bot(command_prefix='/')


@BOT.event
async def on_connect() -> None:
    '''Runs when we connect to Discord.

       This just logs the successful connection and does nothing else.'''
    logging.info(f'Successfully connected to Discord as {BOT.user.name}.')


@BOT.event
async def on_disconnect() -> None:
    '''Runs when we disconnect from Discord.

       This just logs the disconnect and does nothing else.'''
    logging.info('Disconnected from discord.')


@BOT.event
async def on_resume() -> None:
    '''Runs on session resumption.

       This just logs the state change and does nothing else.'''
    logging.info('Resumed session.')


@BOT.event
async def on_ready() -> None:
    '''Run when we are finally fully connected and online.

       This logs which guilds we are serving, and does nothing else.'''
    logging.info('Registered to the following guilds:')

    for guild in BOT.guilds:
        logging.info(f'  * {guild.name}')


@BOT.event
async def on_guild_join(guild) -> None:
    '''Run when we join a guild.

      This just logs the state change and does nothing else.'''
    logging.info(f'Joined {guild.name}.')


@BOT.event
async def on_guild_remove(guild) -> None:
    '''Run when we leave a guild.

      This just logs the state change and does nothing else.'''
    logging.info(f'Left {guild.name}...')


@BOT.event
async def on_message(message) -> None:
    '''Run when we see a new message.

       This fires off command processing for new messages.'''
    await BOT.process_commands(message)


@BOT.group(name='roll35')
@commands.guild_only()
async def roll35(ctx) -> None:
    '''Handler for the command prefix.

       This just returns an 'unrecognized command' message if the user
       did not run a known command.'''
    if ctx.invoked_subcommand is None:
        await ctx.send('Unrecognized command...')


@roll35.error
async def roll35_error(ctx, error: Exception) -> None:
    '''Run when the `roll35` function throws an error.'''
    if isinstance(error, commands.NoPrivateMessage):
        pass
    else:
        await ctx.send('An error occurred, check the BOT logs for more info.')
        logging.exception(GENERIC_ERROR_LOG.format(ctx.message, ctx.author.name, ctx.guild.name), exc_info=error)


@roll35.command(name='weapon', help='Roll for a random mundane weapon.')
@commands.guild_only()
async def weapon(ctx, *, specifier: Optional[str]) -> None:
    '''Run when the `/roll35 weapon` command is issued.

       This rolls a random mundane weapon, possibly limited by the
       parameters passed in the specifier string.

       The specifier string lets the user specify a set of tags to limit
       the list of weapons by.'''
    if specifier:
        tags = set(specifier.split())

        weapons = [x for x in ITEMS['weapon']['base'] if tags <= set(x['tags'])]
    else:
        weapons = ITEMS['weapon']['base']

    if weapons:
        item = random.choice(weapons)

        msg = await render(item['name'])

        if 'cost' in item:
            msg += f' (cost: {item["cost"]}gp)'
    else:
        msg = f"No items matching specified tags: '{specifier}'."

    await ctx.send(msg)


@weapon.error
async def weapon_error(ctx, error: Exception) -> None:
    '''Run when the `weapon` function throws an error.'''
    if isinstance(error, commands.UserInputError):
        await ctx.send('Invalid parameters for `/roll35 weapon` command, usage: ' +
                       '`/weapon [tags]`.')
    elif isinstance(error, commands.NoPrivateMessage):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, NotImplementedError):
        await ctx.send('Command not implemented.')
    else:
        await ctx.send('An error occurred, check the BOT logs for more info.')
        logging.exception(GENERIC_ERROR_LOG.format(ctx.message, ctx.author.name, ctx.guild.name), exc_info=error)


@roll35.command(name='armor', help='Roll for a random mundane shield or armor.')
@commands.guild_only()
async def armor(ctx, category: Optional[str]) -> None:
    '''Run when the `/roll35 armor` command is issued.

       This rolls a random mundane shield or armor, optionally restricted
       to a particular type.

       The category parameter optionally specifies a sub-category based
       on the 'type' key in the base armor item list.'''
    if category:
        items = [x for x in ITEMS['armor']['base'] if x['type'] == category]
    else:
        items = ITEMS['armor']['base']

    if items:
        item = random.choice(items)

        msg = await render(item['name'])

        if 'cost' in item:
            msg += f' (cost: {item["cost"]}gp)'
    else:
        msg = f"No items matching specified category: '{category}'."

    await ctx.send(msg)


@armor.error
async def armor_error(ctx, error: Exception) -> None:
    '''Run when the `armor` function throws an error.'''
    if isinstance(error, commands.UserInputError):
        await ctx.send('Invalid parameters for `/roll35 armor` command, usage: ' +
                       '`/armor [shield|light|medium|heavy]`.')
    elif isinstance(error, commands.NoPrivateMessage):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, NotImplementedError):
        await ctx.send('Command not implemented.')
    else:
        await ctx.send('An error occurred, check the BOT logs for more info.')
        logging.exception(GENERIC_ERROR_LOG.format(ctx.message, ctx.author.name, ctx.guild.name), exc_info=error)


@roll35.command(name='magic-item', help='Roll for a magic item')
@commands.guild_only()
async def magic_item(ctx, *, specifier: str) -> None:
    '''Run when the `/roll35 magic-item` command is issued.

       This rolls a random magic item, possibly limited by the parameters
       passed in the modifier string.

       The modifier string lets the user specify what category of item
       to roll (least/lesser/greater minor/medium/major) and what type
       of item to roll, but works without any of these specified and
       picks one item completely at randomain that case.'''
    params = specifier.split()

    if not params:
        raise commands.MissingArgumentError

    rank1 = None
    rank2 = None
    category = None
    subcategory = None

    for arg in params:
        if arg in ('least', 'lesser', 'greater') and rank1 is None:
            rank1 = arg
        elif arg in ('minor', 'medium', 'major') and rank2 is None:
            rank2 = arg
        elif arg in ('armor', 'weapon', 'potion', 'ring', 'rod',
                     'scroll', 'staff', 'wand', 'wondrous') and category is None:
            category = arg
        elif subcategory is None:
            subcategory = arg

    if category == 'wondrous':
        if subcategory not in {x['category'] for x in ITEMS['wondrous']} and subcategory is not None:
            await ctx.send('Invalid sub-category of wondrous item.')
            return
    elif subcategory is not None:
        await ctx.send('Subcategories can only be specified for wondrous items.')
        return

    if rank1 == 'least' and category != 'wondrous' and \
       subcategory != 'slotless' and rank2 != 'minor':
        await ctx.send('Only minor slotless wondrous items have a least type.')
        return

    if rank2 == 'minor' and category == 'rod':
        await ctx.send('Rods do not have a minor type.')
        return

    if rank2 == 'minor' and category == 'staff':
        await ctx.send('Staves do not have a minor type.')
        return

    if rank1 is None:
        rank1 = random.choice(('lesser', 'greater'))

    if category is None:
        category = random.choice(ITEMS['types'][rank2])['name']

    if category == 'wondrous':
        if subcategory is None:
            subcategory = random.choice(ITEMS['wondrous'])['category']

        category = subcategory

    if rank2 is None:
        rank2 = random.choice([x for x in list(ITEMS[category]) if x not in ('base', 'specific')])

    logging.info(f'Rolling {rank2} {rank1} {category} item.')

    item = await roll_magic_item([category, rank2, rank1])

    await ctx.send(item)


@magic_item.error
async def magic_item_error(ctx, error: Exception) -> None:
    '''Run when the `magic_item` function throws into an error.'''
    if isinstance(error, commands.UserInputError):
        await ctx.send('Invalid parameters for roll35 magic-item command, usage: ' +
                       '`/roll35 magic-item [[least|lesser|greater] minor|medium|major] ' +
                       '[armor|weapon|potion|ring|rod|scroll|staff|wand|wondrous]`.')
    elif isinstance(error, commands.NoPrivateMessage):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, NotImplementedError):
        await ctx.send('Command not implemented.')
    else:
        await ctx.send('An error occurred, check the BOT logs for more info.')
        logging.exception(GENERIC_ERROR_LOG.format(ctx.message, ctx.author.name, ctx.guild.name), exc_info=error)


@roll35.command(name='spell', help='Roll a random spell')
@commands.guild_only()
async def spell(ctx, specifier: str) -> None:
    '''Run when the `/roll35 spell` command is issued.

       This rolls for a random spell from our spell table using parameters
       specified by the command.

       The modifier string has two optional parameters:
       * `level:<level>` Used to specify a specific spell leve.
       * `class:<class>` Used to specify a particular class’s spell list should be used.'''
    return NotImplemented


@spell.error
async def spell_error(ctx, error: Exception) -> None:
    '''Run when the `spell` function throws an error.'''
    if isinstance(error, commands.UserInputError):
        await ctx.send('Invalid parameters for roll35 spell command, usage: ' +
                       '`/roll35 spell [level:<level>] [class:<class>]`.')
    elif isinstance(error, commands.NoPrivateMessage):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, NotImplementedError):
        await ctx.send('Command not implemented.')
    else:
        await ctx.send('An error occurred, check the BOT logs for more info.')
        logging.exception(GENERIC_ERROR_LOG.format(ctx.message, ctx.author.name, ctx.guild.name), exc_info=error)


#############
# Data prep #
#############

try:
    with open('./data.yaml', 'r') as source:
        DATA = yaml.safe_load(source.read())
except (IOError, OSError, yaml.YAMLError):
    logging.exception('Unable to load item data.')
    sys.exit(1)

for name, desc in DATA['keys'].items():
    if desc['type'] == 'flat':
        logging.debug(f'Composing keys.{name}')
        logging.debug(f'Created flat list with {len(desc["data"])} items.')

        selector = create_flat_selector(desc['data'])
    elif desc['type'] == 'flat proportional':
        logging.debug(f'Composing keys.{name}')
        a = compose_simple_itemlist(desc['data'])
        selector = create_flat_selector(a)
    elif desc['type'] == 'grouped':
        for g, d in desc['data']:
            logging.debug(f'Composing keys.{name}.{g}')
            logging.debug(f'Created flat list with {len(desc["data"][g])} items')

        selector = create_grouped_selector(desc['data'])
    elif desc['type'] == 'grouped proportional':
        k = dict()

        for g, d in desc['data'].items():
            logging.debug(f'Composing keys.{name}.{g}')
            k[g] = compose_simple_itemlist(d)

        selector = create_grouped_selector(k)
    else:
        logging.error(f'Invalid type for key with name {name}.')

    setattr(KEYS, name, selector)

ITEMS['types'] = dict()

for t in ('minor', 'medium', 'major'):
    logging.debug(f'Composing types.{t}')
    ITEMS['types'][t] = compose_simple_itemlist(DATA['types'][t])

for t in ('potion', 'scroll', 'wand'):
    logging.debug(f'Composing {t}')
    ITEMS[t] = compose_compound_itemlist(DATA[t])

logging.debug('Composing wondrous')
ITEMS['wondrous'] = compose_simple_itemlist(DATA['wondrous'])

for t in ('armor', 'weapon', 'ring',
          'rod', 'staff', 'belt', 'body',
          'chest', 'eyes', 'feet', 'hands',
          'head', 'headband', 'neck',
          'shoulders', 'wrists', 'slotless'):
    ITEMS[t] = dict()

    for u in ('minor', 'medium', 'major'):
        if u not in DATA[t]:
            continue

        ITEMS[t][u] = dict()

        for v in ('least', 'lesser', 'greater'):
            if v not in DATA[t][u]:
                continue

            logging.debug(f'Composing {t}.{u}.{v}')
            ITEMS[t][u][v] = compose_simple_itemlist(DATA[t][u][v])

for t in ('armor', 'weapon'):
    logging.debug(f'Composing base {t}')
    logging.debug(f'Created flat list with {len(DATA[t]["base"])} items')
    ITEMS[t]['base'] = DATA[t]['base']

ITEMS['armor']['specific'] = dict()

for key, value in DATA['armor']['specific'].items():
    ITEMS['armor']['specific'][key] = dict()

    for u in ('minor', 'medium', 'major'):
        ITEMS['armor']['specific'][key][u] = dict()

        for v in ('lesser', 'greater'):
            logging.debug(f'Composing armor.specific.{key}.{u}.{v}')
            ITEMS['armor']['specific'][key][u][v] = compose_simple_itemlist(value[u][v])

ITEMS['weapon']['specific'] = dict()

for u in ('minor', 'medium', 'major'):
    ITEMS['weapon']['specific'][u] = dict()

    for v in ('lesser', 'greater'):
        logging.debug(f'Composing weapon.specific.{u}.{v}')
        ITEMS['weapon']['specific'][u][v] = compose_simple_itemlist(DATA['weapon']['specific'][u][v])

ITEMS['armor']['enchantments'] = dict()

for t in ('armor', 'shield'):
    ITEMS['armor']['enchantments'][t] = dict()

    for u in (1, 2, 3, 4, 5):
        logging.debug(f'Composing +{u} {t} enchantments')
        ITEMS['armor']['enchantments'][t][u] = compose_simple_itemlist(DATA['armor']['enchantments'][t][u])

ITEMS['weapon']['enchantments'] = dict()

for t in ('melee', 'ranged', 'ammo'):
    ITEMS['weapon']['enchantments'][t] = dict()

    for u in (1, 2, 3, 4, 5):
        logging.debug(f'Composing +{u} {t} enchantments')
        ITEMS['weapon']['enchantments'][t][u] = compose_simple_itemlist(DATA['weapon']['enchantments'][t][u])

logging.debug('Composing spells')
logging.debug(f'Created flat list with {len(DATA["spell"])} items')
ITEMS['spell'] = DATA['spell']

KEYS.spell = get_spell

del DATA


##############
# Main Logic #
##############

BOT.run(TOKEN)
