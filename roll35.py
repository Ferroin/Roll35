#!/usr/bin/env python3
# SPDX-License-Identifier: MITNFA
'''A discord bot for rolling magic items in Pathfinder 1e.'''

import asyncio
import logging
import os
import random
import sys

from copy import copy
from types import SimpleNamespace
from typing import TypeVar, Any, Optional, Callable, \
                   Sequence, List, \
                   Mapping, Dict

import aiosqlite
import jinja2
import yaml

from discord.ext import commands

Item = TypeVar('Item')

TOKEN = os.getenv('DISCORD_TOKEN')
LOGLEVEL = os.getenv('LOG_LEVEL', default='INFO')
DATAPATH = os.getenv('DATA_PATH', default='/data')

logging.basicConfig(level=LOGLEVEL,
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s')
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
SPELL_LOCK = asyncio.Lock()
SPELL_PATH = os.path.join(DATAPATH, 'spells.sqlite3')
JENV = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=False,
    enable_async=True,
)


##############
# Exceptions #
##############

class NoValidSpell(Exception):
    '''Raised by the get_spell() coroutine if no valid spell can be found.'''


############
# Function #
############

def compose_items(items: Sequence[Mapping[str, Any]]) -> Dict[str, List[Item]]:
    '''Convert a compound weighted list into a set of weighted lists.'''
    ret = {
        'minor': list(),
        'medium': list(),
        'major': list()
    }

    for item in items:
        for group in ('minor', 'medium', 'major'):
            ret[group].append({
                'weight': item[group],
                **item
            })

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


def create_flat_proportional_selector(data: Sequence[Item]) -> Callable[[], str]:
    '''Return a function that (safely) selects a weighted random item from the `data` list.'''
    items = copy(data)
    weights = [x['weight'] for x in items]

    def sel() -> str:
        '''Select an item.'''
        return random.choices(items, weights=weights)[0]['name']

    return sel


def create_grouped_selector(data: Mapping[Any, Sequence[Item]]) -> Callable[[Any], str]:
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


def create_grouped_proportional_selector(data: Mapping[Any, Sequence[Item]]) -> Callable[[Any], str]:
    '''Return a function that (safely) selects a weighted random item from the indicated list in `data`.'''
    items = copy(data)
    weights = dict()

    for group, entries in items.items():
        weights[group] = [x['weight'] for x in entries]

    def sel(group: Any) -> str:
        '''Select an item.'''
        return random.choices(items[group], weights=weights[group])[0]['name']

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


##############
# Coroutines #
##############

async def get_spell(level: Optional[int] = None, cls: str = "minimum", tag: Optional[str] = None) -> str:
    '''Pick a random spell.

       Level indicates the spell level.

       cls indicates how to determine the spell level, and is either a
       class or the exact value 'minimum' (which uses the lowest level among
       all classes), 'maximum' (which uses the highest), or 'spellpage'
       (which uses the wizard or cleric level if it's one one of those
       lists, or the highest if not).'''
    if cls == 'spellpage':
        cls = random.choice(('spellpage_divine', 'spellpage_arcane'))

    limit_options = None

    async with SPELL_LOCK:
        async with aiosqlite.connect(f'file:{SPELL_PATH}?mode=ro', uri=True) as spells:
            spells.row_factory = aiosqlite.Row

            async with spells.execute('''SELECT data FROM extra WHERE id = 'classes';''') as cur:
                classes = await cur.fetchall()

                if cls not in classes[0]['data'].split():
                    raise NoValidSpell

            if level is not None:
                async with spells.execute(f'''SELECT * FROM spells WHERE {cls} = {level};''') as cur:
                    options = await cur.fetchall()
            else:
                async with spells.execute(f'''SELECT * FROM spells WHERE {cls} IS NOT NULL;''') as cur:
                    options = await cur.fetchall()

            if tag is not None:
                async with spells.execute(f'''SELECT * FROM tagmap WHERE tagmap MATCH '{tag}';''') as cur:
                    limit_options = {x['name'] for x in await cur.fetchall()}

    if limit_options is not None:
        options = [x for x in options if x['name'] in limit_options]

    if not options:
        raise NoValidSpell

    result = random.choice(options)

    if cls == 'minimum':
        result_cls = result['minimum_cls']
    elif cls == 'spellpage_divine':
        result_cls = result['spellpage_divine_cls']
    elif cls == 'spellpage_arcane':
        result_cls = result['spellpage_arcane_cls']
    else:
        result_cls = cls

    caster_level = ITEMS['spell']['map'][result_cls]['levels'][result[result_cls]]

    return f'{result["name"]} ({result_cls} CL {caster_level})'


