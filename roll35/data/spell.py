# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling of spells.'''

import asyncio
import logging
import random

from functools import reduce
from itertools import repeat
from pathlib import Path

import aiosqlite

from . import agent
from . import constants
from ..common import check_ready, chunk, flatten, yaml
from ..retcode import Ret

MAX_SPELL_LEVEL = 9

logger = logging.getLogger(__name__)


def _eval_minimum(level, cls, minimum, minimum_cls):
    '''Used to figure out the minimum level and class of a spell.

       This is intended to be used with functools.reduce().'''
    if level is not None:
        if level == minimum and not minimum_cls:
            return (level, cls)
        elif minimum is None or level < minimum:
            return (level, cls)

    return (minimum, minimum_cls)


def _eval_spellpage(level, cls, spellpage, spellpage_cls,
                    spellpage_fixed, cls_match):
    '''Used to figure out the spellpage class and level for a spell.

       This is intended to be used with functools.reduce().'''
    if spellpage_fixed:
        return (spellpage, spellpage_cls, True)
    elif level is not None:
        if cls_match == cls:
            return (level, cls, True)
        elif spellpage is None:
            return (level, cls, False)
        elif spellpage < level:
            return (level, cls, False)

    return (spellpage, spellpage_cls, spellpage_fixed)


def _gen_spell_fields(acc, cls):
    '''Generate the SQL fields for a spell.'''
    spell = acc['spell']
    clsdata = acc['clsdata']

    match clsdata[cls]:
        case {'copy': copy}:
            if copy in spell['classes']:
                level = spell['classes'][copy]

                if level >= len(clsdata[cls]['levels']):
                    level = None
            else:
                level = None
        case {'merge': [*classes]}:
            valid = list(set(classes) & set(spell['classes'].keys()))

            match len(valid):
                case 0:
                    level = None
                case 1:
                    level = spell['classes'][valid[0]]

                    if level >= len(clsdata[cls]['levels']):
                        level = None
                case _:
                    level = min(map(lambda x: spell['classes'][x], valid))

                    if level >= len(clsdata[cls]['levels']):
                        level = None
        case _:
            if cls in spell['classes']:
                level = spell['classes'][cls]
            else:
                level = None

    if level is not None and level >= len(clsdata[cls]['levels']):
        logger.warning(f'{ spell.name } has invalid spell level for class { cls }, ignoring.')

    acc['minimum'], acc['minimum_cls'] = _eval_minimum(
        level,
        cls,
        acc['minimum'],
        acc['minimum_cls'],
    )

    if clsdata[cls]['type'] == 'arcane':
        spellpage_arcane, spellpage_arcane_cls, spellpage_arcane_fixed = _eval_spellpage(
            level,
            cls,
            acc['spellpage_arcane'],
            acc['spellpage_arcane_cls'],
            acc['spellpage_arcane_fixed'],
            cls == 'wizard',
        )

        acc['spellpage_arcane'] = spellpage_arcane
        acc['spellpage_arcane_cls'] = spellpage_arcane_cls
        acc['spellpage_arcane_fixed'] = spellpage_arcane_fixed
    elif clsdata[cls]['type'] == 'divine':
        spellpage_divine, spellpage_divine_cls, spellpage_divine_fixed = _eval_spellpage(
            level,
            cls,
            acc['spellpage_divine'],
            acc['spellpage_divine_cls'],
            acc['spellpage_divine_fixed'],
            cls == 'cleric',
        )

        acc['spellpage_divine'] = spellpage_divine
        acc['spellpage_divine_cls'] = spellpage_divine_cls
        acc['spellpage_divine_fixed'] = spellpage_divine_fixed

    return acc | {
        'levels': acc['levels'] | {cls: level},
    }


def process_spell(data):
    '''Process a spell entry.

       Returns a tuple of the column values for the spell to be added
       to the main spell table and a set of tags.'''
    spell, classes = data[0], data[1]

    fields = reduce(_gen_spell_fields, classes.keys(), {
        'spell': spell,
        'clsdata': classes,
        'levels': dict(),
        'minimum': MAX_SPELL_LEVEL,
        'minimum_cls': '',
        'spellpage_arcane': None,
        'spellpage_arcane_cls': None,
        'spellpage_arcane_fixed': False,
        'spellpage_divine': None,
        'spellpage_divine_cls': None,
        'spellpage_divine_fixed': False,
    })

    ret = fields['levels']
    ret['name'] = spell['name']

    for f in ['minimum', 'spellpage_arcane', 'spellpage_divine',
              'minimum_cls', 'spellpage_arcane_cls', 'spellpage_divine_cls']:
        ret[f] = fields[f]

    tags = {
        spell['school'],
        spell['subschool'],
    }

    tags = tags | set(spell['descriptor'].split(', '))

    return (ret, tags)


