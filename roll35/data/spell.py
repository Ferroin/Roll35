# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data agent for handling of spells.'''

from __future__ import annotations

import asyncio
import logging
import random

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import aiofiles

from . import agent
from .classes import ClassesAgent
from .. import types
from ..common import bad_return, chunk, flatten, yaml
from ..log import LogRun, log_call, log_call_async
from ..types.item import MAX_SPELL_LEVEL, ClassMap

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from . import DataSet


def process_spell_chunk(spells: Iterable[Mapping], classes: types.item.ClassMap, idx: int) -> tuple[Iterable[types.Spell], set[str]]:
    '''Process a chunk of the spell data.'''
    with LogRun(logger, logging.DEBUG, f'processing spell chunk {idx}'):
        ret = list(map(lambda x: types.Spell(**x), spells))
        tags = set()

        for spell in ret:
            spell.process_classes(classes)
            tags |= spell.tags

        return (
            ret,
            tags,
        )


@dataclass
class SpellData(agent.AgentData):
    '''Data handled by a SpellAgent.'''
    spells: Sequence[types.Spell]
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
        'occult',
        'spellpage',
        'spellpage_arcane',
        'spellpage_divine',
        'minimum',
    }

    def __init__(self: SpellAgent, dataset: DataSet, name: str, /) -> None:
        super().__init__(dataset, name)
        self._data: SpellData = SpellData(
            spells=list(),
            tags=set(),
        )

    def load_data(self: SpellAgent, /) -> types.Ret:
        '''Load the data for this agent.

           This requires a specific overide as it involves a large amount
           of custom logic and handles the parallelization in a different
           way from most other agents.

           This also requires the dataset to have a `classes` agent with
           data properly loaded.'''
        if not self.ready:
            logger.info('Fetching class data.')

            classes = cast(ClassesAgent, self._ds['classes']).classdata()

            if classes == types.Ret.NOT_READY:
                raise RuntimeError('Classes data is not ready.')

            logger.info('Reading spell data.')

            with open(self._ds.src / f'{self.name}.yaml') as f:
                data = yaml.load(f)

            if not isinstance(data, Sequence):
                raise ValueError('Spell data must be a sequence.')

            logger.info('Processing spell data.')

            results = []

            for idx, spell_chunk in enumerate(chunk(data, size=100)):
                results.append(process_spell_chunk(
                    spell_chunk,
                    classes,
                    idx,
                ))

            spells = list(flatten(map(lambda x: x[0], results)))
            tags = set.union(*map(lambda x: x[1], results))

            self._data = SpellData(
                spells=spells,
                tags=tags,
            )

            logger.info('Finished loading spell data.')

            self.ready = True

        return types.Ret.OK

    async def load_data_async(self: SpellAgent, pool: Executor, /) -> types.Ret:
        '''Load the data for this agent, using the specified executor pool.

           This requires a specific overide as it involves a large amount
           of custom logic and handles the parallelization in a different
           way from most other agents.

           This also requires the dataset to have a `classes` agent either
           queued to load data itself, or with data properly loaded.'''
        if not self.ready:
            logger.info('Fetching class data.')

            classes = await cast(ClassesAgent, self._ds['classes']).W_classdata_async()

            logger.info('Reading spell data.')

            async with aiofiles.open(self._ds.src / f'{self.name}.yaml') as f:
                raw_data = await f.read()

            data = yaml.load(raw_data)

            if not isinstance(data, Sequence):
                raise ValueError('Spell data must be a sequence.')

            logger.info('Processing spell data.')

            loop = asyncio.get_running_loop()
            coros = []

            for idx, spell_chunk in enumerate(chunk(data, size=100)):
                coros.append(loop.run_in_executor(
                    pool,
                    process_spell_chunk,
                    spell_chunk,
                    classes,
                    idx,
                ))

            results = await asyncio.gather(*coros)

            spells = list(flatten(map(lambda x: x[0], results)))
            tags = set.union(*map(lambda x: x[1], results))

            self._data = SpellData(
                spells=spells,
                tags=tags,
            )

            logger.info('Finished loading spell data.')

            self.ready = True

        return types.Ret.OK

    def __random(self: SpellAgent, classes: ClassMap, /, level: int | None = None, cls: str | None = None, tag: str | None = None) -> \
            types.Result[types.Spell]:
        valid_classes = set(classes.keys()) | {
            'minimum',
            'spellpage_arcane',
            'spellpage_divine',
        }

        if level is not None and level not in range(0, MAX_SPELL_LEVEL + 1):
            return (
                types.Ret.INVALID,
                'Level must be an integer between ' +
                f'0 and {MAX_SPELL_LEVEL}.'
            )

        if tag is not None and tag not in self._data.tags:
            return (
                types.Ret.INVALID,
                f'{tag} is not a recognized spell tag.',
            )

        if cls is None:
            cls = 'minimum'

        match (cls, level):
            case ('spellpage', _):
                cls = random.choice([  # nosec # not being used for crypto purposes
                    'spellpage_arcane',
                    'spellpage_divine',
                ])
            case ('arcane' | 'divine' | 'occult' as typ, None):
                valid = [k for (k, v) in classes.items()
                         if v.type == typ]
                cls = random.choice(valid)  # nosec # not being used for crypto purposes
            case ('arcane' | 'divine' | 'occult' as typ, int() as level):
                valid = [k for (k, v) in classes.items()
                         if v.level_in_cls(level)
                         and v.type == typ]
                cls = random.choice(valid)  # nosec # not being used for crypto purposes
            case ('random', None):
                cls = random.choice(list(classes.keys()))  # nosec # not being used for crypto purposes
            case ('random', int() as level):
                valid = [k for (k, v) in classes.items()
                         if v.level_in_cls(level)]
                logger.debug(f'Determining valid classes for level {level} spells: {valid}')
                cls = random.choice(valid)  # nosec # Not being used for crypto purposes
                logger.debug(f'Selected class {cls}')
            case ('minimum', _):
                pass
            case (cls, int() as level) if cls in valid_classes and not classes[cls].level_in_cls(level):
                return (
                    types.Ret.INVALID,
                    f'Class {cls} does not have access to ' +
                    f'level {level} spells.'
                )
            case (cls, _) if cls in valid_classes:
                pass
            case _:
                return (
                    types.Ret.INVALID,
                    'Invalid class name. ' +
                    'Must be one of: random, spellpage, ' +
                    f'{", ".join(valid_classes)}'
                )

        if cls is None:  # Mypy still thinks cls might be None at this point for some reason.
            raise RuntimeError

        possible: Sequence[types.Spell] = self._data.spells

        if tag is not None:
            # Filter by tag first because it’s cheap and will usually eliminate the largest number of spells.
            possible = [x for x in possible if tag in x.tags]

        possible = [x for x in possible if cls in x.classes]

        if level is not None:
            possible = [x for x in possible if x.classes[cls] == level]

        match list(possible):
            case []:
                return (
                    types.Ret.NO_MATCH,
                    'No spells found matching the requested parameters.'
                )
            case [*items]:
                spell = random.choice(items)  # nosec # not being used for crypto purposes

        match cls:
            case 'minimum':
                cls = spell.minimum
            case 'spellpage_arcane':
                cls = spell.spellpage_arcane
            case 'spellpage_divine':
                cls = spell.spellpage_divine

        if cls is None:  # It’s theoretically possible for cls to be None here, but should never happen in practice.
            raise RuntimeError

        if level is None:
            level = spell.classes[cls]

        spell.rolled_cls = cls
        spell.rolled_caster_level = classes[cls].levels[level]

        return (types.Ret.OK, spell)

    @log_call(logger, 'roll random spell')
    @types.check_ready(logger)
    def random(
            self: SpellAgent,
            /,
            level: int | None = None,
            cls: str | None = None,
            tag: str | None = None) -> \
            types.Result[types.Spell]:
        '''Get a random spell, optionally limited by level, class, or tag.'''
        match cast(ClassesAgent, self._ds['classes']).classdata():
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Failed to fetch class data.')
            case dict() as r1:
                classes = r1
            case r2:
                logger.warning(bad_return(r2))
                return (types.Ret.FAILED, 'Unknown internal error.')

        return self.__random(classes, level=level, cls=cls, tag=tag)

    @log_call_async(logger, 'roll random spell')
    @types.check_ready_async(logger)
    async def random_async(
            self: SpellAgent,
            /,
            level: int | None = None,
            cls: str | None = None,
            tag: str | None = None) -> \
            types.Result[types.Spell]:
        '''Get a random spell, optionally limited by level, class, or tag.'''
        match await cast(ClassesAgent, self._ds['classes']).classdata_async():
            case types.Ret.NOT_READY:
                return (types.Ret.NOT_READY, 'Failed to fetch class data.')
            case dict() as r1:
                classes = r1
            case r2:
                logger.warning(bad_return(r2))
                return (types.Ret.FAILED, 'Unknown internal error.')

        return self.__random(classes, level=level, cls=cls, tag=tag)

    @log_call(logger, 'get spell tags')
    @types.check_ready(logger)
    async def tags(self: SpellAgent, /) -> Sequence[str] | types.Ret:
        '''Return a list of recognized tags.'''
        if self._data.tags:
            return list(self._data.tags)
        else:
            return types.Ret.NO_MATCH

    @log_call_async(logger, 'get spell tags')
    @types.check_ready_async(logger)
    async def tags_async(self: SpellAgent, /) -> Sequence[str] | types.Ret:
        '''Return a list of recognized tags.'''
        if self._data.tags:
            return list(self._data.tags)
        else:
            return types.Ret.NO_MATCH