async def prep_spell_db(data: Mapping[str, Any]) -> None:
    '''Populate the spell database based on the given data.

       This gets run at startup if the data file differs from the spell database.'''
    columns = list(data['map'].keys())
    classes = columns + ['minimum', 'spellpage_arcane', 'spellpage_divine']

    async with SPELL_LOCK:
        async with aiosqlite.connect(f'file:{SPELL_PATH}?mode=rwc', uri=True) as spells:
            await spells.executescript(f'''DROP TABLE IF EXISTS spells;
                                           DROP TABLE IF EXISTS tagmap;
                                           DROP TABLE IF EXISTS extra;
                                           CREATE TABLE spells(name TEXT,
                                                               link TEXT,
                                                               {' INTEGER, '.join(columns)} INTEGER,
                                                               minimum INTEGER,
                                                               spellpage_arcane INTEGER,
                                                               spellpage_divine INTEGER,
                                                               minimum_cls TEXT,
                                                               spellpage_arcane_cls TEXT,
                                                               spellpage_divine_cls TEXT);
                                           CREATE VIRTUAL TABLE tagmap USING fts5(name UNINDEXED,
                                                                                  tags,
                                                                                  columnsize='0',
                                                                                  detail='none');
                                           CREATE TABLE extra(id TEXT, data TEXT);
                                           INSERT INTO extra (id, data) VALUES ('classes', '{' '.join(classes)}');
                                           VACUUM;''')
            await spells.commit()

            for item in data['data']:
                logging.debug(f'Entering spell: {item["name"]}')

                cmd = f'''INSERT INTO spells (name, link, {', '.join(columns)}, minimum, spellpage_arcane, spellpage_divine,
                          minimum_cls, spellpage_arcane_cls, spellpage_divine_cls)
                          VALUES ("{item['name']}", "{item['link']}", '''

                values = []
                minimum = 9
                min_cls = ''
                spellpage_arcane = 'NULL'
                spellpage_arcane_fixed = False
                spellpage_arcane_cls = 'NULL'
                spellpage_divine = 'NULL'
                spellpage_divine_fixed = False
                spellpage_divine_cls = 'NULL'

                for cls in columns:
                    lvl = 'NULL'

                    if cls in item['level']:
                        lvl = item['level'][cls]
                    elif 'copy' in data['map'][cls]:
                        if data['map'][cls]['copy'] in item['level']:
                            if 'max_level' in data['map'][cls] and \
                               item['level'][data['map'][cls]['copy']] <= data['map'][cls]['max_level']:
                                lvl = item['level'][data['map'][cls]['copy']]
                            else:
                                lvl = item['level'][data['map'][cls]['copy']]
                    elif 'merge' in data['map'][cls]:
                        merge = set(data['map'][cls]['merge']) & set(item['level'].keys())
                        if len(merge) == 1:
                            lvl = item['level'][list(merge)[0]]
                        elif len(merge) > 1:
                            lvl = min([item['level'][x] for x in merge])

                    if lvl != 'NULL':
                        if not isinstance(lvl, int):
                            raise TypeError

                        if lvl <= minimum:
                            minimum = lvl

                            if min_cls and \
                               ITEMS['spell']['map'][cls]['levels'][lvl] < \
                               ITEMS['spell']['map'][min_cls]['levels'][lvl]:
                                min_cls = cls
                            else:
                                min_cls = cls

                        if data['map'][cls]['type'] == 'divine' and not spellpage_divine_fixed:
                            if cls == 'cleric':
                                spellpage_divine = lvl
                                spellpage_divine_fixed = True
                                spellpage_divine_cls = 'cleric'
                            elif spellpage_divine == 'NULL' or lvl <= spellpage_divine:
                                spellpage_divine = lvl

                                if spellpage_divine_cls != 'NULL' and \
                                   ITEMS['spell']['map'][cls]['levels'][lvl] < \
                                   ITEMS['spell']['map'][spellpage_divine_cls]['levels'][lvl]:
                                    spellpage_divine_cls = cls
                                else:
                                    spellpage_divine_cls = cls

                        if data['map'][cls]['type'] == 'arcane' and not spellpage_arcane_fixed:
                            if cls == 'wizard':
                                spellpage_arcane = lvl
                                spellpage_arcane_fixed = True
                                spellpage_arcane_cls = 'wizard'
                            elif spellpage_arcane == 'NULL' or lvl <= spellpage_arcane:
                                spellpage_arcane = lvl

                                if spellpage_arcane_cls != 'NULL' and \
                                   ITEMS['spell']['map'][cls]['levels'][lvl] < \
                                   ITEMS['spell']['map'][spellpage_arcane_cls]['levels'][lvl]:
                                    spellpage_arcane_cls = cls
                                else:
                                    spellpage_arcane_cls = cls

                    values.append(str(lvl))

                min_cls = f"'{min_cls}'"

                if spellpage_arcane_cls != 'NULL':
                    spellpage_arcane_cls = f"'{spellpage_arcane_cls}'"

                if spellpage_divine_cls != 'NULL':
                    spellpage_divine_cls = f"'{spellpage_divine_cls}'"

                cmd += ', '.join(values)
                cmd += f''', {minimum}, {spellpage_arcane}, {spellpage_divine}, {min_cls},
                           {spellpage_arcane_cls}, {spellpage_divine_cls});
                           INSERT INTO tagmap (name, tags) VALUES ("{item['name']}", "{' '.join(item['tags'])}");'''
                await spells.executescript(cmd)

            await spells.commit()


