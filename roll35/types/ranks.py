# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Enumerables defining valid values for ranks.'''

from __future__ import annotations

import enum

from typing import Type

from pydantic import BaseModel, validator


@enum.unique
class Rank(enum.Enum):
    '''Defines possible ranks for magic items.'''
    MINOR = 'minor'
    MEDIUM = 'medium'
    MAJOR = 'major'


@enum.unique
class Subrank(enum.Enum):
    '''Defines possible subranks for magic items.'''
    LEAST = 'least'
    LESSER = 'lesser'
    GREATER = 'greater'


class RankWeights(BaseModel):
    '''A set of weights for ranks for an item entry.'''
    minor: int
    medium: int
    major: int

    @validator('minor', 'medium', 'major')
    @classmethod
    def check_weight(cls: Type[RankWeights], v: int) -> int:
        if v < 0:
            raise ValueError('Weight must be at least 0.')

        return v
