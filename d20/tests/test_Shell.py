import unittest
from unittest import mock
import os
import collections
from argparse import Namespace
import yaml
import tempfile
import pytest

from d20.Manual.Exceptions import NotFoundError
from d20.Manual.Config import Configuration
from d20.Manual.GameMaster import GameMaster
from d20.Manual.Shell import (BaseCmd, createHypsList, tsTodt,
                              askPrompt,
                              listObjects,
                              listFacts,
                              listHyps,
                              ShellCmd,
                              ObjectCmd,
                              FactCmd,
                              HypCmd,
                              prettyTable,
                              prettyList,
                              createObjectsList,
                              createFactsList,
                              FactHypBaseCmd)
from d20.Manual.Facts import Fact, loadFacts
from d20.tests import wrapOut

loadFacts()


class TestShellFunctions(unittest.TestCase):
    @mock.patch('d20.Manual.Shell.input', return_value='y')
    def testPromptY(self, input):
        self.assertTrue(askPrompt())

    @mock.patch('d20.Manual.Shell.input', return_value='n')
    def testPromptN(self, input):
        self.assertFalse(askPrompt())

    def testTimeString(self):
        ts = 1543509554.0126088
        self.assertEqual(tsTodt(ts), '2018-11-29 16:39:14.012609 UTC')


class TestShell(unittest.TestCase):
    def setUp(self):
        path = os.path.dirname(os.path.abspath(__file__))
        mock_args = Namespace()
        mock_args.statefile = os.path.join(path, "ls.d20")
        Config = Configuration(configFile=None, args=mock_args)
        with open(mock_args.statefile, 'r') as f:
            save_state = yaml.load(f.read(), Loader=yaml.FullLoader)

        gm = GameMaster(config=Config,
                        options=mock_args,
                        save_state=save_state)

        gm.load()
        self.gm = gm

    def testListFunctions(self):
        with mock.patch("d20.Manual.Shell.prettyTable",
                        return_value="Test"):
            self.assertEqual(listObjects(self.gm), "\nTest\n")
            self.assertEqual(listFacts(self.gm), "\nTest\n")
            self.assertEqual(listHyps(self.gm), "\nTest\n")

    def testBaseCmdMisc(self):
        shell = ShellCmd(self.gm)
        with wrapOut() as (out, err):
            shell.do_bc(None)
            self.assertEqual(out.getvalue(), "At root\n")

        # Artificially inflate depthList
        shell.depthList.append(self.gm.objects[0])
        bc = shell._parse_bc()
        self.assertEqual(len(bc), 1)
        self.assertListEqual(bc, [(0, "object", 0)])
        shell.depthList = list()

    def testBaseCmdObj(self):
        shell = ShellCmd(self.gm)
        with self.assertRaises(TypeError):
            shell._find_object(None)

        with self.assertRaises(ValueError):
            shell._find_object('test')

        with self.assertRaises(NotFoundError):
            shell._find_object(10)

        inst = shell._find_object(0)
        self.assertEqual(0, inst.id)

        with self.assertRaises(TypeError):
            shell._find_fact(None)

        with self.assertRaises(ValueError):
            shell._find_fact('test')

        with self.assertRaises(NotFoundError):
            shell._find_fact(50)

        inst = shell._find_fact(0)
        self.assertEqual(0, inst.id)

        with wrapOut() as (out, err):
            shell.do_object(None)
            self.assertEqual(out.getvalue(), "Object id required\n")

        with mock.patch.object(ObjectCmd,
                               'cmdloop',
                               return_value=None) as mock_method:
            ret = shell.do_object(0)
            mock_method.assert_called_once_with()
            self.assertFalse(ret)

    def testBaseCmdFact(self):
        shell = ShellCmd(self.gm)
        with self.assertRaises(TypeError):
            shell._find_fact(None)

        with self.assertRaises(ValueError):
            shell._find_fact('test')

        with self.assertRaises(NotFoundError):
            shell._find_fact(10)

        inst = shell._find_fact(0)
        self.assertEqual(0, inst.id)

        with self.assertRaises(TypeError):
            shell._find_fact(None)

        with self.assertRaises(ValueError):
            shell._find_fact('test')

        with self.assertRaises(NotFoundError):
            shell._find_fact(50)

        inst = shell._find_fact(0)
        self.assertEqual(0, inst.id)

        with wrapOut() as (out, err):
            shell.do_fact(None)
            self.assertEqual(out.getvalue(), "Fact id required\n")

        with mock.patch.object(FactCmd,
                               'cmdloop',
                               return_value=None) as mock_method:
            ret = shell.do_fact(0)
            mock_method.assert_called_once_with()
            self.assertFalse(ret)

    def testBaseCmdHyp(self):
        shell = ShellCmd(self.gm)
        with self.assertRaises(TypeError):
            shell._find_hyp(None)

        with self.assertRaises(ValueError):
            shell._find_hyp('test')

        with self.assertRaises(NotFoundError):
            shell._find_hyp(10)

        inst = shell._find_hyp(0)
        self.assertEqual(0, inst.id)

        with self.assertRaises(TypeError):
            shell._find_hyp(None)

        with self.assertRaises(ValueError):
            shell._find_hyp('test')

        with self.assertRaises(NotFoundError):
            shell._find_hyp(50)

        inst = shell._find_hyp(0)
        self.assertEqual(0, inst.id)

        with wrapOut() as (out, err):
            shell.do_hyp(None)
            self.assertEqual(out.getvalue(), "Hyp id required\n")

        with mock.patch.object(HypCmd,
                               'cmdloop',
                               return_value=None) as mock_method:
            ret = shell.do_hyp(0)
            mock_method.assert_called_once_with()
            self.assertFalse(ret)

    def testObjectCmd(self):
        obj0 = self.gm.objects[0]
        obj = ObjectCmd(self.gm, obj0)

        self.assertEqual(len(obj.depthList), 1)

        fact_rows = obj._find_items(self.gm.facts, obj.obj.childFacts)
        self.assertEqual(len(fact_rows), 5)

        hyp_rows = obj._find_items(self.gm.hyps, obj.obj.childHyps)
        self.assertEqual(len(hyp_rows), 1)

    def testFactHypCmd(self):
        fact0 = self.gm.facts.findById(0)
        fact = FactCmd(self.gm, fact0)

        self.assertEqual(fact._type, "fact")
        self.assertEqual(len(fact.depthList), 1)

        info = fact._find_info()
        self.assertIsInstance(info, collections.OrderedDict)