async def render(item: str, **extra) -> str:
    '''Render the given string as a Jinja2 template.

      This compiles the string as a template, then renders it twice with
      the KEYS object passed in as the value `keys`, returning the result
      of the rendering.'''
    template1 = JENV.from_string(item)
    template2 = JENV.from_string(await template1.render_async(keys=KEYS, **extra))
    return await template2.render_async(keys=KEYS, **extra)


async def assemble_magic_armor(item: Item) -> str:
    '''Construct a piece of magic armor.'''
    base = random.choice(ITEMS['armor']['base'])
    cost = base['cost'] + ((item['bonus'] ** 2) * 1000) + 150
    ret = f'+{item["bonus"]} {base["name"]}'

    tags = set(base['tags'])
    enchants = list()

    for enchant in item['enchants']:
        possible = ITEMS['armor']['enchantments'][base['type']][enchant]

        for possibility in possible:
            if possibility in enchants:
                possible.remove(possibility)
            elif 'limit' in possibility:
                if len(set(possibility['limit']) & tags) == 0:
                    possible.remove(possibility)
            elif 'exclude' in possibility:
                if len(set(possibility['exclude']) & {x['name'] for x in enchants}) != 0:
                    possible.remove(possibility)

        if not possible:
            return assemble_magic_armor(item)

        weights = [x['weight'] for x in possible]

        result = random.choices(possible, weights=weights)[0]

        enchants.append(result)

        ret = f'{result["name"]} {ret}'

        if 'cost' in result:
            cost += result['cost']
        else:
            cost += ((enchant ** 2) * 1000)

    ret += f' (cost: {cost}gp)'

    return ret


async def assemble_magic_weapon(item: Item) -> str:
    '''Construct a magic weapon.'''
    base = random.choice(ITEMS['weapon']['base'])

    if 'double' in base['tags']:
        masterwork = 600
    elif base['type'] == 'ammo':
        masterwork = 6 * base.get('count', 1)
    else:
        masterwork = 300

    cost = base['cost'] + masterwork + ((item['bonus'] ** 2) * (4000 if 'double' in base['tags'] else 2000))
    ret = f'+{item["bonus"]} {base["name"]}'

    tags = set(base['tags'])
    enchants = list()

    for enchant in item['enchants']:
        possible = ITEMS['weapon']['enchantments'][base['type']][enchant]

        for possibility in possible:
            if possibility in enchants:
                possible.remove(possibility)
            elif 'limit' in possibility:
                if 'only' in possibility['limit']:
                    if len(set(possibility['limit']['only']) & tags) == 0:
                        possible.remove(possibility)
                elif 'not' in possibility['limit']:
                    if len(set(possibility['limit']['not']) & tags) != 0:
                        possible.remove(possibility)
            elif 'exclude' in possibility:
                if len(set(possibility['exclude']) & {x['name'] for x in enchants}) != 0:
                    possible.remove(possibility)

        if not possible:
            return assemble_magic_weapon(item)

        weights = [x['weight'] for x in possible]

        result = random.choices(possible, weights=weights)[0]

        enchants.append(result)

        if 'add' in result:
            tags |= set(result['add'])

        if 'remove' in result:
            tags -= set(result['remove'])

        ret = f'{result["name"]} {ret}'

        if 'cost' in result:
            cost += result['cost'] * 2 if 'double' in tags else result['cost']
        else:
            cost += ((enchant ** 2) * 4000 if 'double' in tags else 2000)

    ret += f' (cost: {cost}gp)'

    return ret