def process_spell_chunk(items):
    '''Map a list of spell items into a list of SQL fields.'''
    return map(process_spell, items)


class SpellAgent(agent.Agent):
    '''Data agent for handling spell data.

       This internally uses a SQLite3 database for performance and memory
       efficiency reasons. This lets us push a lot of the actual filtering
       and selection logic into C code, allowing it to run much faster
       than it would in Python while using much less memory.'''
    EXTRA_CLASS_NAMES = {
        'random',
        'arcane',
        'divine',
        'spellpage',
        'spellpage_arcane',
        'spellpage_divine',
        'minimum',
    }

    def __init__(self, dataset, name='spell', db_path=(Path.cwd() / 'spells.db')):
        self._db_path = db_path
        super().__init__(dataset, name)

    async def _level_in_cls(self, level, cls):
        levels = await self._ds['classes'].get_class(cls)
        levels = levels['levels']

        if level is None:
            return True

        return len(levels) > level and levels[level]

    @staticmethod
    def _process_data(_):
        return None

    async def load_data(self, pool):
        '''Load the data for this agent, using the specified executor pool.

           This requires a specific overide as it involves a large amount
           of custom logic and handles the aprallelization in a different
           way from most other agents.

           This also requires the dataset to have a `classes` agent either
           queued to load data itself, or with data properly loaded.'''
        if not self._ready.is_set():
            logger.info('Fetching class data.')

            classes = await self._ds['classes'].W_classdata()

            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row

                logger.info(f'Initializing spell DB at { self._db_path }')

                loop = asyncio.get_running_loop()

                await db.executescript(f'''
                    DROP TABLE IF EXISTS spells;
                    DROP TABLE IF EXISTS tagmap;
                    CREATE TABLE spells(name TEXT,
                                        { " INTEGER, ".join(classes) } INTEGER,
                                        minimum INTEGER,
                                        spellpage_arcane INTEGER,
                                        spellpage_divine INTEGER,
                                        minimum_cls TEXT,
                                        spellpage_arcane_cls TEXT,
                                        spellpage_divine_cls TEXT);
                    CREATE VIRTUAL TABLE tagmap USING fts4(name, tags);
                    PRAGMA journal_mode='WAL';
                    PRAGMA synchronous='NORMAL';
                    VACUUM;
                ''')

                logger.info('Reading spell data.')

                with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                    spells = yaml.load(f)

                logger.info('Processing spells to add to DB.')

                spells = zip(spells, repeat(classes, len(spells)))

                coros = []

                for spell_chunk in chunk(spells, 100):
                    coros.append(loop.run_in_executor(
                        pool,
                        process_spell_chunk,
                        spell_chunk
                    ))

                spells = list(flatten(await asyncio.gather(*coros)))

                spell_params = map(lambda x: x[0], spells)
                tag_params = map(
                    lambda x: {
                        'name': x[0]['name'],
                        'tags': ' '.join(filter(lambda x: x, list(x[1])))
                    },
                    spells
                )

                logger.info('Adding spells to spell table.')

                cls_params = ', '.join(map(lambda x: f':{ x }', classes))

                await db.executemany(f'''
                    INSERT INTO spells VALUES (
                        :name,
                        { cls_params },
                        :minimum,
                        :spellpage_arcane,
                        :spellpage_divine,
                        :minimum_cls,
                        :spellpage_arcane_cls,
                        :spellpage_divine_cls
                    );
                ''', spell_params)

                logger.info('Adding spells to tag map table.')

                await db.executemany('''
                    INSERT INTO tagmap VALUES (
                        :name,
                        :tags
                    );
                ''', tag_params)

                logger.info('Storing tag list.')

                self._data['tags'] = ' '.join(filter(lambda x: x, set.union(*map(lambda x: x[1], spells))))

                logger.info('Optimizing DB.')

                await db.executescript('''
                    PRAGMA optimize;
                ''')

                logger.info('Finished initializing spell DB.')

            self._ready.set()

        return True

    @check_ready
    async def get_spell(self, name):
        '''Look up a spell by name.'''
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row

            spellrow = await db.execute_fetchall('''
                SELECT *
                FROM spells
                WHERE name = ':name';
            ''', {'name': name})

            if not spellrow:
                return Ret.NO_MATCH
            else:
                spellrow = spellrow[0]

            tagsrow = await db.execute_fetchall('''
                SELECT *
                FROM tagmap
                WHERE name = ':name';
            ''', {'name': name})

        if not tagsrow:
            tagsrow = {'data': ''}
        else:
            tagsrow = tagsrow[0]

        tags = tagsrow['data'].split(' ')
        spell = {
            'tags': tags
        }

        for k in spellrow.keys():
            spell[k] = spellrow[k]

        return spell

    @check_ready
    async def random(self, level=None, cls=None, tag=None):
        '''Get a random spell, optionally limited by level, class, or tag.'''
        match await self._ds['classes'].classdata():
            case Ret.NOT_READY:
                return (Ret.NOT_READY, 'Failed to fetch class data.')
            case ret:
                classes = ret

        valid_classes = set(classes.keys()) | {
            'minimum',
            'spellpage_arcane',
            'spellpage_divine',
        }

        if level is not None and level not in range(0, MAX_SPELL_LEVEL + 1):
            return (
                Ret.INVALID,
                'Level must be an integer between ' +
                f'0 and { MAX_SPELL_LEVEL }.'
            )

        match (cls, level):
            case ('spellpage', _):
                cls = random.choice([
                    'spellpage_arcane',
                    'spellpage_divine',
                ])
            case ('arcane', None):
                valid = [k for (k, v) in classes.enumerate()
                         if v.type == 'arcane']
                cls = random.choice(valid)
            case ('arcane', level):
                valid = [k for (k, v) in classes.enumerate()
                         if await self._level_in_cls(level, k)
                         and v.type == 'arcane']
                cls = random.choice(valid)
            case ('divine', None):
                valid = [k for (k, v) in classes.items()
                         if v.type == 'divine']
                cls = random.choice(valid)
            case ('divine', level):
                valid = [k for (k, v) in classes.items()
                         if await self._level_in_cls(level, k)
                         and v.type == 'divine']
                cls = random.choice(valid)
            case ('random', None):
                cls = random.choice(classes.keys())
            case ('random', level):
                valid = [k for (k, v) in classes.items()
                         if await self._level_in_cls(level, k)]
                cls = random.choice(valid)
            case (None, _):
                cls = 'minimum'
            case (cls, level) if cls in valid_classes and \
                    not await self._level_in_cls(level, cls):
                return (
                    Ret.INVALID,
                    f'Class { cls } does not have access to ' +
                    f'level { level } spells.'
                )
            case (cls, _) if cls in valid_classes:
                pass
            case _:
                return (
                    Ret.INVALID,
                    'Invalid class name. ' +
                    'Must be one of: random, spellpage, ' +
                    f'{ ", ".join(valid_classes) }'
                )

        params = {
            'class': cls,
            'level': level,
            'tag': tag,
        }

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row

            match (cls, level, tag):
                case (_, None, None):
                    spell = await db.execute_fetchall(f'''
                        SELECT *
                        FROM spells
                        WHERE { cls } IS NOT NULL
                        ORDER BY random()
                        LIMIT 1;
                    ''', params)
                case (_, _, None):
                    spell = await db.execute_fetchall(f'''
                        SELECT *
                        FROM spells
                        WHERE { cls } = :level
                        ORDER BY random()
                        LIMIT 1;
                    ''', params)
                case (_, None, _):
                    spell = await db.execute_fetchall(f'''
                        SELECT *
                        FROM spells
                        WHERE { cls } IS NOT NULL
                        AND name IN (
                            SELECT name
                            FROM tagmap
                            WHERE tags MATCH :tag
                        )
                        ORDER BY random()
                        LIMIT 1;
                    ''', params)
                case (_, _, _):
                    spell = await db.execute_fetchall(f'''
                        SELECT *
                        FROM spells
                        WHERE { cls } = :level
                        AND name IN (
                            SELECT name
                            FROM tagmap
                            WHERE tags MATCH :tag
                        )
                        ORDER BY random()
                        LIMIT 1;
                    ''', params)

        if not spell:
            return (
                Ret.NO_MATCH,
                'No spells found matching the requested parameters.'
            )
        else:
            spell = spell[0]

        match cls:
            case 'minimum':
                cls = spell['minimum_cls']
            case 'spellpage_arcane':
                cls = spell['spellpage_arcane_cls']
            case 'spellpage_divine':
                cls = spell['spellpage_divine_cls']

        if level is None:
            level = spell[cls]

        spell = {
            'name': spell['name'],
            'level': spell[cls],
            'cls': cls,
            'caster_level': classes[cls]['levels'][level],
        }

        return (Ret.OK, spell)
