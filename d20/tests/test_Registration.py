import unittest
from unittest import mock

from d20.Manual.Config import Configuration
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  BackStoryTemplate,
                                  registerPlayer,
                                  registerNPC,
                                  registerBackStory)
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.Manual.Facts import loadFacts
from d20.BackStories import verifyBackStories

loadFacts()


class TestNPCRegistration(unittest.TestCase):
    def test1registerNPC(self):
        @registerNPC(
            name="RegTestNPC1",
            description="Tracker Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1"
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    def test2missingfieldNPC(self):
        with self.assertRaises(AttributeError):
            @registerNPC(
                name="RegTestNPC2",
                description="Tracker Test NPC",
                creator="",
                engine_version="0.1"
            )
            class RegTestNPC(NPCTemplate):
                def __init__(self, **kwargs):
                    super().__init__(**kwargs)

                def handleData(self, **kwargs):
                    pass

    def test3registerverification(self):
        npcs = verifyNPCs([], Configuration())
        self.assertIsInstance(npcs, list)
        self.assertGreater(len(npcs), 0)

    @mock.patch('d20.NPCS.LOGGER')
    def test4duplicateNPC(self, NPCLogger):
        NPCLogger.warning = mock.Mock()

        @registerNPC(
            name="RegTestNPC3",
            description="Tracker Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1"
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

        @registerNPC(  # noqa: F811
            name="RegTestNPC4",
            description="Tracker Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1"
        )
        class RegTestNPC(NPCTemplate):  # noqa: F811
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

        NPCLogger.warning.assert_called_with(
            'NPC with class name TestNPCRegistration.test4duplicateNPC.'
            '<locals>.RegTestNPC already registered')

    @mock.patch('d20.NPCS.LOGGER')
    def test5duplicateNPCName(self, NPCLogger):
        NPCLogger.warning = mock.Mock()

        @registerNPC(
            name="RegTestNPC5",
            description="Tracker Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1"
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

        @registerNPC(
            name="RegTestNPC5",
            description="Tracker Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1"
        )
        class RegTestNPC2(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

        NPCLogger.warning.assert_called_with(
            'NPC with name RegTestNPC5 already registered')


class TestPlayerRegistration(unittest.TestCase):
    def test1registerPlayer(self):
        @registerPlayer(
            name="RegTestPlayer1",
            description="Tracker Test Player",
            creator="",
            version="0.1",
            engine_version="0.1",
            interests=['mimetype'])
        class RegTestPlayer(PlayerTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleFact(self, **kwargs):
                pass

            def handleHypothesis(self, **kwargs):
                pass

    def test2registerverification(self):
        # Above test should register a player
        players = verifyPlayers([], Configuration())
        self.assertIsInstance(players, list)
        self.assertGreater(len(players), 0)
        self.assertIn(
            "RegTestPlayer1",
            [player.registration.name for player in players],)


class TestBackStoryRegistration(unittest.TestCase):
    def test1registerBackStory(self):
        @registerBackStory(
            name="RegTestBackStory1",
            description="TestBackStory",
            creator="",
            version="0.1",
            engine_version="0.1",
            category="downloader")
        class RegTestBackStory1(BackStoryTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleFact(self, **kwargs):
                pass

    def test2registerverification(self):
        # Above test should register a backstory
        backstories = verifyBackStories([], Configuration())
        self.assertIsInstance(backstories, list)
        self.assertGreater(len(backstories), 0)
        self.assertIn(
            "RegTestBackStory1",
            [backstory.registration.name for backstory in backstories],)
