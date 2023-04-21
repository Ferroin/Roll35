#!/usr/bin/env python3

'''
Validate GitHub label configuration.

Copyright (C) 2023 Austin S. Hemmelgarn

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

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS "AS IS"
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

import re
import sys

from pathlib import Path

from ruamel.yaml import YAML as Yaml
from ruamel.yaml import YAMLError


SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
SRC_DIR = SCRIPT_DIR.parent

# Regex defining accepted label names.
# The limitations it describes are our own and are imposed for consistency.
LABEL_REGEX = re.compile('^([a-zA-Z0-9 ._/-])+$')

# Regex for matching six-digit hexadecimal strings.
COLOR_REGEX = re.compile('^[a-fA-F0-9]{6}$')

YAML = Yaml(typ="safe")


def validate_labels_config(labels_config):
    '''Validate the labels config file.'''
    if not isinstance(labels_config, list):
        print('!!! Top level of labels configuration is not a list.')
        sys.exit(1)

    ret = True

    for idx, item in enumerate(labels_config):
        match item:
            case {'name': n, 'description': d, 'color': c, **other}:
                if other:
                    print(f'!!! Unrecognized keys for { n } in labels config.')
                    ret = False

                if not isinstance(n, str):
                    print(f'!!! Label name is not a string at index { idx }' +
                          ' in labels config.')
                    ret = False
                elif not LABEL_REGEX.match(n):
                    print(f'!!! Label name { n } is not valid. ' +
                          'Label names must consist only of English letters, numbers, ' +
                          '`/`, `-`, `_`, `.`, or spaces.')
                    ret = False

                if not isinstance(d, str):
                    print(f'!!! Description for label { n } is not a string.')
                    ret = False
                elif len(d) > 100:
                    print(f'!!! Description for label { n } is too long. GitHub limits descriptions to 100 characters.')
                    ret = False

                if not isinstance(c, str):
                    print(f'!!! Color for label { n } is not a string. Did you forget to quote it?')
                    ret = False
                elif not COLOR_REGEX.match(c):
                    print(f'!!! Color for label { n } is not a six-digit hexidecimal string.')
                    ret = False
            case {**other}:
                for k in {'name', 'description', 'color'}:
                    if k not in other.keys():
                        print(f'!!! Missing { k } entry at index { idx }' +
                              ' in labels config.')
                        ret = False
            case _:
                print(f'!!! Incorrect type at index { idx } in labels config.')
                sys.exit(1)

    if ret:
        print('>>> Labels config has valid syntax.')

    return ret


def validate_labeler_config(labeler_config):
    '''Validate the labeler config file.'''
    if not isinstance(labeler_config, dict):
        print('!!! Top level of labeler configuration is not a mapping.')

    ret = True

    for key, value in labeler_config.items():
        if not isinstance(key, str):
            print(f'!!! \'{ key }\' in labeler config is not a string.')
            ret = False

        if not isinstance(value, list):
            print(f'!!! Invalid type for value of { key } in labeler config.')
            ret = False
            continue

        match value:
            case [{'all': [*_], 'any': [*_]}]:
                pass
            case [{'all': [*_]}]:
                pass
            case [{'any': [*_]}]:
                pass
            case [*results] if all(map(lambda x: isinstance(x, str), results)):
                pass
            case [*results]:
                for idx, item in enumerate(results):
                    if not isinstance(item, str):
                        print(f'!!! Invalid item at index { idx } for '
                              f'{ key } in labeler configuration')
                        ret = False

    if ret:
        print('>>> Labeler config has valid syntax.')

    return ret


def check_labeler_labels(labels, labeler_config):
    '''Confirm that all labels in the labeler config exist.'''
    missing_labeler_labels = {x for x in labeler_config.keys()
                              if x not in labels}

    if missing_labeler_labels:
        print('!!! Missing labels found in labeler config:' +
              f'{ str(missing_labeler_labels) }')
        return False

    print('>>> All labels in labeler config are defined in labels config.')
    return True


def check_dependabot_labels(labels, dependabot_config):
    '''Confirm that dependabot labels are all correct.'''
    ret = True

    for idx, entry in enumerate(dependabot_config['updates']):
        if 'labels' in entry:
            missing_labels = {x for x in entry['labels'] if x not in labels}

            if missing_labels:
                print('!!! Missing labels found in dependabot config entry { idx }:' +
                      f'{ str(missing_labels) }')
                ret = False

    if ret:
        print('>>> All labels in dependabot config are defined in labels config.')

    return ret


try:
    LABELS_CONFIG = YAML.load(SRC_DIR / '.github' / 'labels.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labels configuration file.')
    sys.exit(1)

try:
    LABELER_CONFIG = YAML.load(SRC_DIR / '.github' / 'labeler.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labeler configuration file.')
    sys.exit(1)

try:
    DEPENDABOT_CONFIG = YAML.load(SRC_DIR / '.github' / 'dependabot.yml')
except (YAMLError, IOError, OSError):
    print('!!! Failed to load labeler configuration file.')
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