def testPrettyTable():
    tup = collections.namedtuple('test', ['a', 'b'])
    rows = []

    rows.append(tup("1", "2"))
    rows.append(tup("c", "d"))

    table = prettyTable(rows)
    assert table == 'a | b\n==+==\n1 | 2\nc | d'


def testPrettyList(capsys):
    data = {
        "test": ["a", "b", "c"],
        "test2": "d",
        "test3": "e",
    }

    table = prettyList(data, debug=True)
    assert table == 'test  \n      a\n      b\n      c\ntest2 = d\ntest3 = e\n'
    captured = capsys.readouterr()
    assert captured.out == '5\n'

    data = {}
    table = prettyList(data)
    assert table == "None"


def testListObjectsNoObjects():
    gm = mock.Mock()
    gm.objects = []
    x = listObjects(gm)
    assert x == "No objects found\n"


def testListHypsNoHyps():
    gm = mock.Mock()
    gm.hyps = {}
    x = listHyps(gm)
    assert x == "No hyps found\n"


def testCreateObjectsList():
    obj = mock.Mock()
    obj.id = 0
    obj._created_ = 1
    obj.metadata = {'filename': "test"}
    obj._creator_ = "tester"

    gm = mock.Mock()
    gm.objects = [obj]

    source = mock.Mock()
    source.Objects = [0]

    table = createObjectsList("", gm, source)
    assert table == 'id | creator |            created             | ' \
        'filename\n===+=========+================================+===' \
        '======\n0  | tester  | 1970-01-01 00:00:01.000000 UTC | test    '

    source2 = mock.Mock()
    source2.Objects = []
    table = createObjectsList("", gm, source2)
    assert table == "None\n"


def testCreateFactsList():
    fact = mock.Mock()
    fact.id = 0
    fact.created = 1
    fact.creator = "tester"

    gm = mock.Mock()
    gm.facts = {"fact": [fact]}

    source = mock.Mock()
    source.Facts = [0]
    table = createFactsList("", gm, source)
    assert table == 'id | type | creator |            created            \n=' \
        '==+======+=========+===============================\n0  | fact | ' \
        'tester  | 1970-01-01 00:00:01.000000 UTC'

    source2 = mock.Mock()
    source2.Facts = []
    table = createFactsList("", gm, source2)
    assert table == "None\n"


