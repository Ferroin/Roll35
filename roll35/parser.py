'''Provides basic command parameter parsing functionality.'''

import logging
import shlex

from io import StringIO

logger = logging.getLogger(__name__)


class Parser:
    '''A simple class for parsing commands into a dictionary.

       Takes a schema in the form of a dict. Keys correspond to target
       keys for the parsed output, while values are dicts that define
       how to produce the value for that key.

       Each value recognizes the following keys:
       - `type`: Specifies a callable to pass the token to to convert
         it to the desired type.
       - `names`: A list of strings which are used to indicate the
         specified token.
       '''
    def __init__(self, schema):
        self._schema = schema
        self._rindex = dict()

        for key in schema.keys():
            for name in schema[key]['names']:
                self._rindex[name] = key

    def parse(self, data):
        '''Parse a string using the schema.

           Returns either a tuple of True and the dictionary produced
           by the parser, or False and an error message.'''
        if data is None:
            return (True, dict())

        ret = dict()

        for key in self._schema:
            ret[key] = None

        lexer = shlex.shlex(StringIO(data), posix=True)

        while True:
            match lexer.get_token():
                case lexer.eof:
                    return (True, ret)
                case token if token in self._rindex:
                    key = self._rindex[token]
                    value = lexer.get_token()
                    schema = self._schema[key]

                    if value == lexer.eof:
                        return (False, f'Unexpected end of arguments after `{ token }`.')

                    if 'type' in schema:
                        try:
                            ret[key] = schema['type'](value)
                        except Exception:
                            return (False, f'Failed to parse `{ value }` as value for `{ token }`.')
                    else:
                        ret[key] = value
                case token:
                    return (False, f'Unrecognized token `{ token }`.')
