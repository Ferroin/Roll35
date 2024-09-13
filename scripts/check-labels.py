#!/usr/bin/env python3

'''
Validate GitHub label configuration.

Copyright (C) 2024 Austin S. Hemmelgarn

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
'''

import sys

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Discriminator, Field, Tag, TypeAdapter
from ruamel.yaml import YAML as Yaml, YAMLError

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
SRC_DIR = SCRIPT_DIR.parent

# Regex defining accepted label names.
# The limitations it describes are our own and are imposed for consistency.
LABEL_REGEX = r'^([a-zA-Z0-9 ._/-])+$'

# Regex for matching six-digit hexadecimal strings.
COLOR_REGEX = r'^[a-fA-F0-9]{6}$'

YAML = Yaml(typ='safe')


class LabelEntry(BaseModel):
    name: Annotated[str, Field(pattern=LABEL_REGEX)]
    description: Annotated[str, Field(min_length=1, max_length=100)]
    color: Annotated[str, Field(pattern=COLOR_REGEX)]


LabelListAdapter = TypeAdapter(Annotated[Sequence[LabelEntry], Field(min_length=1)])  # type: ignore

REGEX_LIST = Annotated[Sequence[Annotated[str, Field(min_length=1)]], Field(min_length=1)]


class ChangedFiles1(BaseModel):
    any_glob_to_any_file: REGEX_LIST = Field(alias='any-glob-to-any-file')


class ChangedFiles2(BaseModel):
    any_glob_to_all_files: REGEX_LIST = Field(alias='any-glob-to-all-files')


class ChangedFiles3(BaseModel):
    all_globs_to_any_file: REGEX_LIST = Field(alias='all-globs-to-any-file')


class ChangedFiles4(BaseModel):
    all_globs_to_all_files: REGEX_LIST = Field(alias='all-globs-to-all-files')


def cf_disc(item: Any) -> str:
    match item:
        case {'any-glob-to-any-file': _}:
            return 'CF1'
        case {'any-glob-to-all-files': _}:
            return 'CF2'
        case {'all-globs-to-any-file': _}:
            return 'CF3'
        case {'all-globs-to-all-files': _}:
            return 'CF4'
        case _:
            raise ValueError


CF = Annotated[
    Annotated[ChangedFiles1, Tag('CF1')] |
    Annotated[ChangedFiles2, Tag('CF2')] |
    Annotated[ChangedFiles3, Tag('CF3')] |
    Annotated[ChangedFiles4, Tag('CF4')],
    Discriminator(cf_disc)
]


class ChangedFilesEntry(BaseModel):
    changed_files: Annotated[Sequence[CF], Field(min_length=1, max_length=1)] = Field(alias='changed-files')


class HeadBranchEntry(BaseModel):
    head_branches: REGEX_LIST = Field(alias='head-branches')


class BaseBranchEntry(BaseModel):
    base_branches: REGEX_LIST = Field(alias='base-branches')


def ll_disc(item: Any) -> str:
    match item:
        case {'changed-files': _}:
            return 'CF'
        case {'head-branches': _}:
            return 'HB'
        case {'base-branches': _}:
            return 'BB'
        case _:
            raise ValueError


LL = Annotated[
    Annotated[ChangedFilesEntry, Tag('CF')] |
    Annotated[HeadBranchEntry, Tag('HB')] |
    Annotated[BaseBranchEntry, Tag('BB')],
    Discriminator(ll_disc)
]


class LabelAnyLimits(BaseModel):
    any: Annotated[Sequence[LL], Field(min_length=1)]


class LabelAllLimits(BaseModel):
    all: Annotated[Sequence[LL], Field(min_length=1)]


def lal_disc(item: Any) -> str:
    match item:
        case {'any': _}:
            return 'any'
        case {'all': _}:
            return 'all'
        case _:
            raise ValueError


LAL = Annotated[
    Annotated[LabelAnyLimits, Tag('any')] |
    Annotated[LabelAllLimits, Tag('all')],
    Discriminator(lal_disc)
]

LabelerMapAdapter = TypeAdapter(  # type: ignore
    Annotated[
        Mapping[
            Annotated[
                str,
                Field(pattern=LABEL_REGEX),
            ],
            Annotated[
                Sequence[LAL],
                Field(min_length=1),
            ]
        ],
        Field(min_length=1),
    ]
)


def validate_labels_config(labels_config: Any) -> bool:
    '''Validate the labels config file.'''
    ret = True

    labels_config = LabelListAdapter.validate_python(labels_config)

    seen_labels = set()

    for idx, item in enumerate(labels_config):
        if item.name in seen_labels:
            print(f'!!! Duplicate label name at index {idx} in labels config.')  # noqa: DB100
            ret = False

        seen_labels.add(item.name)

    if ret:
        print('>>> Labels config has valid syntax.')  # noqa: DB100

    return ret


def validate_labeler_config(labeler_config: Any) -> bool:
    '''Validate the labeler config file.'''
    if not isinstance(labeler_config, dict):
        print('!!! Top level of labeler configuration is not a mapping.')  # noqa: DB100

    ret = True

    labeler_config = LabelerMapAdapter.validate_python(labeler_config)

    if ret:
        print('>>> Labeler config has valid syntax.')  # noqa: DB100

    return ret


def check_labeler_labels(labels: Any, labeler_config: Any) -> bool:
    '''Confirm that all labels in the labeler config exist.'''
    missing_labeler_labels = {x for x in labeler_config.keys()
                              if x not in labels}

    if missing_labeler_labels:
        print('!!! Missing labels found in labeler config:' +  # noqa: DB100
              f'{str(missing_labeler_labels)}')
        return False

    print('>>> All labels in labeler config are defined in labels config.')  # noqa: DB100
    return True


def check_dependabot_labels(labels: Any, dependabot_config: Any) -> bool:
    '''Confirm that dependabot labels are all correct.'''
    ret = True

    for idx, entry in enumerate(dependabot_config['updates']):
        if 'labels' in entry:
            missing_labels = {x for x in entry['labels'] if x not in labels}

            if missing_labels:
                print('!!! Missing labels found in dependabot config entry { idx }:' +  # noqa: DB100
                      f'{str(missing_labels)}')
                ret = False

    if ret:
        print('>>> All labels in dependabot config are defined in labels config.')  # noqa: DB100

    return ret


try:
    LABELS_CONFIG = YAML.load(SRC_DIR / '.github' / 'labels.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labels configuration file.')  # noqa: DB100
    sys.exit(1)

try:
    LABELER_CONFIG = YAML.load(SRC_DIR / '.github' / 'labeler.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labeler configuration file.')  # noqa: DB100
    sys.exit(1)

try:
    DEPENDABOT_CONFIG = YAML.load(SRC_DIR / '.github' / 'dependabot.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labeler configuration file.')  # noqa: DB100
    sys.exit(1)

if not all([
        validate_labels_config(LABELS_CONFIG),
        validate_labeler_config(LABELER_CONFIG),
       ]):
    sys.exit(1)

LABELS = [x['name'] for x in LABELS_CONFIG]

if not all([
        check_labeler_labels(LABELS, LABELER_CONFIG),
        check_dependabot_labels(LABELS, DEPENDABOT_CONFIG),
       ]):
    sys.exit(1)
