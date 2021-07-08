import unittest
from unittest import mock
import os
import collections
from argparse import Namespace
import yaml

from d20.Manual.Exceptions import NotFoundError
from d20.Manual.Config import Configuration
from d20.Manual.GameMaster import GameMaster
from d20.Manual.Shell import (tsTodt,
                              askPrompt,
                              listObjects,
                              listFacts,
                              listHyps,
                              ShellCmd,
                              ObjectCmd,
                              FactCmd,
                              HypCmd)
from d20.Manual.Facts import loadFacts
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
