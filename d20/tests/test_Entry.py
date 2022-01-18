import sys
import shlex
import unittest
from unittest import mock
from argparse import Namespace

from d20.version import GAME_ENGINE_VERSION
from d20.Manual.Entry import (main, play, shellmain,
                              __fix_default)
from d20.Manual.Config import Configuration
from d20.tests import wrapOut


test5mainTestOutput1 = """TestPlayer:
\tCreator: test
\tVersion: 0.1.1
\tGame Engine: 0.1.1
\tDescription: test description
\tFacts Consumed:
\t	MD5HashFact
\tFacts Generated:
\t	NoSuchFact

\tHelp:
\t	Some Help String
"""

test5mainTestOutput2 = """TestPlayer:
\tCreator: test
\tVersion: 0.1.1
\tGame Engine: 0.1.1
\tDescription: test test test test test test test test test test
\t             test test test test test
\tFacts Consumed:
\t	MD5HashFact
\tFacts Generated:
\t	NoSuchFact

\tHelp:
\t	test test test test test test test test test test test test
\t	test test test
"""

test1shellTestOutput1 = \
    "Reading state file, please wait ... \nLoading GM ...\n"


class TestEntryMain(unittest.TestCase):
    def _createArgs(self, arguments):
        args = ['d20']
        args.extend(shlex.split(arguments))
        sys.argv = args

    def test1main(self):
        self._createArgs("--version")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertEqual(
                out.getvalue(), "d20: Engine %s\n" % (GAME_ENGINE_VERSION))

        self._createArgs("")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertEqual(
                out.getvalue(), "File/BackStory Facts or Save State required\n"
            )

        self._createArgs("--list-players")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith("Registered Players:"))

        self._createArgs("--list-npcs")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith("Registered NPCs:"))

        self._createArgs("--list-backstories")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith(
                "Registered BackStories:"))

        self._createArgs("--list-screens")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith("Installed Screens:"))

    @mock.patch("d20.Manual.Entry.verifyPlayers", return_value=list())
    def test2main(self, vp):
        self._createArgs("--list-players")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith(
                "Registered Players:\n\tNo Players"))

    @mock.patch("d20.Manual.Entry.verifyNPCs", return_value=list())
    def test3main(self, vn):
        self._createArgs("--list-npcs")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith(
                "Registered NPCs:\n\tNo NPCs"))

    @mock.patch("d20.Manual.Entry.verifyScreens", return_value=list())
    def test4main(self, vs):
        self._createArgs("--list-screens")
        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertTrue(out.getvalue().startswith(
                "Installed Screens:\n\tNo Screens"))

    @mock.patch("d20.Manual.Entry.verifyPlayers")
    def test5main(self, vp):
        self._createArgs("--info-player TestPlayer")
        vp.return_value = [Namespace(
            name="TestPlayer",
            registration=Namespace(
                name="TestPlayer",
                creator="test",
                version="0.1.1",
                engine_version="0.1.1",
                description="test description",
                facts_consumed=["MD5HashFact"],
                facts_generated=["NoSuchFact"],
                help="Some Help String"))]

        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertMultiLineEqual(
                out.getvalue(), test5mainTestOutput1
            )

        vp.return_value = [Namespace(
            name="TestPlayer",
            registration=Namespace(
                name="TestPlayer",
                creator="test",
                version="0.1.1",
                engine_version="0.1.1",
                description="test " * 15,
                facts_consumed=["MD5HashFact"],
                facts_generated=["NoSuchFact"],
                help="test " * 15))]

        with wrapOut() as (out, err):
            with self.assertRaises(SystemExit):
                main()
            self.assertMultiLineEqual(
                out.getvalue(), test5mainTestOutput2
            )


