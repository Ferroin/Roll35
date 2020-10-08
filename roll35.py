#!/usr/bin/env python3
'''A discord bot for rolling magic items in Pathfinder 1e.'''

import logging
import os
import random
import sys

from copy import copy
from types import SimpleNamespace
from typing import TypeVar, Any, Callable, \
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
ITEMS = {
    'types': dict(),
    'armor': dict(),
    'weapon': dict(),
    'potion': dict(),
    'ring': dict(),
    'rod': dict(),
    'scroll': dict(),
    'staff': dict(),
    'wand': dict(),
    'wondrous': dict(),
    'spell': dict(),
}
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
    # TODO: This should divide the weights by their GCD to better optimize the static table it produces.
    ret = list()

    logging.debug(f'Created simple list with {len(items)} items and {sum([x["weight"] for x in items])} slots.')

    for item in items:
        i = copy(item)

        del i['weight']

        j = [i] * item['weight']
        ret += j

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
    # TODO: This should divide the weights by their GCD to better optimize the static tables it produces.
    ret = {
        'minor': list(),
        'medium': list(),
        'major': list(),
    }

    logging.debug(f'Created compound list with {len(items)} items, ' +
                  f'{sum([x["minor"] for x in items])} minor slots, ' +
                  f'{sum([x["medium"] for x in items])} medium slots, ' +
                  f'and {sum([x["major"] for x in items])} major slots.')

    for item in items:
        i = copy(item)

        del i['minor']
        del i['medium']
        del i['major']

        for j in ('minor', 'medium', 'major'):
            ret[j] += [i] * item[j]

    return ret


def create_flat_selector(data: Sequence[Item]) -> Callable[[], Item]:
    '''Return a function that (safely) selects a random item form the `data` list.'''
    items = copy(data)

    def sel():
        '''Select an item.'''
        return random.choice(items)

    return sel


def create_grouped_selector(data: Mapping[Any, Item]) -> Callable[[Any], Item]:
    '''Return a function that safely selects a random item from the indicated list in `data`.'''
    items = copy(data)

    def sel(group):
        '''Select an item.'''
        return random.choice(items[group])

    return sel


# pylint: disable=dangerous-default-value
def path_to_table(path: Sequence[str], _ref=ITEMS) -> Sequence[Item]:
    '''Get a specific table based on a sequence of keys.'''
    if len(path) > 1:
        return path_to_table(path[1:], _ref=_ref[path[0]])
    return _ref[path[0]]
# pylint: enable=dangerous-default-value


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
    cost = base['cost'] + (total_mod ** 2)
    ret = f'+{item.bonus} {base.name}'

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
    cost = 2 * (total_mod ** 2)
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

    if hasattr(item, 'reroll'):
        return await roll_magic_item(item['reroll'].split(':'))

    if hasattr(item, 'type') and item['type'] == 'armor':
        return await assemble_magic_armor(item)

    if hasattr(item, 'type') and item['type'] == 'weapon':
        return await assemble_magic_weapon(item)

    return f'{await render(item["name"])} (cost: {item["cost"]}gp)'


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
    params = specifier.split(':')

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
        if subcategory not in {x.category for x in ITEMS['wondrous']} and subcategory is not None:
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

    if rank2 is None:
        rank2 = random.choice(('minor', 'medium', 'major'))

    if category is None:
        category = random.choice(ITEMS['types'][rank2])

    if category == 'wondrous':
        if subcategory is None:
            subcategory = random.choice(ITEMS['wondrous']).category

        category = subcategory

    item = await roll_magic_item([category, rank2, rank1])

    await ctx.send(item)


@magic_item.error
async def magic_item_error(ctx, error: Exception) -> None:
    '''Run when the `magic_item` function throws into an error.'''
    if isinstance(error, (commands.BadArgument, commands.MissingArgumentError)):
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
    if isinstance(error, (commands.BadArgument, commands.MissingArgumentError)):
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

for t in ('minor', 'medium', 'major'):
    logging.debug(f'Composing types.{t}')
    ITEMS['types'][t] = compose_simple_itemlist(DATA['types'][t])

for t in ('potion', 'scroll', 'wand'):
    logging.debug(f'Composing {t}')
    ITEMS[t] = compose_compound_itemlist(DATA[t])

for t in ('armor', 'weapon', 'ring',
          'rod', 'staff', 'belt', 'body',
          'chest', 'eyes', 'feet', 'hands',
          'head', 'headband', 'neck',
          'shoulders', 'wrsts', 'slotless'):
    ITEMS[t] = dict()

    for u in ('minor', 'medium', 'major'):
        if not hasattr(DATA[t], u):
            continue

        ITEMS[t][u] = dict()

        for v in ('least', 'lesser', 'greater'):
            if not hasattr(DATA[t][u], v):
                continue

            logging.debug(f'Composing {t}.{u}.{v}')
            ITEMS[t][u][v] = compose_simple_itemlist(DATA[t][u][v])

for t in ('armor', 'weapon'):
    logging.debug(f'Composing base {t}')
    logging.debug(f'Created flat list with {len(DATA[t]["base"])} items')
    ITEMS[t]['base'] = DATA[t]['base']

    for key, value in DATA[t]['specific']:
        for u in ('minor', 'medium', 'major'):
            ITEMS[k]['specific'][key][u] = dict()

            for v in ('lesser', 'greater'):
                logging.debug(f'Composing {t}.specific.{key}.{u}.{v}')
                ITEMS[t]['specific'][key][u][v] = compose_simple_itemlist(value[u][v])

for t in ('armor', 'shield'):
    for u in (1, 2, 3, 4, 5):
        logging.debug(f'Composing +{u} {t} enchantments')
        ITEMS['armor']['enchantments'][t][u] = compose_simple_itemlist(DATA['armor']['enchantments'][t][u])

for t in ('melee', 'ranged', 'ammo'):
    for u in (1, 2, 3, 4, 5):
        logging.debug(f'Composing +{u} {t} enchantments')
        ITEMS['weapon']['enchantments'][t][u] = compose_simple_itemlist(DATA['weapon']['enchantments'][t][u])

logging.debug('Composing spells')
logging.debug(f'Created flat list with {len(DATA["spells"])} items')
ITEMS['spells'] = DATA['spells']

del DATA


##############
# Main Logic #
##############

BOT.run(TOKEN)
