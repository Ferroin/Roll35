# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Enumerables defining valid values for ranks.'''

from __future__ import annotations

import enum

from dataclasses import dataclass


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


@dataclass
class RankWeights:
    '''A set of weights for ranks for an item entry.'''
    minor: int
    medium: int
    major: int
