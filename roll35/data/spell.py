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
from ..common import chunk, flatten, DATA_ROOT, yaml

MAX_SPELL_LEVEL = 9
MAX_CONCURRENT_DB_REQS = 8
DB_CONN_LINGER = 60

logger = logging.getLogger(__name__)


def _eval_minimum(level, cls, minimum, minimum_cls):
    if level is not None:
        if level == minimum and not minimum_cls:
            return (level, cls)
        elif minimum is None or level < minimum:
            return (level, cls)

    return (minimum, minimum_cls)


def _eval_spellpage(level, cls, spellpage, spellpage_cls,
                    spellpage_fixed, cls_match):
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
    return map(process_spell, items)


class SpellAgent(agent.Agent):
    def __init__(self, pool, db_path, logger=logger):
        self.name = 'spells'
        self._cls_path = DATA_ROOT / 'classes.yaml'
        self._spell_path = DATA_ROOT / 'spells.yaml'
        self._db_path = db_path
        super().__init__(pool, logger)

    def _level_in_cls(self, level, cls):
        levels = self._data['classes'][cls]['levels']

        if level is None:
            return True

        return len(levels) > level and levels[level]

    async def load_data(self):
        self.logger.info('Loading class data.')
        with open(self._cls_path) as f:
            self._data['classes'] = yaml.load(f)

        self.logger.info('Finished loading class data.')

        self.logger.info('Checking timestamps for spell DB.')
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row

            table = await db.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='info' COLLATE NOCASE"
            )

            if table:
                class_mtime = await db.execute_fetchall(
                    "SELECT data FROM info WHERE id='class_mtime';"
                )

                if class_mtime:
                    class_mtime = int(class_mtime[0]['data'].split('.')[0])
                else:
                    class_mtime = 0

                spell_mtime = await db.execute_fetchall(
                    "SELECT data FROM info WHERE id='spell_mtime';"
                )

                if spell_mtime:
                    spell_mtime = int(spell_mtime[0]['data'].split('.')[0])
                else:
                    spell_mtime = 0

                mod_mtime = await db.execute_fetchall(
                    "SELECT data FROM info WHERE id='mod_mtime';"
                )

                if mod_mtime:
                    mod_mtime = int(mod_mtime[0]['data'].split('.')[0])
                else:
                    mod_mtime = 0
            else:
                class_mtime = 0
                spell_mtime = 0
                mod_mtime = 0

            if any([
                class_mtime < self._cls_path.stat().st_mtime,
                spell_mtime < self._spell_path.stat().st_mtime,
                mod_mtime < Path(__file__).stat().st_mtime,
            ]):
                await self._prepare_spell_db(db, {
                    'spell_mtime': self._spell_path.stat().st_mtime,
                    'class_mtime': self._cls_path.stat().st_mtime,
                    'mod_mtime': Path(__file__).stat().st_mtime,
                })

            self.logger.info('Caching tag list.')
            tags = await db.execute_fetchall(
                "SELECT data FROM info WHERE id='tags';"
            )

            self._data['tags'] = tags[0]['data'].split(' ')

        self._ready = True

        return True

    async def _prepare_spell_db(self, db, times):
        self.logger.info(f'Initializing spell DB at { self._db_path }')

        loop = asyncio.get_running_loop()

        classes = self._data['classes'].keys()

        await db.executescript(f'''
            DROP TABLE IF EXISTS spells;
            DROP TABLE IF EXISTS tagmap;
            DROP TABLE IF EXISTS info;
            CREATE TABLE spells(name TEXT,
                                { " INTEGER, ".join(classes) } INTEGER,
                                minimum INTEGER,
                                spellpage_arcane INTEGER,
                                spellpage_divine INTEGER,
                                minimum_cls TEXT,
                                spellpage_arcane_cls TEXT,
                                spellpage_divine_cls TEXT);
            CREATE VIRTUAL TABLE tagmap USING fts4(name, tags);
            CREATE TABLE info(id TEXT, data TEXT);
            PRAGMA journal_mode='WAL';
            PRAGMA synchronous='NORMAL';
            VACUUM;
        ''')

        with open(self._spell_path) as f:
            spells = yaml.load(f)

        spells = zip(spells, repeat(self._data['classes'], len(spells)))

        self.logger.info('Processing spells to add to DB.')

        coros = []

        for spell_chunk in chunk(spells, 100):
            coros.append(loop.run_in_executor(
                self._pool,
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

        self.logger.info('Adding spells to spell table.')

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

        self.logger.info('Adding spells to tag map table.')

        await db.executemany('''
            INSERT INTO tagmap VALUES (
                :name,
                :tags
            );
        ''', tag_params)

        self.logger.info('Storing tag list.')

        tags = ' '.join(filter(lambda x: x, set.union(*map(lambda x: x[1], spells))))

        await db.execute('''
            INSERT INTO info VALUES (
                "tags",
                ?
            );
        ''', [tags])

        self.logger.info('Storing source data timestamps.')

        await db.executescript(f'''
            INSERT INTO info VALUES ('spell_mtime', '{ times["spell_mtime"] }');
            INSERT INTO info VALUES ('class_mtime', '{ times["class_mtime"] }');
            INSERT INTO info VALUES ('mod_mtime', '{ times["mod_mtime"] }');
            PRAGMA optimize;
        ''')

        self.logger.info('Finished initializing spell DB.')

        return True

    async def classes(self):
        if self._ready:
            return list(self._data['classes'].keys())
        else:
            return False

    async def get_class(self, cls):
        if self._ready:
            return self._data['classes'][cls]
        else:
            return False

    async def get_spell(self, name):
        if self._ready:
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row

                spellrow = await db.execute_fetchall('''
                    SELECT *
                    FROM spells
                    WHERE name = ':name';
                ''', {'name': name})

                if not spellrow:
                    return None
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
        else:
            return False

    async def random(self, level=None, cls=None, tag=None):
        if not self._ready:
            return False

        valid_classes = set(self._data['classes'].keys()) | {
            'minimum',
            'spellpage_arcane',
            'spellpage_divine',
        }

        if level is not None and level not in range(0, MAX_SPELL_LEVEL + 1):
            return (
                False,
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
                valid = [k for (k, v) in self._data['classes'].enumerate()
                         if v.type == 'arcane']
                cls = random.choice(valid)
            case ('arcane', level):
                valid = [k for (k, v) in self._data['classes'].enumerate()
                         if self._level_in_cls(level, k)
                         and v.type == 'arcane']
                cls = random.chioce(valid)
            case ('divine', None):
                valid = [k for (k, v) in self._data['classes'].enumerate()
                         if v.type == 'divine']
                cls = random.choice(valid)
            case ('divine', level):
                valid = [k for (k, v) in self._data['classes'].enumerate()
                         if self._level_in_cls(level, k)
                         and v.type == 'divine']
                cls = random.chioce(valid)
            case ('random', None):
                cls = random.choice(self._data['classes'].keys())
            case ('random', level):
                valid = [k for (k, v) in self._data['classes'].enumerate()
                         if self._level_in_cls(level, k)]
                cls = random.chioce(valid)
            case (None, _):
                cls = 'minimum'
            case (cls, level) if cls in valid_classes and \
                    not self._level_in_cls(level, cls):
                return (
                    False,
                    f'Class { cls } does not have access to ' +
                    f'level { level } spells.'
                )
            case (cls, _) if cls in valid_classes:
                pass
            case _:
                return (
                    False,
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
                False,
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

        caster_level = self._data['classes'][cls]['levels'][level]

        return (
            True,
            f'{ spell["name"] } (' +
            f'{ cls.capitalize() } CL ' +
            f'{ caster_level })'
        )
