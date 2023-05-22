# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Classes defining item formats.'''

from __future__ import annotations

from collections.abc import Sequence, Mapping, MutableMapping
from typing import Literal, TypeVar, Type, Any, cast

from pydantic import BaseModel, Field, validator, root_validator

from .ranks import RankWeights

EnchantBonus = int
Cost = float
_Cost = Cost | Literal['varies']
CostRange = tuple[Cost, Cost]
Tag = str

MAX_SPELL_LEVEL = 9


def check_weight(w: int) -> int:
    '''Ensure that a weight is within bounds.'''
    if w < 1:
        raise ValueError('Weight must be at least 1.')

    return w


def check_spell_level(lvl: int | None) -> int | None:
    '''Check a spell level.'''
    if lvl is not None:
        if lvl < 0:
            raise ValueError('Spell level must be at least 0.')

        if lvl > MAX_SPELL_LEVEL:
            raise ValueError('Spell level must not be higher than { MAX_SPELL_LEVEL }.')

    return lvl


def check_enchant_bonus(b: int | None) -> int | None:
    '''Ensure that an enchantment bonus is within bounds.'''
    if b is not None:
        if b < 1:
            raise ValueError('Enchantment bonus must be at least 1.')

    return b


class WeightedValue(BaseModel):
    '''Basic class for weighted value selection.'''
    weight: int
    value: str

    _check_weight = validator('weight', allow_reuse=True)(check_weight)


class ClassEntry(BaseModel):
    '''A spellcasting class entry.'''
    name: str
    type: Literal['arcane'] | Literal['divine'] | Literal['occult']
    levels: list[int | None]
    duplicate: str | None = None
    merge: Sequence[str] | None = None

    @validator('levels')
    @classmethod
    def check_levels(cls: Type[ClassEntry], v: list[int | None], values: dict[str, Any]) -> list[int | None]:
        if len(v) > MAX_SPELL_LEVEL + 1:
            raise ValueError(f'Too many spell levels in { values["name"] } class entry, no more than { MAX_SPELL_LEVEL + 1 } may be specified.')

        last = v[0]

        if last is not None and last < 1:
            raise ValueError(f'Spell level 0 level is less than 1 in { values["name"] } class entry.')

        for idx, level in enumerate(v[1:]):
            if last is not None:
                if level is None:
                    raise ValueError('Sparse spell lists are not supported.')
                elif level < last:
                    raise ValueError(f'Spell level { idx } level is lower than spell level { idx } level in { values["name"] } class entry.')
                elif level < 1:
                    raise ValueError(f'Spell level { idx } level is less than 1 in { values["name"] } class entry.')

            last = level

        return v

    @root_validator
    @classmethod
    def mutex_duplicate_merge(cls: Type[ClassEntry], values: dict[str, Any]) -> dict[str, Any]:
        '''Duplicate and merge keys are mutually exclusive.'''
        if values.get('duplicate') is not None and values.get('merge') is not None:
            raise ValueError('Only one of duplicate or merge key may be defined on a class entry.')

        return values


ClassMap = Mapping[str, ClassEntry]


class BaseItem(BaseModel):
    '''Base class for item entries.'''
    weight: int = 1
    reroll: Sequence[str] | None = None
    cost: _Cost | None = None
    costrange: CostRange | None = None
    costmult: Cost | None = None

    _check_weight = validator('weight', allow_reuse=True)(check_weight)

    @validator('cost')
    @classmethod
    def check_cost(cls: Type[BaseItem], v: _Cost) -> _Cost:
        if v is not None and v != 'varies':
            if v < 0:
                raise ValueError('Cost must be at least zero.')

        return v

    @validator('costrange')
    @classmethod
    def check_costrange(cls: Type[BaseItem], v: CostRange, values: dict[str, Any]) -> CostRange:
        if v is not None:
            if values.get('cost') is not None or values.get('costmult') is not None:
                raise TypeError('If costrange is specified, cost and costmult may not be specified.')

            if v[0] < 0:
                raise ValueError('Lower cost limit must be greater than or equal to zero.')

            if v[1] < 0:
                raise ValueError('Upper cost limit must be greater than or equal to zero.')

            if v[0] == float('inf'):
                raise ValueError('Lower cost limit must not be infinite.')

            if v[1] == float('inf'):
                raise ValueError('Upper cost limit must not be infinite.')

            if v[0] > v[1]:
                raise ValueError('Upper cost limit must be less than or equal to lower cost limit.')

        return v

    @validator('costmult')
    @classmethod
    def check_costmult(cls: Type[BaseItem], v: Cost) -> Cost:
        if v is not None:
            if v < 1:
                raise ValueError('Cost must be at least one.')

        return v


