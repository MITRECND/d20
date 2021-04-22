import datetime
import cerberus

from d20.Manual.Logger import logging

LOGGER = logging.getLogger(__name__)


class _empty:
    """Marker object for CerberusSchemaGenerator.empty"""


class Arguments:
    def __init__(self, *args, **kwargs):
        self._schemaGenerator = CerberusSchemaGenerator()

        for arg in args:
            if not isinstance(arg, tuple):
                raise TypeError("Expected a tuple of (name, {args})")
            (name, arguments) = arg

            self._schemaGenerator.add_argument(
                name, **arguments
            )

        self._validator = cerberus.Validator(
            self._schemaGenerator.schema
        )

    def parse(self, arguments, common=None):
        valid = self._validator.validate(arguments)
        if not valid:
            raise ValueError(
                "Unable to verify config: %s"
                % (self._validator.errors))

        options = self._validator.normalized(arguments)
        if common is None:
            common = dict()
        options['common'] = common

        return options

    @property
    def docs(self):
        return self._schemaGenerator._docs


class CerberusSchemaGenerator:
    empty = _empty

    def __init__(self):
        self._schema = dict()
        self._docs = dict()

    def python2CerberusType(self, type):
        if type == str:
            return 'string'
        elif type == int:
            return 'integer'
        elif type in [bytes, bytearray]:
            return 'binary'
        elif type == datetime.date:
            return 'date'
        elif type == datetime.datetime:
            return 'datetime'
        elif type == dict:
            return 'dict'
        elif type == float:
            return 'float'
        elif type == list:
            return 'list'
        elif type == set:
            return 'set'
        elif type == bool:
            return 'boolean'
        else:
            raise TypeError("Unknown type")

    def add_argument(
            self, name, type=str, help=None,
            default=_empty, **kwargs):

        if name in self._docs:
            raise ValueError("Argument already exists")

        self._docs[name] = {
            'type': type,
            'default': default,
            'help': help
        }

        arg_schema = {
            'type': self.python2CerberusType(type),
            'nullable': True
        }

        if default is not self.empty:
            arg_schema['default'] = default

        self._schema[name] = arg_schema

    @property
    def schema(self):
        return self._schema
