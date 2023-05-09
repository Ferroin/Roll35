# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling of spells.'''

from __future__ import annotations

import asyncio
import logging
import random

from dataclasses import dataclass, field
from functools import reduce
from itertools import repeat
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

from . import agent
from . import constants
from .classes import ClassesAgent, ClassMap, ClassEntry
from .. import types
from ..common import check_ready, chunk, flatten, yaml
from ..log import log_call_async, LogRun

MAX_SPELL_LEVEL = 9

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Mapping, Iterable, Sequence
    from concurrent.futures import Executor

    from . import DataSet

Cls = str
Level = int


def _eval_minimum(level: Level | None, cls: Cls, minimum: Level | None, minimum_cls: Cls) -> tuple[Level | None, Cls]:
    '''Used to figure out the minimum level and class of a spell.

       This is intended to be used with functools.reduce().'''
    if level is not None:
        if level == minimum and not minimum_cls:
            return (level, cls)
        elif minimum is None or level < minimum:
            return (level, cls)

    return (minimum, minimum_cls)


def _eval_spellpage(level: Level | None, cls: Cls, spellpage: Level | None, spellpage_cls: Cls,
                    spellpage_fixed: bool, cls_match: Cls) -> tuple[Level | None, Cls, bool]:
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


@dataclass
class SpellFileEntry:
    '''Represents the data about a spell from the spell data file.'''
    classes: Mapping[Cls, Level]
    descriptor: str
    domains: Mapping[Cls, Level]
    name: str
    school: str
    subschool: str


def make_spell_file_entry(data: Mapping[str, Any]) -> SpellFileEntry:
    '''Convert a spell file entry to the correct data class.'''
    try:
        return SpellFileEntry(**data)
    except TypeError:
        raise RuntimeError(f'Invalid spell entry: { data }')


@dataclass
class SpellFields:
    '''Used to represent fields for a spell.'''
    spell: SpellFileEntry
    clsdata: ClassMap
    levels: dict[Cls, Level | None] = field(default_factory=dict)
    minimum: Level | None = MAX_SPELL_LEVEL
    minimum_cls: Cls = ''
    spellpage_arcane: Level | None = None
    spellpage_arcane_cls: Cls = ''
    spellpage_arcane_fixed: bool = False
    spellpage_divine: Level | None = None
    spellpage_divine_cls: Cls = ''
    spellpage_divine_fixed: bool = False


def _gen_spell_fields(acc: SpellFields, cls: Cls) -> SpellFields:
    '''Generate the SQL fields for a spell.'''
    spell = acc.spell
    clsdata = acc.clsdata

    match clsdata[cls]:
        case ClassEntry(copy=copy) if copy is not None:
            if copy in spell.classes:
                level: Level | None = spell.classes[copy]

                if cast(Level, level) >= len(clsdata[cls].levels):
                    level = None
            else:
                level = None
        case ClassEntry(merge=merge) if merge is not None:
            valid = list(set(merge) & set(spell.classes.keys()))

            match len(valid):
                case 0:
                    level = None
                case 1:
                    level = spell.classes[valid[0]]

                    if level >= len(clsdata[cls].levels):
                        level = None
                case _:
                    level = min(map(lambda x: spell.classes[x], valid))

                    if level >= len(clsdata[cls].levels):
                        level = None
        case _:
            if cls in spell.classes:
                level = spell.classes[cls]
            else:
                level = None

    if level is not None and level >= len(clsdata[cls].levels):
        logger.warning(f'{ spell.name } has invalid spell level for class { cls }, ignoring.')

    acc.minimum, acc.minimum_cls = _eval_minimum(
        level,
        cls,
        acc.minimum,
        acc.minimum_cls,
    )

    if clsdata[cls].type == 'arcane':
        spellpage_arcane, spellpage_arcane_cls, spellpage_arcane_fixed = _eval_spellpage(
            level,
            cls,
            acc.spellpage_arcane,
            acc.spellpage_arcane_cls,
            acc.spellpage_arcane_fixed,
            'wizard',
        )

        acc.spellpage_arcane = spellpage_arcane
        acc.spellpage_arcane_cls = spellpage_arcane_cls
        acc.spellpage_arcane_fixed = spellpage_arcane_fixed
    elif clsdata[cls].type == 'divine':
        spellpage_divine, spellpage_divine_cls, spellpage_divine_fixed = _eval_spellpage(
            level,
            cls,
            acc.spellpage_divine,
            acc.spellpage_divine_cls,
            acc.spellpage_divine_fixed,
            'cleric',
        )

        acc.spellpage_divine = spellpage_divine
        acc.spellpage_divine_cls = spellpage_divine_cls
        acc.spellpage_divine_fixed = spellpage_divine_fixed

    acc.levels = acc.levels | {cls: level}

    return acc


