import unittest
from unittest import mock
import pytest
from packaging import version

from d20.Manual.Config import Configuration
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  BackStoryTemplate, ScreenTemplate,
                                  registerPlayer,
                                  registerNPC,
                                  registerScreen,
                                  registerBackStory)
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.Manual.Facts import loadFacts
from d20.BackStories import verifyBackStories
from d20.Manual.Registration import _test_version_string

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


def testRegistrationFormWrongOption():
    with pytest.raises(TypeError) as excinfo:
        @registerNPC(
            name="Tester1",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            options="abc",
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "'options must be of type 'Arguments'"


def testRegistrationFormWrongInterest():
    with pytest.raises(ValueError) as excinfo:
        @registerNPC(
            name="Tester2",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            interests={'test': 'test'}
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "Unexpected keys in interests dict"

    with pytest.raises(TypeError) as excinfo:
        @registerNPC(
            name="Tester2b",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            interests=1
        )
        class RegTestNPC2(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "Expected an interable type"


def testRegistrationFormHelp():
    @registerNPC(
        name="Tester3",
        description="Test NPC",
        creator="",
        version="0.1",
        engine_version="0.1",
        help="help"
    )
    class RegTestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    npcs = verifyNPCs([], Configuration())
    assert "help" in [npc.registration.help for npc in npcs]


def testRegistrationFormFactsConsumed(monkeypatch):
    with pytest.raises(TypeError) as excinfo:
        @registerNPC(
            name="Tester4",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            facts_consumed=1
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "facts_consumed must be list-like type"

    mock_true = mock.Mock(return_value=True)
    monkeypatch.setattr('d20.Manual.Registration.isFactGroup', mock_true)

    @registerNPC(
        name="Tester4B",
        description="Test NPC",
        creator="",
        version="0.1",
        engine_version="0.1",
        facts_consumed=['Test']
    )
    class RegTestNPC2(NPCTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    npcs = verifyNPCs([], Configuration())
    for npc in npcs:
        if "Tester4B" in npc.name:
            assert "Test (Group)" in npc.registration.facts_consumed


def testRegistrationFormFactsGenerated(monkeypatch):
    with pytest.raises(TypeError) as excinfo:
        @registerNPC(
            name="Tester5",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            facts_generated=1
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "facts_generated must be list-like type"

    mock_true = mock.Mock(return_value=True)
    monkeypatch.setattr('d20.Manual.Registration.isFactGroup', mock_true)

    @registerNPC(
        name="Tester5B",
        description="Test NPC",
        creator="",
        version="0.1",
        engine_version="0.1",
        facts_generated=['Test']
    )
    class RegTestNPC2(NPCTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    npcs = verifyNPCs([], Configuration())
    for npc in npcs:
        if "Tester5B" in npc.name:
            assert "Test (Group)" in npc.registration.facts_generated


def testRegistrationFormWrongArgument():
    with pytest.raises(TypeError) as excinfo:
        @registerNPC(
            name="Tester6",
            description="Test NPC",
            creator="",
            version="0.1",
            engine_version="0.1",
            test="test"
        )
        class RegTestNPC(NPCTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "test is an invalid keyword argument"


def testRegistrationFormRightInterest():
    @registerNPC(
        name="Tester7",
        description="Test NPC",
        creator="",
        version="0.1",
        engine_version="0.1",
        interests={'facts': ['ssdeep'], 'hyps': ['ssdeep']}
    )
    class RegTestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    targetdict = {'facts': {'ssdeep'}, 'hyps': {'ssdeep'}}
    npcs = verifyNPCs([], Configuration())
    for npc in npcs:
        if "Tester7" in npc.name:
            assert targetdict == npc.registration.interests


@pytest.mark.parametrize("input", [1, version.LegacyVersion("1.0")])
def testVersionStringException(input):
    with pytest.raises(ValueError) as excinfo:
        _test_version_string(input)

    assert str(excinfo.value) == "Unable to parse version information" or \
        str(excinfo.value) == "Unparseable version specified"


def testRegistrationFormSave():
    @registerNPC(
        name="Tester8",
        description="Test NPC",
        creator="",
        version="0.1",
        engine_version="0.1"
    )
    class RegTestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    test = {'name': "Tester8",
            'description': "Test NPC",
            'creator': "",
            'version': "0.1",
            'engine_version': "0.1",
            'interests': {'facts': set(), 'hyps': set()},
            'help': None}

    npcs = verifyNPCs([], Configuration())
    for npc in npcs:
        if "Tester8" in npc.name:
            save_dict = npc.registration.save()
            assert test == save_dict


def testScreenRegistrationFormWrongOption():
    with pytest.raises(TypeError) as excinfo:
        @registerScreen(
            name="ScreenTester1",
            version="0.1",
            engine_version="0.1",
            options="abc",
        )
        class RegTestScreen(ScreenTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def present(self):
                pass

            def filter(self):
                pass

            def formatData(self, data):
                pass

    assert str(excinfo.value) == "'options must be of type 'Arguments'"


def testScreenRegistrationFormWrongArgument():
    with pytest.raises(TypeError) as excinfo:
        @registerScreen(
            name="ScreenTester2",
            version="0.1",
            engine_version="0.1",
            test="test",
        )
        class RegTestScreen(ScreenTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def present(self):
                pass

            def filter(self):
                pass

            def formatData(self, data):
                pass

    assert str(excinfo.value) == "test is an invalid keyword argument"


def testBackStoryRegistrationFormWrongOption():
    with pytest.raises(TypeError) as excinfo:
        @registerBackStory(
            name="BackStoryTester1",
            description="Test BackStory",
            creator="",
            version="0.1",
            engine_version="0.1",
            category="test",
            options="abc",
        )
        class RegTestBackStory(BackStoryTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "'options must be of type 'Arguments'"


def testBackStoryRegistrationFormWrongArgument():
    with pytest.raises(TypeError) as excinfo:
        @registerBackStory(
            name="BackStoryTester2",
            description="Test BackStory",
            creator="",
            version="0.1",
            engine_version="0.1",
            category="test",
            test="test",
        )
        class RegTestBackStory(BackStoryTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "test is an invalid keyword argument"


def testBackStoryRegistrationFormNonIterableInterest():
    with pytest.raises(TypeError) as excinfo:
        @registerBackStory(
            name="BackStoryTester2",
            description="Test BackStory",
            creator="",
            version="0.1",
            engine_version="0.1",
            category="test",
            interests=1
        )
        class RegTestBackStory(BackStoryTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "Expected an interable type"


def testBackStoryRegistrationFormWrongDefaultWeight():
    with pytest.raises(TypeError) as excinfo:
        @registerBackStory(
            name="BackStoryTester3",
            description="Test BackStory",
            creator="",
            version="0.1",
            engine_version="0.1",
            category="test",
            default_weight="test"
        )
        class RegTestBackStory(BackStoryTemplate):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def handleData(self, **kwargs):
                pass

    assert str(excinfo.value) == "Expected an int type"


def testBackStoryRegistrationFormHelp():
    @registerBackStory(
        name="BackStoryTester4",
        description="Test BackStory",
        creator="",
        version="0.1",
        engine_version="0.1",
        category="test",
        help="help"
    )
    class RegTestBackStory(BackStoryTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    backstories = verifyBackStories([], Configuration())
    assert "help" in [backstory.registration.help for backstory in backstories]


def testBackStoryRegistrationFormSave():
    @registerBackStory(
        name="BackStoryTester5",
        description="Test BackStory",
        creator="",
        version="0.1",
        engine_version="0.1",
        category="test"
    )
    class RegTestBackStory(BackStoryTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleData(self, **kwargs):
            pass

    test = {'name': "BackStoryTester5",
            'description': "Test BackStory",
            'creator': "",
            'version': "0.1",
            'engine_version': "0.1",
            'interests': set(),
            'help': None}

    backstories = verifyBackStories([], Configuration())
    for backstory in backstories:
        if "BackStoryTester5" in backstory.name:
            save_dict = backstory.registration.save()
            assert test == save_dict