def testCreateHypsList():
    hyp = mock.Mock()
    hyp.id = 0
    hyp.created = 1
    hyp.creator = "tester"

    gm = mock.Mock()
    gm.hyps = {"hyp": [hyp]}

    source = mock.Mock()
    source.Hyps = [0]
    table = createHypsList("", gm, source)
    assert table == 'id | type | creator |            created            \n=' \
        '==+======+=========+===============================\n0  | hyp  | ' \
        'tester  | 1970-01-01 00:00:01.000000 UTC'

    source2 = mock.Mock()
    source2.Hyps = []
    table = createHypsList("", gm, source2)
    assert table == "None\n"


def testBaseCmdPreCmd():
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    line = cmd.precmd("test")
    assert line == "test"

    with pytest.raises(SystemExit):
        line = cmd.precmd('EOF')


def testBaseCmdDoSave(capsys, monkeypatch):
    gm = mock.Mock()
    gm.options = None
    cmd = BaseCmd(gm)

    cmd.do_save(None)
    captured = capsys.readouterr()
    assert captured.out == 'No save path was found\n'

    with monkeypatch.context() as m:
        gm.options = mock.Mock()
        gm.options.statefile = "testfile"
        cmd = BaseCmd(gm)
        mockTrue = mock.Mock(return_value=True)
        mockFalse = mock.Mock(return_value=False)

        m.setattr("os.path.exists", mockTrue)
        m.setattr("os.path.isfile", mockFalse)
        cmd.do_save(None)
        captured = capsys.readouterr()
        assert captured.out == 'testfile exists but is not a file\n'

        m.setattr("os.path.exists", mockTrue)
        m.setattr("os.path.isfile", mockTrue)
        m.setattr("d20.Manual.Shell.askPrompt", mockFalse)
        cmd.do_save(None)
        captured = capsys.readouterr()
        assert captured.out == 'State not saved\n'

        m.setattr("os.path.exists", mockFalse)
        m.setattr("os.path.isfile", mockFalse)
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        gm.options = mock.Mock()
        gm.options.statefile = "testfile"
        gm.save = mock.Mock(return_value={})
        cmd = BaseCmd(gm)
        cmd.do_save(tf.name)
        captured = capsys.readouterr()
        assert ("Saving to %s ... Saved\n" % tf.name) in captured.out
        os.remove(tf.name)


def testBaseCmdDoListNoArg(capsys):
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    cmd.do_list(None)
    captured = capsys.readouterr()
    assert captured.out == "list objects|facts|hyps\n"


def testBaseCmdDoBack(capsys):
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    cmd.do_back(None)
    captured = capsys.readouterr()
    assert captured.out == "Already at root\n"

    cmd.depthList.append('test')
    cmd.do_back(None)
    assert cmd.do_back(None)

    cmd.do_back('root')
    assert cmd.backTo

    cmd.do_back('123')
    assert cmd.backTo == 123

    cmd.depthList = ["raiseError"]
    assert not cmd.do_back('test')
    captured = capsys.readouterr()
    assert captured.out == "Unexpected value to back\n"


def testBaseCmdParseBcFact():
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    fact1 = mock.Mock(spec=Fact)
    fact1.tainted = False
    fact1.id = 0
    fact2 = mock.Mock(spec=Fact)
    fact2.tainted = True
    fact2.id = 1

    cmd.depthList.extend([fact1, fact2])

    bc = cmd._parse_bc()
    assert bc == [(0, 'fact', 0), (1, 'hyp', 1)]

    cmd.depthList = ["RaiseError"]
    with pytest.raises(RuntimeError) as excinfo:
        cmd._parse_bc()
    assert str(excinfo.value) == "Unknown type"


def testBaseCmdDoBc(capsys):
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    fact1 = mock.Mock(spec=Fact)
    fact1.tainted = False
    fact1.id = 0

    cmd.depthList.append(fact1)

    cmd.do_bc(None)
    captured = capsys.readouterr()
    assert captured.out == "%d - %s %d\n" % (0, 'fact', 0)


def testBaseCmdCheckBackTo():
    gm = mock.Mock()
    cmd = BaseCmd(gm)

    assert cmd.checkBackTo(True)
    assert cmd.backTo

    assert cmd.checkBackTo(1)
    assert cmd.backTo == 1

    cmd.depthList = [1, 2, 3]
    assert not cmd.checkBackTo(2)

    assert not cmd.checkBackTo(False)


def testBaseCmdDoObjectError(capsys):
    obj = mock.Mock()
    obj.id = 0
    gm = mock.Mock()
    gm.objects = [obj]
    cmd = BaseCmd(gm)

    assert not cmd.do_object([0])
    captured = capsys.readouterr()
    assert captured.out == "Object id must be an integer value"

    assert not cmd.do_object('1.0')
    captured = capsys.readouterr()
    assert captured.out == "Object id must be an integer value"

    assert not cmd.do_object('1')
    captured = capsys.readouterr()
    assert captured.out == "No object by that id\n"


