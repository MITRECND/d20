import unittest
from unittest import mock

from d20.Manual.Facts import (Fact,
                              registerFact,
                              resolveFacts,
                              getFactClass,
                              isFact,
                              isFactGroup,
                              loadFact,
                              loadFacts)

from d20.Manual.Facts.Fields import FactField

# from d20.Manual.Facts.Facts import MD5HashFact

from d20.Manual.Facts.Fields import (StringField,
                                     BooleanField,
                                     BytesField,
                                     IntegerField,
                                     ListField,
                                     NumericalField,
                                     StrOrBytesField,
                                     ConstrainedList)


class TestFacts(unittest.TestCase):
    def test1FactRegistration1(self):
        """Test creation/registration of facts
            1 - Basic registration
            2 - Registration with function syntax
            3 - Registration with a fact group
        """
        @registerFact
        class TestFact(Fact):
            _type_ = 'test1'

        with self.assertRaises(ValueError):
            @registerFact
            class InvalidFact(Fact):
                """Invalid"""

        @registerFact()
        class TestFact2(Fact):
            _type_ = 'test2'

        @registerFact('testgroup')
        class TestFact3(Fact):
            _type_ = 'test3'

        with self.assertRaises(ValueError):
            @registerFact
            class TestFact2_2(Fact):
                _type_ = 'test2'

        with self.assertRaises(TypeError):
            @registerFact(list('foo'))
            class TesetFact3_5(Fact):
                _type_ = 'test3.5'

        self.assertTrue(isFact('test1'))
        self.assertFalse(isFact('notafact'))
        self.assertTrue(isFactGroup('testgroup'))
        self.assertFalse(isFactGroup('notagroup'))

        with self.assertRaises(TypeError):
            @registerFact
            class InvalidFact2:
                _type_ = 'invalidfact2'

    def test2DuplicateFact(self):
        with self.assertRaises(ValueError):
            @registerFact()
            class TestFact(Fact):
                _type_ = 'test1'

    def test3ResolveGroup(self):
        foo = resolveFacts('testgroup')
        self.assertEqual(foo, ['test3'])

    def test4FactClass(self):
        global TestFact4

        @registerFact
        class TestFact4(Fact):
            _type_ = 'test4'

        fcls = getFactClass('TestFact4')
        self.assertEqual(fcls, TestFact4)

    def test5FactBinding(self):
        @registerFact
        class TestFact5(Fact):
            _type_ = 'test5'
            value = StringField()
            field2 = BooleanField()

        TestFact5(value='test', field2=True)

    def test6SaveLoad(self):
        @registerFact
        class TestFact6(Fact):
            _type_ = 'test6'
            value = StringField()

        foo = TestFact6(value='bar')
        data = foo.save()
        bar = TestFact6.load(**data)
        self.assertEqual(foo.value, bar.value)

    def test7InvalidFieldName(self):
        with self.assertRaises(AttributeError):
            @registerFact
            class TestFact7_1(Fact):
                _type_ = 'test7'
                _id_ = StringField()

        with self.assertRaises(AttributeError):
            @registerFact
            class TestFact7_2(Fact):
                _type_ = 'test7.5'
                __eq__ = StringField()

    def test8InvalidArgument(self):
        @registerFact
        class TestFact8(Fact):
            _type_ = 'test8'
            value = StringField()

        with self.assertRaises(TypeError):
            TestFact8(childFacts=set())

    def test9InvalidFactResolve(self):
        with self.assertRaises(ValueError):
            resolveFacts('test1', 'nosuchfact')

    @mock.patch("d20.Manual.Facts.Parameter")
    @mock.patch("d20.Manual.Facts.Signature")
    def test10FactMembers(self, signature, parameter):
        parameter.return_value = None

        @registerFact
        class TestFact9(Fact):
            _type_ = 'test9'
            value = StringField(default='test')

        parameter.assert_has_calls([
            mock.call("value", parameter.KEYWORD_ONLY, default='test'),
            mock.call("kwargs", parameter.VAR_KEYWORD)
        ])
        parameter.reset_mock()

        @registerFact
        class TestFact10(Fact):
            _type_ = 'test10'
            # Since we are mocking Parameter, default needs to be manually set
            # otherwise code in Fields.py will set it to Parameter.empty
            # which is not equal to mock class
            value = StringField(required=True, default=parameter.empty)

        parameter.assert_has_calls([
            mock.call(
                "value", parameter.KEYWORD_ONLY, default=parameter.empty),
            mock.call("kwargs", parameter.VAR_KEYWORD)
        ])

    def test11FactMembers(self):
        with self.assertRaises(TypeError):
            @registerFact
            class TestFact11(Fact):
                _type_ = 'test11'
                value = StringField(help=list('foo'))

        @registerFact
        class TestFact12(Fact):
            _type_ = 'test12'
            value = StringField(help='test')

        self.assertEqual(TestFact12.value.__doc__, 'test')


class TestFactUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global TestFactUsage1

        @registerFact('testusages')
        class TestFactUsage1(Fact):
            _type_ = 'testusage1'
            field1 = StringField()
            field2 = NumericalField()

    def test1Creation(self):
        with self.assertRaises(TypeError):
            TestFactUsage1(parentObjects={'test': 'test'})

        with self.assertRaises(TypeError):
            TestFactUsage1(parentFacts={'test': 'test'})

        with self.assertRaises(TypeError):
            TestFactUsage1(parentHyps={'test': 'test'})

        with self.assertRaises(TypeError):
            TestFactUsage1(_childObjects_={'test': 'test'})

        with self.assertRaises(TypeError):
            TestFactUsage1(_childFacts_={'test': 'test'})

        with self.assertRaises(TypeError):
            TestFactUsage1(_childHyps_={'test': 'test'})

        tf = TestFactUsage1()
        self.assertEqual(tf.factType, 'testusage1')
        self.assertEqual(tf.factGroups, ('testusages',))

        tf._taint()
        self.assertTrue(tf.tainted)
        tf._untaint()
        self.assertFalse(tf.tainted)

    def test2Relationships(self):
        tf = TestFactUsage1(
            parentObjects=[1],
            parentFacts=[1],
            parentHyps=[1],
            _childObjects_=[1],
            _childFacts_=[1],
            _childHyps_=[1]
        )

        tf.addParentObject(2)
        self.assertEqual(tf.parentObjects, [1, 2])
        tf.remParentObject(1)
        self.assertEqual(tf.parentObjects, [2])

        tf.addParentFact(2)
        self.assertEqual(tf.parentFacts, [1, 2])
        tf.remParentFact(1)
        self.assertEqual(tf.parentFacts, [2])

        tf.addParentHyp(2)
        self.assertEqual(tf.parentHyps, [1, 2])
        tf.remParentHyp(1)
        self.assertEqual(tf.parentHyps, [2])

        tf.addChildObject(2)
        self.assertEqual(tf.childObjects, [1, 2])
        tf.remChildObject(1)
        self.assertEqual(tf.childObjects, [2])

        tf.addChildFact(2)
        self.assertEqual(tf.childFacts, [1, 2])
        tf.remChildFact(1)
        self.assertEqual(tf.childFacts, [2])

        tf.addChildHyp(2)
        self.assertEqual(tf.childHyps, [1, 2])
        tf.remChildHyp(1)
        self.assertEqual(tf.childHyps, [2])


class TestFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global TestFieldsFact1

        @registerFact
        class TestFieldsFact1(Fact):
            _type_ = 'testfields1'
            field1 = StringField()
            field2 = BooleanField()
            field3 = BytesField()
            field4 = IntegerField()
            field5 = StrOrBytesField()
            field6 = ListField()
            field7 = ListField(valType=int)
            field8 = NumericalField()

    def test1InvalidTypeEnforcement(self):
        foo = TestFieldsFact1()
        with self.assertRaises(TypeError):
            foo.field1 = True

        with self.assertRaises(TypeError):
            foo.field2 = "Foo"

        with self.assertRaises(TypeError):
            foo.field5 = 1

        with self.assertRaises(TypeError):
            foo.field6 = 1

        with self.assertRaises(TypeError):
            foo.field7 = ['test']

        with self.assertRaises(TypeError):
            foo.field8 = 'test'

    def test2FactFields(self):
        foo = TestFieldsFact1()
        foo.field1 = "String"
        foo.field2 = True
        foo.field3 = b'foo'
        foo.field6 = ['test']
        foo.field7 = [1]

    def test3FactFields(self):
        bar = TestFieldsFact1(field1='test', field5=b'testbinary')
        self.assertTrue(hasattr(bar, '_field1__'))
        self.assertTrue(isinstance(bar._field1__, FactField))
        self.assertTrue(hasattr(bar, 'field1'))
        self.assertEqual(bar._field1__.getShell(), 'test')

        self.assertTrue(hasattr(bar, 'field5'))
        self.assertTrue(hasattr(bar, '_field5__'))
        self.assertEqual(bar._field5__.getShell(), 'testbinary')

        with self.assertRaises(AttributeError):
            bar.field3

        with self.assertRaises(AttributeError):
            bar._field3__.getShell()

    def test4FactFields(self):
        bar = TestFieldsFact1()

        self.assertTrue(hasattr(bar, '_field5__'))
        with self.assertRaises(AttributeError):
            bar._field5__.getShell()

    def test5ConstrainedList(self):
        t1 = ConstrainedList(valType=int)
        t2 = ConstrainedList(['test'], valType=str)
        ConstrainedList([], valType=int)

        with self.assertRaises(TypeError):
            ConstrainedList([1], valType=str)

        t1.append(1)
        t1.extend([2, 3])
        self.assertEqual(list(t1), [1, 2, 3])
        t1 += [4, 5]
        self.assertIsInstance(t1, ConstrainedList)
        self.assertEqual(list(t1), [1, 2, 3, 4, 5])
        t1.insert(0, 0)

        with self.assertRaises(TypeError):
            t1 += t2


class TestFactMisc(unittest.TestCase):
    def testloadFact(self):
        with self.assertRaises(ValueError):
            loadFact('test')

    @mock.patch(
        "d20.Manual.Facts.os.path.abspath", return_value="/tmp/test/foo.py")
    @mock.patch(
        "d20.Manual.Facts.os.listdir",
        return_value=["foo.py", "bar", "foobar.py", "_special.py"])
    @mock.patch("d20.Manual.Facts.os.path.isfile", return_value=True)
    @mock.patch("d20.Manual.Utils.importlib.util")
    def testloadFacts(self, fimp, os_isfile,
                      os_listdir, os_abspath):
        fimp.spec_from_file_location = mock.MagicMock(side_effect=TypeError())
        with self.assertRaises(TypeError):
            loadFacts()

        fimp.spec_from_file_location = mock.MagicMock(
            side_effect=AttributeError())
        with self.assertRaises(AttributeError):
            loadFacts()

        fimp.spec_from_file_location = mock.MagicMock(side_effect=Exception())
        with self.assertRaises(RuntimeError):
            loadFacts()

        spec_mock = mock.MagicMock()
        spec_mock.loader = mock.MagicMock()
        fimp.spec_from_file_location = mock.MagicMock(return_value=(spec_mock))
        fimp.module_from_spec = mock.MagicMock(return_value=[True])
        loadFacts(facts_path=['/tmp/test2'])

        spec_mock.loader.exec_module.assert_called()