def process_spell(data: tuple[SpellFileEntry, ClassMap]) -> tuple[dict[str, Any], set[str]]:
    '''Process a spell entry.

       Returns a tuple of the column values for the spell to be added
       to the main spell table and a set of tags.'''
    spell, classes = data[0], data[1]

    fields = reduce(_gen_spell_fields, classes.keys(), SpellFields(
        spell=spell,
        clsdata=classes,
    ))

    ret: dict[str, Any] = fields.levels
    ret['name'] = spell.name

    for f in ['minimum', 'spellpage_arcane', 'spellpage_divine',
              'minimum_cls', 'spellpage_arcane_cls', 'spellpage_divine_cls']:
        ret[f] = getattr(fields, f)

    tags = {
        spell.school,
        spell.subschool,
    }

    tags = tags | set(spell.descriptor.split(', '))

    return (ret, tags)


def process_spell_chunk(items: Iterable[tuple[SpellFileEntry, ClassMap]], idx: int) -> Iterable[tuple[dict[str, Any], set[str]]]:
    '''Map a list of spell items into a list of SQL fields.'''
    ret = []

    with LogRun(logger, logging.DEBUG, f'processing spell chunk { idx }'):
        for spell in items:
            ret.append(process_spell(spell))

    return ret


@dataclass
class SpellData(agent.AgentData):
    '''Data handled by a SpellAgent.'''
    tags: set[str]


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

    def __init__(self: SpellAgent, dataset: DataSet, name: str, db_path: Path = (Path.cwd() / 'spells.db')) -> None:
        super().__init__(dataset, name)
        self._db_path = db_path
        self._data: SpellData = SpellData(
            tags=set()
        )

    async def _level_in_cls(self: SpellAgent, level: Level, cls: Cls) -> bool:
        classes = await cast(ClassesAgent, self._ds['classes']).get_class(cls)
        levels = classes.levels

        if level is None:
            return True

        return len(levels) > level and levels[level]

    @staticmethod
    def _process_data(_):
        return None

    async def load_data(self: SpellAgent, pool: Executor) -> types.Ret:
        '''Load the data for this agent, using the specified executor pool.

           This requires a specific overide as it involves a large amount
           of custom logic and handles the aprallelization in a different
           way from most other agents.

           This also requires the dataset to have a `classes` agent either
           queued to load data itself, or with data properly loaded.'''
        if not self._ready.is_set():
            logger.info('Fetching class data.')

            classes = await cast(ClassesAgent, self._ds['classes']).W_classdata()

            logger.info('Reading spell data.')

            with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            spell_list = zip(map(make_spell_file_entry, data), repeat(classes, len(data)))

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

                logger.info('Processing spells to add to DB.')

                coros = []

                for idx, spell_chunk in enumerate(chunk(spell_list, 100)):
                    coros.append(loop.run_in_executor(
                        pool,
                        process_spell_chunk,
                        spell_chunk,
                        idx,
                    ))

                # TODO: Improve parallelism and memory usage.

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

                self._data.tags = reduce(set.union, map(lambda x: x[1], spells))

                logger.info('Optimizing DB.')

                await db.executescript('''
                    PRAGMA optimize;
                ''')

                logger.info('Finished initializing spell DB.')

            self._ready.set()

        return types.Ret.OK

    @log_call_async(logger, 'roll random spell')
    @check_ready
    async def random(
            self: SpellAgent,
            level: Level | None = None,
            cls: Cls | None = None,
            tag: str | None = None) -> \
            types.Result[types.item.SpellEntry]:
        '''Get a random spell, optionally limited by level, class, or tag.'''
        match await cast(ClassesAgent, self._ds['classes']).classdata():
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Failed to fetch class data.')
            case ret:
                classes = ret

        valid_classes = set(classes.keys()) | {
            'minimum',
            'spellpage_arcane',
            'spellpage_divine',
        }

        if level is not None and level not in range(0, MAX_SPELL_LEVEL + 1):
            return (
                types.Ret.INVALID,
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
                         if await self._level_in_cls(cast(int, level), k)
                         and v.type == 'arcane']
                cls = random.choice(valid)
            case ('divine', None):
                valid = [k for (k, v) in classes.items()
                         if v.type == 'divine']
                cls = random.choice(valid)
            case ('divine', level):
                valid = [k for (k, v) in classes.items()
                         if await self._level_in_cls(cast(int, level), k)
                         and v.type == 'divine']
                cls = random.choice(valid)
            case ('random', None):
                cls = random.choice(classes.keys())
            case ('random', level):
                valid = [k for (k, v) in classes.items()
                         if await self._level_in_cls(cast(int, level), k)]
                cls = random.choice(valid)
            case (None, _):
                cls = 'minimum'
            case (cls, level) if cls in valid_classes and \
                    not await self._level_in_cls(cast(int, level), cls):
                return (
                    types.Ret.INVALID,
                    f'Class { cls } does not have access to ' +
                    f'level { level } spells.'
                )
            case (cls, _) if cls in valid_classes:
                pass
            case _:
                return (
                    types.Ret.INVALID,
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
                types.Ret.NO_MATCH,
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

        return (
            types.Ret.OK,
            types.item.SpellEntry(
                name=spell['name'],
                level=spell[cls],
                cls=cast(str, cls),
                caster_level=classes[cls].levels[level],
            )
        )

    @log_call_async(logger, 'get spell tags')
    @check_ready
    async def tags(self: SpellAgent) -> Sequence[str] | types.Ret:
        '''Return a list of recognized tags.'''
        if self._data.tags:
            return list(self._data.tags)
        else:
            return types.Ret.NO_MATCH