class SpellParams(BaseModel):
    '''Parameters for rolling a spell for an item.'''
    level: int | None = None
    cls: str | None = None

    _check_level = validator('level', allow_reuse=True)(check_spell_level)


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
    @classmethod
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
    @classmethod
    def check_classes(cls: Type[Spell], v: MutableMapping[str, int], values: dict[str, Any]) -> MutableMapping[str, int]:
        for c, l in v.items():
            try:
                check_spell_level(l)
            except (ValueError, TypeError) as e:
                raise ValueError(f'Invalid spell level for class { c } in { values["name"] }: { e }')

        return v

    @validator('domains')
    @classmethod
    def check_domains(cls: Type[Spell], v: MutableMapping[str, int], values: dict[str, Any]) -> MutableMapping[str, int]:
        for c, l in v.items():
            try:
                check_spell_level(l)
            except (ValueError, TypeError) as e:
                raise ValueError(f'Invalid spell level for domain { c } in { values["name"] }: { e }')

        return v

    @validator('school')
    @classmethod
    def check_school(cls: Type[Spell], v: str, values: dict[str, Any]) -> str:
        if not v:
            raise ValueError(f'Missing school for { values["name"] }.')

        return v

    def process_classes(self: Spell, classes: ClassMap) -> None:
        '''Determine derived classes for this spell based on classes and sanity check levels.'''
        for cls, level in self.classes.items():
            if cls in {'minimum', 'spellpage_arcane', 'spellpage_divine'}:
                continue

            if cls not in classes:
                raise ValueError(f'Spell entry for { self.name } references non-existent class { cls }.')

            if level > len(classes[cls].levels) - 1:
                raise ValueError(f'Spell level for class { cls } in { self.name } is higher than the number of levels defined for that class.')

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


class SpellItem(BaseItem):
    '''Base class for an item with an embedded spell.'''
    spell: SpellParams
    rolled_spell: Spell | None = None
    cls: str | None = None
    level: int | None = None
    caster_level: int | None = None

    _check_level = validator('level', allow_reuse=True)(check_spell_level)

    @validator('caster_level')
    @classmethod
    def check_caster_level(cls: Type[SpellItem], v: int | None) -> int | None:
        if v is not None:
            if v < 1:
                raise ValueError('Caster level must be at least 1.')

        return v


class SimpleItem(BaseItem):
    '''A basic item entry.'''
    name: str = ''


class SimpleSpellItem(SimpleItem, SpellItem):
    '''A basic item entry with an embedded spell.'''
    pass


class CompoundItem(SimpleItem, RankWeights):
    '''An entry for an item in a compound item list.'''
    pass


class CompoundSpellItem(CompoundItem, SpellItem):
    '''An entry for a compound item with an embedded spell.'''
    pass


class OrdnancePattern(BaseItem):
    '''A pattern entry for constructing an ordnance item.'''
    bonus: EnchantBonus | None = None
    enchants: Sequence[EnchantBonus] | None = None
    specific: Sequence[str] | None = None

    _check_bonus = validator('bonus', allow_reuse=True)(check_enchant_bonus)

    @validator('enchants')
    @classmethod
    def check_enchants(cls: Type[OrdnancePattern], v: Sequence[EnchantBonus] | None) -> Sequence[EnchantBonus] | None:
        if v is not None:
            for i in v:
                try:
                    check_enchant_bonus(i)
                except (ValueError, TypeError) as e:
                    raise ValueError(f'Invalid enchantment bonus in enchantment list: { e }')

        return v

    @validator('specific')
    @classmethod
    def check_specific(cls: Type[OrdnancePattern], v: Sequence[str] | None, values: dict[str, Any]) -> Sequence[str] | None:
        if v is not None:
            if values.get('bonus') is not None or values.get('enchants') is not None:
                raise TypeError('specific key is mutually exclusive with bonus and enchants keys.')

            if len(v) not in {2, 3}:
                raise TypeError('specific key should have exactly two or three items.')

        return v


OrdnanceSpecific = SimpleItem


class OrdnanceBaseItem(BaseItem):
    '''A base ordnance item entry.'''
    type: str
    tags: set[Tag]
    name: str
    count: int | None = None

    @validator('count')
    @classmethod
    def check_count(cls: Type[OrdnanceBaseItem], v: int | None) -> int | None:
        if v is not None:
            if v < 1:
                raise ValueError('Count must be at least 1.')

        return v


class EnchantLimits(BaseModel):
    '''Information specifying tag limits for enchantments.'''
    only: Sequence[Tag] | None = None
    none: Sequence[Tag] | None = None


class OrdnanceEnchant(BaseItem):
    '''An enchantment entry for ordnance items.'''
    name: str
    bonuscost: Cost | None = None
    bonus: EnchantBonus | None = None
    exclude: list[str] | None = None
    remove: list[str] | None = None
    add: list[str] | None = None
    limit: EnchantLimits | None = None

    _check_bonus = validator('bonus', allow_reuse=True)(check_enchant_bonus)

    @validator('bonuscost')
    @classmethod
    def check_bonuscost(cls: Type[OrdnanceEnchant], v: Cost | None) -> Cost | None:
        if v is not None:
            if v < 0:
                raise ValueError('Bonus cost for enchantment must be at least 0.')

        return v


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
