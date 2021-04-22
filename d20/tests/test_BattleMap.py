import unittest
from unittest import mock

from d20.Manual.BattleMap import (TableColumn,
                                  FactTable,
                                  HypothesisTable,
                                  ObjectList,
                                  FileObject)

from d20.Manual.Facts.Facts import (MD5HashFact,
                                    MimeTypeFact,
                                    SHA1HashFact)

from d20.Manual.Facts import Fact
from d20.Manual.Facts.Fields import (StringField)


class BMFactTests(unittest.TestCase):
    def test1TableColumnNoType(self):
        with self.assertRaises(TypeError):
            TableColumn()

    def test2TableColumn(self):
        testCol = TableColumn(MD5HashFact._type_)

        tfact1 = MD5HashFact()
        tfact2 = MimeTypeFact()

        with self.assertRaises(ValueError):
            testCol.append(tfact2)

        testCol.append(tfact1)

        for fact in testCol:
            self.assertTrue(isinstance(fact, MD5HashFact))

        self.assertEqual(testCol[0], tfact1)

        tColList = testCol.tolist()

        self.assertEqual(tColList[0], testCol[0])

        # tColList should be a shallow copy
        tColList.append(MD5HashFact())
        self.assertNotEqual(tColList, testCol.column)

        self.assertEqual(testCol.index(tfact1), 0)


class BMFactTableTests(unittest.TestCase):
    def setUp(self):
        self.facts = FactTable()

    def test1FactTableUnregisteredFact(self):
        class UnregFact(Fact):
            _type_ = 'unreg'
            value = StringField()

        with self.assertRaises(ValueError):
            self.facts.add(UnregFact())

    def test2AddingFact(self):
        tfact1 = MD5HashFact()
        self.assertTrue(self.facts.add(tfact1) == 0)
        self.assertEqual(tfact1, self.facts.findById(0))
        self.assertEqual(None, self.facts.findById(999))
        thyp1 = MD5HashFact()
        thyp1._taint()
        with self.assertRaises(TypeError):
            self.facts.add(thyp1)

    def test3FactTable(self):
        testFacts = [MD5HashFact() for i in range(5)]
        testFacts.extend([MimeTypeFact() for i in range(5)])

        for fact in testFacts:
            self.facts.add(fact)

        self.assertTrue(isinstance(
            self.facts.getColumn(MD5HashFact._type_), TableColumn))

        with self.assertRaises(ValueError):
            self.facts.getColumn('foo')

        self.assertEqual(self.facts.getColumn(SHA1HashFact._type_), None)
        self.assertListEqual(
            sorted(['md5', 'mimetype']), sorted(list(self.facts)))
        self.assertEqual(len(self.facts.columns()), 2)
        self.assertTrue(self.facts.hasColumn('md5'))
        self.assertFalse(self.facts.hasColumn('sha1'))
        with self.assertRaises(ValueError):
            self.facts.hasColumn('foobar')

    def test4SaveTable(self):
        testFacts = [MD5HashFact() for i in range(5)]

        for fact in testFacts:
            self.facts.add(fact)

        data = self.facts.save()
        self.assertEqual(data['ids'], 5)


class BMHypTableTests(unittest.TestCase):
    def setUp(self):
        self.hyps = HypothesisTable()

    def testAddHyp(self):
        thyp1 = MD5HashFact()
        thyp1._taint()
        self.assertEqual(self.hyps.add(thyp1), 0)
        ret = self.hyps.remove(0)
        self.assertEqual(thyp1, ret)


class BMFileObjectTests(unittest.TestCase):
    def setUp(self):
        self.data = b'testtesttesttest'
        self.strdata = str(self.data, 'utf-8')
        self.badata = bytearray(self.data)

    def test1FileObject(self):
        FileObject(self.data, 0)

        FileObject(self.strdata, 0)

        FileObject(self.badata, 0)

        with self.assertRaises(TypeError):
            FileObject(list(), 0)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentObjects_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentFacts_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentHyps_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentObjects_=1)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentFacts_=1)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _parentHyps_=1)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childObjects_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childFacts_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childHyps_=['test'])

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childObjects_=1)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childFacts_=1)

        with self.assertRaises(TypeError):
            FileObject(self.data, 0, _childHyps_=1)

        with self.assertRaises(TypeError):
            FileObject('testtesttest', 0, encoding='break')

    def test2FileObject(self):
        foo = FileObject(self.data, 0)

        foo.addParentObject(1)
        self.assertEqual([1], foo.parentObjects)
        foo.remParentObject(1)
        self.assertEqual([], foo.parentObjects)

        foo.addParentFact(1)
        self.assertEqual([1], foo.parentFacts)
        foo.remParentFact(1)
        self.assertEqual([], foo.parentFacts)

        foo.addParentHyp(1)
        self.assertEqual([1], foo.parentHyps)
        foo.remParentHyp(1)
        self.assertEqual([], foo.parentHyps)

        foo.addChildObject(1)
        self.assertEqual([1], foo.childObjects)
        foo.remChildObject(1)
        self.assertEqual([], foo.childObjects)

        foo.addChildFact(1)
        self.assertEqual([1], foo.childFacts)
        foo.remChildFact(1)
        self.assertEqual([], foo.childFacts)

        foo.addChildHyp(1)
        self.assertEqual([1], foo.childHyps)
        foo.remChildHyp(1)
        self.assertEqual([], foo.childHyps)

    def test3FileObject(self):
        foo = FileObject(self.data, 0)
        foo.add_metadata('test', 'value')
        self.assertEqual({'test': 'value'}, foo.metadata)
        self.assertEqual(foo.size, len(self.data))

    @mock.patch("d20.Manual.BattleMap.TemporaryObjectOnDisk")
    def test3FileObjTemp(self, tempObject):
        foo = FileObject(self.data, 0)
        foo.onDisk
        tempObject.assert_called_once_with(0, self.data)

    @mock.patch("d20.Manual.BattleMap.TemporaryObjectStream")
    def test3FileStreamTemp(self, tempStream):
        foo = FileObject(self.data, 0)
        foo.stream
        tempStream.assert_called_once_with(0, self.data)

    def testSaveLoad(self):
        tobj = FileObject(self.data, 0)
        data = tobj.save()

        FileObject.load(data)


class ObjectListTests(unittest.TestCase):
    def setUp(self):
        self.objects = ObjectList()
        self.data = b'testtesttest'

    @mock.patch("os.path")
    def testObjectListTemp(self, os_path):
        os_path.exists = mock.Mock(return_value=False)
        os_path.mkdirs = mock.Mock()
        os_path.join = mock.Mock(return_value="/var/foo/objects")

        ObjectList(temporary='/var/foo')
        os_path.exists.assert_called_once_with('/var/foo/objects')
        os_path.mkdirs.assert_called_once_with('/var/foo/objects')

    def testObjectList(self):
        obj = self.objects.addObject(self.data)
        self.assertEqual(self.objects.getObjectByData(self.data), obj)
        self.assertEqual(self.objects.getObjectByData(b'no'), None)

    def test2ObjectList(self):
        with self.assertRaises(TypeError):
            self.objects.append(list())

        objects = self.objects.tolist()
        self.assertIsInstance(objects, list)
