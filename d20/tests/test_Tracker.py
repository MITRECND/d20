import unittest
from unittest import mock
import pytest
import time

from d20.Manual.Trackers import (BackStoryTracker, NPCTracker,
                                 PlayerTracker,
                                 CloneTracker,
                                 BackStoryCategoryTracker)
from d20.Manual.Console import PlayerState
from d20.Manual.Config import Configuration
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  registerPlayer,
                                  registerNPC)
from d20.BackStories import BackStory
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.Manual.Facts import loadFacts


loadFacts()


@registerPlayer(
    name="TrackerTestPlayer",
    description="Tracker Test Player",
    creator="",
    version="0.1",
    engine_version="0.1",
    interests=['mimetype'])
class TrackerTestPlayer(PlayerTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleFact(self, **kwargs):
        pass

    def handleHypothesis(self, **kwargs):
        pass


@registerNPC(
    name="TrackerTestNPC",
    description="Tracker Test NPC",
    creator="",
    version="0.1",
    engine_version="0.1"
)
class TrackerTestNPC(NPCTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleData(self, **kwargs):
        pass


@registerNPC(
    name="TrackerTestWrongTemplateNPC",
    description="Tracker Test Wrong Template NPC",
    creator="",
    version="0.1",
    engine_version="0.1"
)
class TrackerTestWrongTemplateNPC(PlayerTemplate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handleData(self, **kwargs):
        pass


class TestPlayerTracker(unittest.TestCase):
    def testTrackerCreation(self):
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        players = verifyPlayers([], Configuration())
        player = players[0]
        with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
            tracker = PlayerTracker(id=0,
                                    player=player,
                                    rpcServer=rpcServer,
                                    asyncData=asyncData)

            self.assertEqual(tracker.state, PlayerState.stopped)
            clone = tracker.createClone()
            self.assertIsInstance(clone, CloneTracker)
            saveData = tracker.save()
            PlayerTracker.load(
                saveData, player, rpcServer, asyncData)

    def testNPCTrackerCreation(self):
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        npcs = verifyNPCs([], Configuration())
        npc = npcs[0]
        with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
            tracker = NPCTracker(id=0,
                                 npc=npc,
                                 rpcServer=rpcServer,
                                 asyncData=asyncData)

            self.assertEqual(tracker.state, PlayerState.stopped)
            saveData = tracker.save()
            NPCTracker.load(saveData, npc, rpcServer, asyncData)


def testNPCTrackerMissingNPCConfig(caplog):
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    npcs = verifyNPCs([], Configuration())
    npc = npcs[0]
    npc.config = None
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        NPCTracker(id=0,
                   npc=npc,
                   rpcServer=rpcServer,
                   asyncData=asyncData)

    assert "TrackerTestNPC does not have configs" in caplog.text


def testNPCTrackerWrongTemplate(caplog):
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    npcs = verifyNPCs([], Configuration())
    npc = npcs[1]
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        NPCTracker(id=0,
                   npc=npc,
                   rpcServer=rpcServer,
                   asyncData=asyncData)
        assert "TrackerTestWrongTemplateNPC is not using the NPCTemplate!" \
            in caplog.text


def testNPCTrackerRuntime():
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    npcs = verifyNPCs([], Configuration())
    npc = npcs[0]
    npc.config = None
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        tracker = NPCTracker(id=0,
                             npc=npc,
                             rpcServer=rpcServer,
                             asyncData=asyncData)

        assert tracker.runtime == 0


def testNPCTrackerLoadNonNPC():
    with pytest.raises(TypeError) as excinfo:
        data = {}
        npc = 1
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        NPCTracker.load(data, npc, rpcServer, asyncData)

    assert str(excinfo.value) == "Expected an 'NPC' type"


def testBackStoryCategoryTrackerState():
    tracker = BackStoryCategoryTracker("test")
    assert tracker.state == PlayerState.stopped


def testBackStoryCategoryTrackerThread(caplog):
    fact = mock.Mock()
    backstoryTracker = mock.Mock()
    backstoryTracker.handleFact.side_effect = Exception("handleFact")
    tracker = BackStoryCategoryTracker("test")
    tracker.backstory_trackers.extend([backstoryTracker])
    tracker.factQueue.put(fact)
    time.sleep(1)
    tracker.stopped = True
    assert "Exception: handleFact" in caplog.text


def testBackStoryTrackerWrongkwarg():
    with pytest.raises(TypeError) as excinfo:
        backstory = mock.Mock()
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
            BackStoryTracker(id=0,
                             backstory=backstory,
                             rpcServer=rpcServer,
                             asyncData=asyncData,
                             test="test")
    assert str(excinfo.value) == "test is an invalid kwarg"


def testBackStoryTrackerWeight():
    backstory = mock.Mock()
    backstory.config.options = {'weight': 123}
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        bt = BackStoryTracker(id=0,
                              backstory=backstory,
                              rpcServer=rpcServer,
                              asyncData=asyncData)

        assert bt.weight == 123


def testBackStoryTrackerName():
    backstory = mock.Mock()
    backstory.name = "tester"
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        bt = BackStoryTracker(id=0,
                              backstory=backstory,
                              rpcServer=rpcServer,
                              asyncData=asyncData)

        assert bt.name == "tester"


def testBackStoryTrackerCreateBackStoryConfigError(caplog):
    backstory = mock.Mock()
    backstory.config = None
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        BackStoryTracker(id=0,
                         backstory=backstory,
                         rpcServer=rpcServer,
                         asyncData=asyncData)

    assert "does not have configs set" in caplog.text


def testBackStoryTrackerRuntime():
    backstory = mock.Mock()
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        bt = BackStoryTracker(id=0,
                              backstory=backstory,
                              rpcServer=rpcServer,
                              asyncData=asyncData)

        assert bt.runtime == 0

        bt.addRuntime(2)
        assert bt.runtime == 2


def testBackStoryTrackerSave():
    backstory = mock.Mock()
    backstory.name = "test"
    asyncData = mock.Mock()
    rpcServer = mock.Mock()

    save_dict = {'id': 0,
                 'name': "test",
                 'memory': {}}

    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        bt = BackStoryTracker(id=0,
                              backstory=backstory,
                              rpcServer=rpcServer,
                              asyncData=asyncData)

        assert bt.save() == save_dict


def testBackStoryTrackerLoadWrongArg():
    with pytest.raises(TypeError) as excinfo:
        data = mock.Mock()
        backstory = 1
        asyncData = mock.Mock()
        rpcServer = mock.Mock()
        BackStoryTracker.load(data, backstory, rpcServer, asyncData)
    assert str(excinfo.value) == "Expected an 'BackStory' type"


def testBackStoryTrackerLoad():
    data = {'id': 1,
            'memory': "test"}
    backstory = mock.Mock(spec=BackStory)
    backstory.name = "abc"
    backstory.registration = mock.Mock()
    backstory.registration.default_weight = 1
    backstory.config = None
    asyncData = mock.Mock()
    rpcServer = mock.Mock()

    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        bt = BackStoryTracker.load(data, backstory, rpcServer, asyncData)

        assert bt.id == 1
        assert bt.backstory == backstory
        assert bt.asyncData == asyncData
        assert bt.rpcServer == rpcServer
        assert bt.memory == "test"
        assert bt.weight == 1


def testPlayerTrackerState():
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    players = verifyPlayers([], Configuration())
    player = players[0]
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        tracker = PlayerTracker(id=0,
                                player=player,
                                rpcServer=rpcServer,
                                asyncData=asyncData)

        clone = mock.Mock()
        clone.state = PlayerState.waiting
        tracker.clones['1'] = clone
        assert tracker.state == PlayerState.waiting

        clone.state = PlayerState.running
        tracker.clones['2'] = clone
        assert tracker.state == PlayerState.running

        tracker.clones = {}
        clone.turnTime = 2
        tracker.clones['1'] = clone
        tracker.maxTurnTime = 1
        assert tracker.state == PlayerState.stopped
        assert tracker.ignoredClones[0] == '1'


def testPlayerTrackerStates():
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    players = verifyPlayers([], Configuration())
    player = players[0]
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        tracker = PlayerTracker(id=0,
                                player=player,
                                rpcServer=rpcServer,
                                asyncData=asyncData)

        clone = mock.Mock()
        clone.state = PlayerState.waiting
        tracker.clones['0'] = clone

        clone2 = mock.Mock()
        clone2.state = PlayerState.running
        tracker.clones['1'] = clone2

        clone3 = mock.Mock()
        clone3.state = PlayerState.stopped
        tracker.clones['2'] = clone3

        states = tracker.states
        assert PlayerState.waiting in states
        assert PlayerState.running in states
        assert PlayerState.stopped in states


def testPlayerTrackerRuntime():
    asyncData = mock.Mock()
    rpcServer = mock.Mock()
    players = verifyPlayers([], Configuration())
    player = players[0]
    with mock.patch('d20.Manual.Trackers.PlayerDirectoryHandler'):
        tracker = PlayerTracker(id=0,
                                player=player,
                                rpcServer=rpcServer,
                                asyncData=asyncData)
        assert tracker.runtime == 0


def testCloneTrackerNoArgs(caplog):
    with pytest.raises(KeyError):
        CloneTracker()
        assert "Unable to setup Clone Tracker" in caplog.text