async def roll_magic_item(path: Sequence[str]) -> str:
    '''Roll for a magic item.

       This function operates recursively as it walks the tree of items.'''
    table = path_to_table(path)
    item = random.choices(table, weights=[x['weight'] for x in table])[0]

    if 'reroll' in item:
        return await roll_magic_item(item['reroll'].split(':'))

    if 'type' in item:
        if item['type'] == 'armor':
            item = await assemble_magic_armor(item)
            return await render(item)

        if item['type'] == 'weapon':
            item = await assemble_magic_weapon(item)
            return await render(item)

    if 'spell' in item:
        selected_spell = await get_spell(**item['spell'])
        ret = await render(item['name'], spell=selected_spell)
    else:
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

       This logs the successful connection and then checks if the spell
       database needs updated.'''
    logging.info(f'Successfully connected to Discord as {BOT.user.name}.')

    if not os.access(SPELL_PATH, os.F_OK):
        logging.info('Generating initial spell database.')
        await prep_spell_db(ITEMS['spell'])
        logging.info('Finished generating spell database.')
    elif os.path.getmtime('./data.yaml') > os.path.getmtime(SPELL_PATH):
        logging.info('Data file newer than spell database, updating spell database.')
        await prep_spell_db(ITEMS['spell'])
        logging.info('Finished updating spell database.')
    elif os.path.getmtime(os.path.abspath(__file__)) > os.path.getmtime(SPELL_PATH):
        logging.info('Script newer than spell database, updating spell database.')
        await prep_spell_db(ITEMS['spell'])
        logging.info('Finished updating spell database.')
    else:
        logging.info('Spell database already up to date.')


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
        category = random.choices(ITEMS['types'][rank2],
                                  weights=[x['weight'] for x in ITEMS['types'][rank2]])[0]['name']

    if category == 'wondrous':
        if subcategory is None:
            subcategory = random.choices(ITEMS['wondrous'],
                                         weights=[x['weight'] for x in ITEMS['wondrous']])[0]['category']

        category = subcategory

    if rank2 is None:
        rank2 = random.choice([x for x in list(ITEMS[category]) if x in ('minor', 'medium', 'major')])

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
async def spell(ctx, *, specifier: Optional[str]) -> None:
    '''Run when the `/roll35 spell` command is issued.

       This rolls for a random spell from our spell table using parameters
       specified by the command.

       The modifier string has three optional parameters:
       * `level:<level>` Used to specify a specific spell leve.
       * `class:<class>` Used to specify a particular class’s spell list should be used.
       * `tag:<tag>` Used to specify a tag that must match (for example, listing only conjuration spells.'''
    level = None
    cls = 'minimum'
    tag = None

    if specifier:
        for param in specifier.split():
            if param.startswith('level:'):
                try:
                    level = int(param.split(':')[1])
                except (ValueError, KeyError):
                    await ctx.send('invalid format for level parameter.')
                    return
            elif param.startswith('class:'):
                try:
                    cls = param.split(':')[1]
                except (ValueError, KeyError):
                    await ctx.send('invalid format for class parameter.')
                    return
            elif param.startswith('tag:'):
                try:
                    tag = param.split(':')[1]
                except (ValueError, KeyError):
                    await ctx.send('invalid format for tag parameter.')
                    return
            else:
                await ctx.send(f'Unrecognized parameter {param}.')
                return

    try:
        await ctx.send(await get_spell(level=level, cls=cls, tag=tag))
    except NoValidSpell:
        await ctx.send('Unable to find any spells matching requested parameters.')


@spell.error
async def spell_error(ctx, error: Exception) -> None:
    '''Run when the `spell` function throws an error.'''
    if isinstance(error, commands.UserInputError):
        await ctx.send('Invalid parameters for roll35 spell command, usage: ' +
                       '`/roll35 spell [level:<level>] [class:<class>] [tag:<tag>]`.')
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
# Data Prep #
#############

try:
    logging.info('Loading item data.')
    with open('./data.yaml', 'r') as source:
        DATA = yaml.safe_load(source.read())
except (IOError, OSError, yaml.YAMLError):
    logging.exception('Unable to load item data.')
    sys.exit(1)

logging.info('Initializing template values.')
for name, desc in DATA['keys'].items():
    if desc['type'] == 'flat':
        selector = create_flat_selector(desc['data'])
    elif desc['type'] == 'flat proportional':
        selector = create_flat_proportional_selector(desc['data'])
    elif desc['type'] == 'grouped':
        selector = create_grouped_selector(desc['data'])
    elif desc['type'] == 'grouped proportional':
        selector = create_grouped_proportional_selector(desc['data'])
    else:
        logging.error(f'Invalid type for key with name {name}.')

    setattr(KEYS, name, selector)

logging.info('Initializing item data.')
ITEMS['types'] = DATA['types']

for i in ('potion', 'scroll', 'wand'):
    logging.debug(f'Composing {i}')
    ITEMS[i] = compose_items(DATA[i])

for i in ('armor', 'weapon', 'ring',
          'rod', 'staff', 'belt', 'body',
          'chest', 'eyes', 'feet', 'hands',
          'head', 'headband', 'neck',
          'shoulders', 'wrists', 'slotless',
          'wondrous'):
    ITEMS[i] = DATA[i]

ITEMS['spell'] = DATA['spell']

logging.info('Successfully initialized primary data structures.')

##############
# Main Logic #
##############

BOT.run(TOKEN)
