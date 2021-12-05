import unittest
from unittest import mock
import pytest
import queue

from d20.Manual.Trackers import (NPCTracker,
                                 PlayerTracker,
                                 CloneTracker,
                                 PlayerState, BackStoryCategoryTracker)

from d20.Manual.Config import Configuration
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  registerPlayer,
                                  registerNPC)
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


def testNPCTrackerRuntime(caplog):
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


def testBackStoryCategoryTrackerThread():
    fact = mock.Mock()
    fact2 = mock.Mock()
    fact2.return_value = Exception("break loop")
    backstoryTracker1 = mock.Mock()
    backstoryTracker1.handleFact.return_value = True
    backstoryTracker2 = mock.Mock()
    backstoryTracker2.handleFact.return_value = Exception("handleFact")
    queueGetMock = mock.Mock()
    queueGetMock.side_effect = [fact, Exception("break loop")]

    tracker = BackStoryCategoryTracker("test")
    tracker.factQueue.put(fact)
    tracker.factQueue.put(fact2)
    tracker.backstory_trackers.extend([backstoryTracker1, backstoryTracker2])

    with pytest.raises(Exception) as excinfo1:
        with pytest.raises(Exception) as excinfo2:
            # tracker = BackStoryCategoryTracker("test")
            # tracker.factQueue.put(fact)
            # tracker.backstory_trackers.extend([backstoryTracker1, backstoryTracker2])

        
            tracker.backStoryCategoryThread()

        assert str(excinfo2.value) == "handleFact"
    assert str(excinfo1.value) == "break loop"