class TestEntryPlay(unittest.TestCase):
    @mock.patch("d20.Manual.Entry.GameMaster")
    def test1play(self, fakeGM):
        with self.assertRaises(TypeError):
            play(file={'should': 'error'})

        with self.assertRaises(TypeError):
            play(extra_players=1)

        with self.assertRaises(TypeError):
            play(disable_async=0)

        with self.assertRaises(ValueError):
            play(nosuchoption=True)

    @mock.patch("d20.Manual.Entry.GameMaster")
    @mock.patch("d20.Manual.Entry.yaml")
    def test2play(self, yaml, fakeGM):
        yaml.load = mock.MagicMock()
        with mock.patch(
                "d20.Manual.Entry.open",
                mock.mock_open(read_data="foo")) as mock_file:
            play(load_file='foobar.save')
            mock_file.assert_called_with("foobar.save", 'r')

            play(load_file="foobar.save", _config=Configuration())

    @mock.patch("d20.Manual.Entry.GameMaster", side_effect=Exception())
    @mock.patch("d20.Manual.Entry.yaml")
    def test3play(self, yaml, fakeGM):
        yaml.load = mock.MagicMock()
        with mock.patch(
                "d20.Manual.Entry.open",
                mock.mock_open(read_data="foo")):
            with self.assertRaises(RuntimeError):
                play(load_file="foobar.save")

            fakeGM.side_effect = None
            fakeGM().startGame = mock.MagicMock(side_effect=Exception())
            with self.assertRaises(RuntimeError):
                play(load_file="foobar.save")

            fakeGM().startGame = mock.MagicMock()
            with mock.patch("d20.Manual.Entry.time.sleep") as mock_sleep:
                mock_sleep.side_effect = KeyboardInterrupt()
                type(fakeGM()).gameRunning = mock.PropertyMock(
                    return_value=True)
                play(load_file="foobar.save", disable_async=True)
                fakeGM().stop.assert_called_with()

                mock_sleep.side_effect = None
                type(fakeGM()).gameRunning = mock.PropertyMock(
                    return_value=False)
                play(load_file="foobar.save", disable_async=True)
                fakeGM().join.assert_called_with()

    @mock.patch("d20.Manual.Entry.GameMaster")
    @mock.patch("d20.Manual.Entry.yaml")
    @mock.patch("d20.Manual.Entry.os.makedirs")
    def test4play(self, os_makedirs, yaml, fakeGM):
        yaml.load = mock.MagicMock()
        with mock.patch(
                "d20.Manual.Entry.open",
                mock.mock_open(read_data="foo")) as mock_file:

            type(fakeGM()).objects = mock.PropertyMock(
                return_value=[
                    Namespace(
                        metadata={'filename': 'foobar'},
                        _creator_="TestCreator",
                        id=0,
                        hash="HASH",
                        data='foo')])

            play(
                load_file="foobar.save",
                printable=True,
                use_screen="json",
                save_file="d20.test.save",
                dump_objects="/tmp/out/objects")
            fakeGM().provideData.assert_called_with("json", printable=True)
            fakeGM().save.assert_called_with()
            mock_file.assert_has_calls([
                mock.call("d20.test.save", 'w'),
                mock.call("/tmp/out/objects/0-TestCreator-HASH-foobar", "wb")
            ], any_order=True)
            mock_file().write.assert_called_with("foo")


class TestEntryShell(unittest.TestCase):
    def _createArgs(self, arguments):
        args = ['d20']
        args.extend(shlex.split(arguments))
        sys.argv = args

    @mock.patch("d20.Manual.Entry.GameMaster")
    @mock.patch("d20.Manual.Entry.yaml")
    @mock.patch("d20.Manual.Entry.ShellCmd")
    def test1shell(self, shellcmd, yaml, fakeGM):
        yaml.load = mock.MagicMock()
        with mock.patch(
                "d20.Manual.Entry.open",
                mock.mock_open(read_data="foo")) as mock_file:

            self._createArgs("foobar.save")

            fakeGM.side_effect = Exception()
            with wrapOut() as (out, err):
                with self.assertRaises(SystemExit):
                    shellmain()

            fakeGM.side_effect = None
            with wrapOut() as (out, err):
                shellmain()
                self.assertMultiLineEqual(
                    out.getvalue(), test1shellTestOutput1)
            mock_file.assert_called_with("foobar.save", 'r')


def testFixDefault():
    assert __fix_default(False) == "false"
    assert __fix_default(True) == "true"
    assert __fix_default(b"test") == "test"
    assert __fix_default(1) == "1"
