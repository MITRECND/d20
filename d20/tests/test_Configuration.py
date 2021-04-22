import unittest
from unittest import mock
import yaml
import copy
import argparse

from d20.Manual.Config import (Configuration, EntityConfiguration)
from d20.tests import wrapOut

sampleConfig1String = """---
Screens:
    json:
        exclude_objects: true
        convert_bytes: true
        option1: value
        option2: value
Players:
    TestPlayer:
        option1: test player option string
NPCS:
    TestNPC:
        option1: test npc option string
BackStories:
    TestBackStory:
        option1: test backstory option
Actions:
    TestAction:
        option1: blah
        user: blah
common:
    http_proxy: "http://localhost:80"
d20:
   extra-players:
       - /opt/d20_extras/Players
   extra-facts:
       - /opt/d20_extras/Facts
   extra-npcs:
       - /opt/d20_extras/NPCs
   temporary: "/tmp/path"
   graceTime: 5

"""

sampleConfig2String = """---
Players:
    TestPlayer:
"""

sampleConfig1 = yaml.safe_load(sampleConfig1String)
sampleConfig2 = yaml.safe_load(sampleConfig2String)


class TestConfiguration(unittest.TestCase):
    def test_empty_config(self):
        Configuration()

    def test_sample_config(self):
        Configuration(config=copy.deepcopy(sampleConfig1))

    def test_wrong_type(self):
        with self.assertRaises(TypeError):
            Configuration(config=[])

    def test_missing_data(self):
        with self.assertRaises(TypeError):
            Configuration(config=copy.deepcopy(sampleConfig2))

    def test_arg_injection(self):
        args = argparse.Namespace()
        Configuration(config=copy.deepcopy(sampleConfig1),
                      args=args)
        self.assertIn('extra_players', args)
        self.assertIsInstance(args.extra_players, list)
        self.assertEqual(args.extra_players, ['/opt/d20_extras/Players'])

    def test_configfile_not_found(self):
        with wrapOut() as (out, err):
            with self.assertRaises(FileNotFoundError):
                Configuration(configFile='/tmp/nosuchfile')

    def test_read_config_failure(self):
        with wrapOut() as (out, err):
            with mock.patch("builtins.open", mock.mock_open()) as mock_open:
                mock_open.side_effect = Exception()
                with self.assertRaises(Exception):
                    Configuration(configFile='/tmp/foo')

    def test_read_config(self):
        with mock.patch(
                "builtins.open",
                mock.mock_open(read_data=sampleConfig1String)) as mock_open:
            Configuration(configFile='/tmp/foo')
            mock_open.assert_called_with('/tmp/foo', 'r')

    def test_read_config_yaml_failure(self):
        with wrapOut() as (out, err):
            with mock.patch(
                    "builtins.open",
                    mock.mock_open(read_data="foo\t\tfoo")):
                with self.assertRaises(Exception):
                    Configuration(configFile='/tmp/foo')


class TestConfigurations(unittest.TestCase):
    def setUp(self):
        try:
            self.config0 = Configuration()
            self.config1 = Configuration(config=copy.deepcopy(sampleConfig1))
        except Exception:
            raise

    def test_default_dicts(self):
        self.assertIsInstance(self.config0.players, dict)
        self.assertIsInstance(self.config0.npcs, dict)
        self.assertIsInstance(self.config0.screens, dict)
        self.assertIsInstance(self.config0.actions, dict)
        self.assertIsInstance(self.config0.d20, dict)
        self.assertIsInstance(self.config0.common, dict)

    def test_player_config(self):
        tpconfig = self.config1.playerConfig('TestPlayer')
        self.assertIsInstance(tpconfig, EntityConfiguration)
        self.assertIn("option1", tpconfig.options.keys())

    def test_player_default_config(self):
        tpconfig = self.config1.playerConfig('NoPlayer')
        self.assertIsInstance(tpconfig, EntityConfiguration)

    def test_npc_config(self):
        tnconfig = self.config1.npcConfig('TestNPC')
        self.assertIsInstance(tnconfig, EntityConfiguration)
        self.assertIn("option1", tnconfig.options.keys())

    def test_npc_default_config(self):
        tnconfig = self.config1.npcConfig('NoNPC')
        self.assertIsInstance(tnconfig, EntityConfiguration)

    def test_screens_config(self):
        tsconfig = self.config1.screenConfig('json')
        self.assertIsInstance(tsconfig, EntityConfiguration)
        self.assertIn("option1", tsconfig.options.keys())

    def test_screens_default_config(self):
        tsconfig = self.config1.playerConfig('NoScreen')
        self.assertIsInstance(tsconfig, EntityConfiguration)

    def test_backstory_config(self):
        tbconfig = self.config1.backStoryConfig('TestBackStory')
        self.assertIsInstance(tbconfig, EntityConfiguration)
        self.assertIn("option1", tbconfig.options.keys())

    def test_backstory_default_config(self):
        tbconfig = self.config1.backStoryConfig('NoBackStory')
        self.assertIsInstance(tbconfig, EntityConfiguration)

    def test_action_config(self):
        taconfig = self.config1.actionConfig('TestAction')
        self.assertIsInstance(taconfig, EntityConfiguration)
        self.assertIn("option1", taconfig.options.keys())

    def test_action_default_config(self):
        taconfig = self.config1.actionConfig('NoAction')
        self.assertIsInstance(taconfig, EntityConfiguration)


if __name__ == "__main__":
    unittest.main()


__all__ = ['TestConfiguration',
           'TestConfigurations']
