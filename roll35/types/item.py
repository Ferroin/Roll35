# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Classes defining item formats.'''

from __future__ import annotations

from collections.abc import Sequence, Mapping, MutableMapping
from dataclasses import dataclass, KW_ONLY
from typing import Union, Literal, TypedDict, TypeVar, Type, Any, cast

from pydantic import BaseModel, Field, validator

from .ranks import RankWeights

EnchantBonus = int
Cost = int | float
_Cost = Cost | Literal['varies']
CostRange = tuple[Cost, Cost]
Tag = str

MAX_SPELL_LEVEL = 9


def check_weight(w: int) -> int:
    '''Ensure that a weight is within bounds.'''
    if w < 1:
        raise ValueError('Weight must be at least 1.')

    return w


class WeightedValue(BaseModel):
    '''Basic class for weighted value selection.'''
    weight: int
    value: str

    _check_weight = validator('weight', allow_reuse=True)(check_weight)


@dataclass
class ClassEntry:
    '''A spellcasting class entry.'''
    _: KW_ONLY
    name: str
    type: Literal['arcane' | 'divine']
    levels: list[int | None]
    copy: str | None = None
    merge: Sequence[str] | None = None


ClassMap = Mapping[str, ClassEntry]


@dataclass
class BaseItem:
    '''Base class for item entries.'''
    _: KW_ONLY
    weight: int = 1
    reroll: Sequence[str] | None = None
    cost: _Cost | None = None
    costrange: CostRange | None = None
    costmult: Cost | None = None


class SpellParams(TypedDict, total=False):
    '''Parameters for rolling a spell for an item.'''
    level: int
    cls: str


class Spell(BaseModel):
    '''Data model representing a spell.'''
    name: str
    classes: MutableMapping[str, int]
    domains: Mapping[str, int] = Field(default_factory=dict)
    descriptor: str
    school: str
    subschool: str
    tags: set[str] = Field(default_factory=set)
    minimum: str | None = None
    spellpage_arcane: str | None = None
    spellpage_divine: str | None = None
    rolled_cls: str | None = None
    rolled_caster_level: int | None = None

    @validator('tags', always=True)
    @staticmethod
    def populate_tags(cls: Type[Spell], v: set[str], values: dict[str, Any]) -> set[str]:
        if not v:
            t = {x for x in cast(str, values['descriptor']).split(', ') if x}

            if values['school']:
                t.add(cast(str, values['school']))

            if values['subschool']:
                t.add(cast(str, values['subschool']))
        else:
            t = v

        return t

    @validator('classes')
    @staticmethod
    def check_classes(cls: Type[Spell], v: MutableMapping[str, int], values: dict[str, Any]) -> MutableMapping[str, int]:
        for c, l in v.items():
            if l < 0:
                raise ValueError(f'Spell level for class { c } in { values["name"] } must be at least 0.')

            if l > MAX_SPELL_LEVEL:
                raise ValueError(f'Spell level for class { c } in { values["name"] } must be less than or equal to { MAX_SPELL_LEVEL }.')

        return v

    @validator('domains')
    @staticmethod
    def check_domains(cls: Type[Spell], v: MutableMapping[str, int], values: dict[str, Any]) -> MutableMapping[str, int]:
        for c, l in v.items():
            if l < 0:
                raise ValueError(f'Spell level for domain { c } in { values["name"] } must be at least 0.')

            if l > MAX_SPELL_LEVEL:
                raise ValueError(f'Spell level for domain { c } in { values["name"] } must be less than or equal to { MAX_SPELL_LEVEL }.')

        return v

    @validator('school')
    @staticmethod
    def check_school(cls: Type[Spell], v: str, values: dict[str, Any]) -> str:
        if not v:
            raise ValueError(f'Missing school for { values["name"] }.')

        return v

    def set_derived_classes(self: Spell, classes: ClassMap) -> None:
        '''Determine derived classes for this spell based on classes.'''
        self.minimum = min(self.classes, key=lambda x: self.classes[x])
        self.classes['minimum'] = self.classes[self.minimum]

        if 'wizard' in self.classes:
            self.spellpage_arcane = 'wizard'
        else:
            possible = [x for x in classes if x in self.classes and classes[x].type == 'arcane']

            if possible:
                self.spellpage_arcane = min(possible, key=lambda x: self.classes[x])

        if self.spellpage_arcane is not None:
            self.classes['spellpage_arcane'] = self.classes[self.spellpage_arcane]

        if 'cleric' in self.classes:
            self.spellpage_divine = 'cleric'
        else:
            possible = [x for x in classes if x in self.classes and classes[x].type == 'divine']

            if possible:
                self.spellpage_divine = min(possible, key=lambda x: self.classes[x])

        if self.spellpage_divine is not None:
            self.classes['spellpage_divine'] = self.classes[self.spellpage_divine]


@dataclass
class SpellItem(BaseItem):
    '''Base class for an item with an embedded spell.'''
    _: KW_ONLY
    spell: SpellParams
    rolled_spell: Spell | None = None
    cls: str | None = None
    level: int | None = None
    caster_level: int | None = None


@dataclass
class SimpleItem(BaseItem):
    '''A basic item entry.'''
    _: KW_ONLY
    name: str = ''


@dataclass
class SimpleSpellItem(SimpleItem, SpellItem):
    '''A basic item entry with an embedded spell.'''
    pass


@dataclass
class OrdnancePattern(BaseItem):
    '''A pattern entry for constructing an ordnance item.'''
    bonus: EnchantBonus | None = None
    enchants: list[EnchantBonus] | None = None
    specific: list[str] | None = None


OrdnanceSpecific = SimpleItem


@dataclass
class OrdnanceBaseItem(BaseItem):
    '''A base ordnance item entry.'''
    type: str
    tags: set[Tag]
    name: str
    count: int | None = None


EnchantLimits = TypedDict('EnchantLimits', {'only': Union[list[Tag]], 'not': Union[list[Tag]]}, total=False)


@dataclass
class OrdnanceEnchant(BaseItem):
    '''An enchantment entry for ordnance items.'''
    name: str
    bonuscost: Cost | None = None
    bonus: EnchantBonus | None = None
    exclude: list[str] | None = None
    remove: list[str] | None = None
    add: list[str] | None = None
    limit: EnchantLimits | None = None


OrdnanceItem = Union[OrdnancePattern, OrdnanceSpecific, OrdnanceBaseItem, OrdnanceEnchant]


@dataclass
class CompoundItem(SimpleItem, RankWeights):
    '''An entry for an item in a compound item list.'''
    pass


@dataclass
class CompoundSpellItem(CompoundItem, SpellItem):
    '''An entry for a compound item with an embedded spell.'''
    pass


Item = TypeVar(
    'Item',
    BaseItem,
    SimpleItem,
    SimpleSpellItem,
    CompoundItem,
    CompoundSpellItem,
    OrdnancePattern,
    OrdnanceSpecific,
    OrdnanceBaseItem,
    OrdnanceEnchant,
)
