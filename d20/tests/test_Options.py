import unittest
import datetime

from d20.Manual.Options import (Arguments, CerberusSchemaGenerator)


class TestOptions(unittest.TestCase):
    def test_empty_arguments(self):
        Arguments()

    def test_arguments_wrong_type(self):
        with self.assertRaises(TypeError):
            Arguments("test")

    def test_valid_arguments(self):
        arg = Arguments(('option1', {}))

        with self.assertRaises(ValueError):
            arg.parse({'foo': 'bar'})

        options = arg.parse({'option1': 'bar'})

        self.assertDictEqual(
            options,
            {'option1': 'bar', 'common': {}})

        self.assertDictEqual(arg.docs, arg._schemaGenerator._docs)

    def test_schema_generator(self):
        schemaGenerator = CerberusSchemaGenerator()

        schemaGenerator.add_argument('foo', type=str, help="Test")

        with self.assertRaises(ValueError):
            schemaGenerator.add_argument('foo', type=str, help="Test")

        self.assertDictEqual(
            schemaGenerator._docs['foo'],
            {'type': str, 'default': schemaGenerator.empty, 'help': 'Test'})
        self.assertIn('foo', schemaGenerator._schema.keys())

    def test_schema_generator_types(self):
        schemaGenerator = CerberusSchemaGenerator()

        self.assertEqual(
            schemaGenerator.python2CerberusType(str), 'string')
        self.assertEqual(
            schemaGenerator.python2CerberusType(int), 'integer')
        self.assertEqual(
            schemaGenerator.python2CerberusType(bytes), 'binary')
        self.assertEqual(
            schemaGenerator.python2CerberusType(bytearray), 'binary')
        self.assertEqual(
            schemaGenerator.python2CerberusType(datetime.date), 'date')
        self.assertEqual(
            schemaGenerator.python2CerberusType(datetime.datetime), 'datetime')
        self.assertEqual(
            schemaGenerator.python2CerberusType(dict), 'dict')
        self.assertEqual(
            schemaGenerator.python2CerberusType(float), 'float')
        self.assertEqual(
            schemaGenerator.python2CerberusType(list), 'list')
        self.assertEqual(
            schemaGenerator.python2CerberusType(set), 'set')
        self.assertEqual(
            schemaGenerator.python2CerberusType(bool), 'boolean')

        with self.assertRaises(TypeError):
            schemaGenerator.python2CerberusType(type('foo', tuple(), dict()))