def testBaseCmdDoFactError(capsys):
    fact = mock.Mock()
    fact.id = 0
    gm = mock.Mock()
    gm.facts = {'fact': [fact]}
    cmd = BaseCmd(gm)

    assert not cmd.do_fact([0])
    captured = capsys.readouterr()
    assert captured.out == "Fact id must be integer value\n"

    assert not cmd.do_fact('1.0')
    captured = capsys.readouterr()
    assert captured.out == "Fact id must be integer value\n"

    assert not cmd.do_fact('1')
    captured = capsys.readouterr()
    assert captured.out == "No fact by that id\n"


def testBaseCmdDoHypError(capsys):
    hyp = mock.Mock()
    hyp.id = 0
    gm = mock.Mock()
    gm.hyps = {'hyp': [hyp]}
    cmd = BaseCmd(gm)

    assert not cmd.do_hyp([0])
    captured = capsys.readouterr()
    assert captured.out == "Hyp id must be integer value"

    assert not cmd.do_hyp('1.0')
    captured = capsys.readouterr()
    assert captured.out == "Hyp id must be integer value"

    assert not cmd.do_hyp('1')
    captured = capsys.readouterr()
    assert captured.out == "No hyp by that id\n"


def testObjectCmdDoInfo(capsys):
    gm = mock.Mock()
    obj = mock.Mock()
    obj._created_ = 1
    obj.id = 0
    obj._creator_ = "test"
    cmd = ObjectCmd(gm, obj)
    cmd.do_info(None)
    captured = capsys.readouterr()
    assert captured.out == "\nObject 0:\n--------------\nid      = 0\n" \
        "creator = test\ncreated = 1970-01-01 00:00:01.000000 UTC\n---------" \
        "-----\n\n"


def testObjectCmdDoItems(monkeypatch, capsys):
    data = mock.Mock()
    children = mock.Mock()
    gm = mock.Mock()
    obj = mock.Mock()
    obj._created_ = 1
    obj.id = 0
    obj._creator_ = "test"
    cmd = ObjectCmd(gm, obj)

    mock1 = mock.Mock(return_value=["foo"])
    monkeypatch.setattr("d20.Manual.Shell.ObjectCmd._find_items", mock1)
    mockTable = mock.Mock(return_value="testing")
    monkeypatch.setattr("d20.Manual.Shell.prettyTable", mockTable)
    cmd._do_items("test", data, children)
    captured = capsys.readouterr()
    assert captured.out == "\ntesting\n"

    mock1 = mock.Mock(return_value=[])
    monkeypatch.setattr("d20.Manual.Shell.ObjectCmd._find_items", mock1)
    cmd._do_items("test", data, children)
    captured = capsys.readouterr()
    assert captured.out == "No test associated with object\n"


def testFactHypBaseCmdWriteList(capsys):
    item = mock.Mock()
    item.id = 1
    gm = mock.Mock()
    cmd = FactHypBaseCmd("test", gm, item)

    cmd.write_list("testing")
    captured = capsys.readouterr()
    assert captured.out == "\nTest 1:\n--------------\ntesting" \
                           "--------------\n\n"


def testFactHypBaseCmdInitError(capsys):
    item = mock.Mock()
    item.id = None
    gm = mock.Mock()
    FactHypBaseCmd("test", gm, item)

    captured = capsys.readouterr()
    assert captured.out == "Something went wrong, Fact had no ID\n"


def testFactHypBaseCmdDoGet(capsys):
    gm = mock.Mock()
    item1 = mock.Mock()
    item1.id = 1
    item1._fields_ = None
    cmd = FactHypBaseCmd("test", gm, item1)
    cmd.do_get(None)
    captured = capsys.readouterr()
    assert captured.out == "No field by that name\n"

    item2 = mock.Mock()
    item2.id = 1
    item2._fields_ = []
    cmd = FactHypBaseCmd("test", gm, item2)
    cmd.do_get("test")
    captured = capsys.readouterr()
    assert captured.out == "No field by that name\n"

    item3 = mock.Mock()
    item3.id = 1
    item3._fields_ = ["test"]
    item3._test__ = "tester"
    cmd = FactHypBaseCmd("test", gm, item3)
    cmd.do_get("test")
    captured = capsys.readouterr()
    assert captured.out == "test field was unset/undefined\n"
