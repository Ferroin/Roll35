# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Classes defining item formats.'''

from __future__ import annotations

from collections.abc import Sequence, Mapping, MutableMapping
from typing import Literal, TypeVar, Type, Any, cast

from pydantic import field_validator, model_validator, BaseModel, Field, FieldValidationInfo

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

    _check_weight = field_validator('weight')(check_weight)


class ClassEntry(BaseModel):
    '''A spellcasting class entry.'''
    name: str
    type: Literal['arcane'] | Literal['divine'] | Literal['occult']
    levels: list[int | None]
    duplicate: str | None = None
    merge: Sequence[str] | None = None

    @field_validator('levels')
    @classmethod
    def check_levels(cls: Type[ClassEntry], v: list[int | None], info: FieldValidationInfo) -> list[int | None]:
        if len(v) > MAX_SPELL_LEVEL + 1:
            raise ValueError(f'Too many spell levels in { info.data["name"] } class entry, no more than { MAX_SPELL_LEVEL + 1 } may be specified.')

        last = v[0]

        if last is not None and last < 1:
            raise ValueError(f'Spell level 0 level is less than 1 in { info.data["name"] } class entry.')

        for idx, level in enumerate(v[1:]):
            if last is not None:
                if level is None:
                    raise ValueError('Sparse spell lists are not supported.')
                elif level < last:
                    raise ValueError(f'Spell level { idx } level is lower than spell level { idx } level in { info.data["name"] } class entry.')
                elif level < 1:
                    raise ValueError(f'Spell level { idx } level is less than 1 in { info.data["name"] } class entry.')

            last = level

        return v

    @model_validator(mode='before')
    @classmethod
    def mutex_duplicate_merge(cls: Type[ClassEntry], values: dict[str, Any]) -> dict[str, Any]:
        '''Duplicate and merge keys are mutually exclusive.'''
        if values.get('duplicate') is not None and values.get('merge') is not None:
            raise ValueError('Only one of duplicate or merge key may be defined on a class entry.')

        return values

    def level_in_cls(self: ClassEntry, level: int) -> bool:
        '''Check if a given level of spell is available in this class.'''
        if level < 0:
            raise ValueError('Negative spell levels are not supported.')
        elif len(self.levels) <= level:
            return False
        elif self.levels[level] is None:
            return False

        return True


ClassMap = Mapping[str, ClassEntry]


class BaseItem(BaseModel):
    '''Base class for item entries.'''
    weight: int = 1
    reroll: Sequence[str] | None = None
    cost: _Cost | None = None
    costrange: CostRange | None = None
    costmult: Cost | None = None

    _check_weight = field_validator('weight')(check_weight)

    @field_validator('cost')
    @classmethod
    def check_cost(cls: Type[BaseItem], v: _Cost) -> _Cost:
        if v is not None and v != 'varies':
            if v < 0:
                raise ValueError('Cost must be at least zero.')

        return v

    @field_validator('costrange')
    @classmethod
    def check_costrange(cls: Type[BaseItem], v: CostRange, info: FieldValidationInfo) -> CostRange:
        if v is not None:
            if info.data.get('cost') is not None or info.data.get('costmult') is not None:
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

    @field_validator('costmult')
    @classmethod
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

    _check_level = field_validator('level')(check_spell_level)


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

    @field_validator('tags', mode='before')
    @classmethod
    def populate_tags(cls: Type[Spell], v: set[str], info: FieldValidationInfo) -> set[str]:
        if not v:
            t = {x for x in cast(str, info.data['descriptor']).split(', ') if x}

            if info.data['school']:
                t.add(cast(str, info.data['school']))

            if info.data['subschool']:
                t.add(cast(str, info.data['subschool']))
        else:
            t = v

        return t

    @field_validator('classes')
    @classmethod
    def check_classes(cls: Type[Spell], v: MutableMapping[str, int], info: FieldValidationInfo) -> MutableMapping[str, int]:
        for c, l in v.items():
            try:
                check_spell_level(l)
            except (ValueError, TypeError) as e:
                raise ValueError(f'Invalid spell level for class { c } in { info.data["name"] }: { e }')

        return v

    @field_validator('domains')
    @classmethod
    def check_domains(cls: Type[Spell], v: MutableMapping[str, int], info: FieldValidationInfo) -> MutableMapping[str, int]:
        for c, l in v.items():
            try:
                check_spell_level(l)
            except (ValueError, TypeError) as e:
                raise ValueError(f'Invalid spell level for domain { c } in { info.data["name"] }: { e }')

        return v

    @field_validator('school')
    @classmethod
    def check_school(cls: Type[Spell], v: str, info: FieldValidationInfo) -> str:
        if not v:
            raise ValueError(f'Missing school for { info.data["name"] }.')

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

    _check_level = field_validator('level')(check_spell_level)

    @field_validator('caster_level')
    @classmethod
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

    _check_bonus = field_validator('bonus')(check_enchant_bonus)

    @field_validator('enchants')
    @classmethod
    @classmethod
    def check_enchants(cls: Type[OrdnancePattern], v: Sequence[EnchantBonus] | None) -> Sequence[EnchantBonus] | None:
        if v is not None:
            for i in v:
                try:
                    check_enchant_bonus(i)
                except (ValueError, TypeError) as e:
                    raise ValueError(f'Invalid enchantment bonus in enchantment list: { e }')

        return v

    @field_validator('specific')
    @classmethod
    def check_specific(cls: Type[OrdnancePattern], v: Sequence[str] | None, info: FieldValidationInfo) -> Sequence[str] | None:
        if v is not None:
            if info.data.get('bonus') is not None or info.data.get('enchants') is not None:
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

    @field_validator('count')
    @classmethod
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

    def check_tags(self: EnchantLimits, tags: set[Tag]) -> None:
        if self.only is not None:
            for tag in self.only:
                if tag not in tags:
                    raise ValueError(f'Invalid tag in enchantment limits: { tag }')

        if self.none is not None:
            for tag in self.none:
                if tag not in tags:
                    raise ValueError(f'Invalid tag in enchantment limits: { tag }')


class OrdnanceEnchant(BaseItem):
    '''An enchantment entry for ordnance items.'''
    name: str
    bonuscost: Cost | None = None
    bonus: EnchantBonus | None = None
    exclude: list[str] | None = None
    remove: list[Tag] | None = None
    add: list[Tag] | None = None
    limit: EnchantLimits | None = None

    _check_bonus = field_validator('bonus')(check_enchant_bonus)

    @field_validator('bonuscost')
    @classmethod
    @classmethod
    def check_bonuscost(cls: Type[OrdnanceEnchant], v: Cost | None) -> Cost | None:
        if v is not None:
            if v < 0:
                raise ValueError('Bonus cost for enchantment must be at least 0.')

        return v

    def check_tags(self: OrdnanceEnchant, tags: set[Tag]) -> None:
        if self.limit is not None:
            try:
                self.limit.check_tags(tags)
            except Exception as e:
                raise ValueError(f'Invalid enchantment limits for { self.name }: { e }')

        if self.add is not None:
            for tag in self.add:
                if tag not in tags:
                    raise ValueError(f'Invalid tag in add key for { self.name }: { tag }')

        if self.remove is not None:
            for tag in self.remove:
                if tag not in tags:
                    raise ValueError(f'Invalid tag in remove key for { self.name }: { tag }')


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
