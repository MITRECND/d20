import time
import threading
import queue
from enum import Enum
from types import SimpleNamespace
from typing import List, Dict, Optional

from d20.Manual.Exceptions import PlayerCreationError
from d20.Manual.Logger import logging, Logger
from d20.Manual.Templates import (PlayerTemplate,
                                  NPCTemplate,
                                  BackStoryTemplate)
from d20.Manual.Console import (NPCConsole,
                                PlayerConsole,
                                BackStoryConsole,
                                PlayerState)
from d20.Manual.Temporary import PlayerDirectoryHandler
from d20.Players import Player
from d20.NPCS import NPC
from d20.BackStories import BackStory
from d20.Manual.RPC import EntityType, RPCClient, RPCServer
from d20.Manual.BattleMap import FileObject
from d20.Manual.Facts import Fact


LOGGER: Logger = logging.getLogger(__name__)


class NPCTracker(object):
    """NPCTracker

        This class tracks an individual NPC and provides a unified
        way of invoking its functionalty including setting up its console
        and related communication queues

        Args:
            id: The id of the npc
            npc: Instance of NPC class
            rpcServer: Instance of RPCServer
    """
    def __init__(self, *, id: int, npc: NPC, rpcServer: RPCServer,
                 asyncData: SimpleNamespace, **kwargs) -> None:
        # Process parameters
        self._state: PlayerState = PlayerState.stopped
        self.memory: Dict = dict()
        self._inst: NPCTemplate
        self._runtime: float = 0.0
        self.dataQueue: queue.Queue[FileObject] = queue.Queue()
        self.dHandler: PlayerDirectoryHandler = \
            PlayerDirectoryHandler(id, False)

        self.id: int = id
        self.npc: NPC = npc
        self.rpcServer: RPCServer = rpcServer
        self.asyncData: SimpleNamespace = asyncData

        for (name, value) in kwargs.items():
            if name == 'memory':
                self.memory = value
            else:
                raise TypeError("%s is an invalid kwarg" % (name))

        LOGGER.debug("Tracking NPC '%s' with id %d" % (self.npc.name, self.id))

        self.createNPC()
        self.npc_thread: threading.Thread = threading.Thread(
            name='npcTracker.%d' % (self.id),
            target=self.npcThread)
        self.npc_thread.daemon = True
        self.npc_thread.start()

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def name(self) -> str:
        return self.npc.name

    def npcThread(self) -> None:
        while 1:
            data: FileObject = self.dataQueue.get()
            try:
                start: float = time.time()
                self._state = PlayerState.running
                self._inst.handleData(data=data)
            except Exception:
                LOGGER.exception("Error running NPC %s" % (self.npc.name))
            finally:
                runtime: float = time.time() - start
                self._runtime += runtime
                LOGGER.debug("NPC '%s' took %f seconds"
                             % (self.npc.name, runtime))
                self._state = PlayerState.stopped

    def createNPC(self) -> None:
        # Set Options
        if not self.npc.config:
            LOGGER.error(("NPC {0} does not have configs set".format(
                self.npc.name)))
            return

        options: Dict = self.npc.registration.options.parse(
            self.npc.config.options,
            self.npc.config.common
        )

        # Generate GM Interface
        rpc_client = self.rpcServer.createClient(EntityType.npc, self.id)
        console = NPCConsole(id=self.id,
                             rpc_client=rpc_client,
                             asyncData=self.asyncData,
                             tracker=self,
                             directoryHandler=self.dHandler,
                             config=self.npc.config.common)
        try:
            _inst: NPCTemplate = self.npc.cls(console=console,
                                              options=options)
        except Exception as e:
            LOGGER.exception("Unable to create NPC %s ..." % (self.npc.name))
            raise PlayerCreationError(e) from None

        if not isinstance(_inst, NPCTemplate):
            LOGGER.error(("NPC {0} is not using the NPCTemplate! "
                          "{0} will be ignored!".format(self.npc.name)))
            return

        self._inst = _inst

    def handleData(self, data: FileObject) -> None:
        self.dataQueue.put(data)

    @property
    def runtime(self) -> float:
        return self._runtime

    def save(self) -> Dict:
        data: Dict = {'id': self.id,
                      'name': self.npc.name,
                      'memory': self.memory}
        return data

    @staticmethod
    def load(data: Dict, npc: NPC, rpcServer: RPCServer,
             asyncData) -> 'NPCTracker':
        if not isinstance(npc, NPC):
            raise TypeError("Expected an 'NPC' type")

        npc_track: NPCTracker = NPCTracker(**{'id': data['id'],
                                              'npc': npc,
                                              'rpcServer': rpcServer,
                                              'asyncData': asyncData,
                                              'memory': data['memory']})
        return npc_track


class BackStoryCategoryTracker:
    """This class tracks a category of BackStories, ensuring facts are passed
    to them in weighted order and if a BackStory returns 'True'
    short-circuits the execution chain
    """
    def __init__(self, category: str, **kwargs) -> None:
        self._state: PlayerState = PlayerState.stopped
        self.factQueue: queue.Queue = queue.Queue()
        self.category: str = category
        self.backstory_trackers: List['BackStoryTracker'] = list()

        self.stopped = False
        self.backstory_thread: threading.Thread = threading.Thread(
            name='backstoryTracker.%s' % (category),
            target=self.backStoryCategoryThread)
        self.backstory_thread.daemon = True
        self.backstory_thread.start()

    @property
    def state(self) -> PlayerState:
        return self._state

    def addBackStoryTracker(self,
                            backstory_tracker: 'BackStoryTracker') -> None:
        self.backstory_trackers.append(backstory_tracker)
        self.backstory_trackers = sorted(
            self.backstory_trackers, key=lambda i: i.weight)

    def backStoryCategoryThread(self) -> None:
        while not self.stopped:
            fact: Fact = self.factQueue.get()
            for backstory_tracker in self.backstory_trackers:
                try:
                    start: float = time.time()
                    self._state = PlayerState.running
                    result: bool = backstory_tracker.handleFact(fact=fact)
                    if result is True:
                        break
                except Exception:
                    LOGGER.exception(
                        "Error running BackStory %s"
                        % (backstory_tracker.name))
                finally:
                    runtime = time.time() - start
                    backstory_tracker.addRuntime(runtime)
                    LOGGER.debug("BackStory '%s' took %f seconds"
                                 % (backstory_tracker.name, runtime))
                    self._state = PlayerState.stopped

    def handleFact(self, fact: Fact) -> None:
        self.factQueue.put(fact)


class BackStoryTracker:
    """BackStoryTracker

        This class tracks an individual BackStory and provides a unified
        way of invoking its functionalty including setting up its console
        and related communication queues.

        Args:
            id: The id of the backstory
            backstory: Instance of BackStory class
            rpcServer: Instance of RPCServer
    """
    def __init__(self, *, id: int, backstory: BackStory, rpcServer: RPCServer,
                 asyncData, **kwargs) -> None:
        # Process parameters
        self.memory: Dict = dict()
        self._inst: BackStoryTemplate
        self._runtime: float = 0.0
        self.factQueue: queue.Queue = queue.Queue()
        self.dHandler: PlayerDirectoryHandler = \
            PlayerDirectoryHandler(id, False)
        self.__options: Optional[Dict] = None

        self.id: int = id
        self.backstory: BackStory = backstory
        self.rpcServer: RPCServer = rpcServer
        self.asyncData = asyncData

        for (name, value) in kwargs.items():
            if name == 'memory':
                self.memory = value
            else:
                raise TypeError("%s is an invalid kwarg" % (name))

        LOGGER.debug(
            "Tracking BackStory '%s' with id %d"
            % (self.backstory.name, self.id))

        self.weight = backstory.registration.default_weight
        if backstory.config is not None:
            config_weight = backstory.config.options.get('weight', None)
            if config_weight is not None:
                self.weight = config_weight

        self.createBackStory()

    @property
    def name(self) -> str:
        return self.backstory.name

    @property
    def options(self) -> Optional[Dict]:
        if self.__options is None and self.backstory.config is not None:
            self.__options = self.backstory.registration.options.parse(
                self.backstory.config.options,
                self.backstory.config.common
            )

        return self.__options

    def createBackStory(self) -> None:
        if not self.backstory.config:
            LOGGER.error(("Backstory {0} does not have configs set".format(
                self.backstory.name)))
            return

        # Generate GM Interface
        rpc_client: RPCClient = self.rpcServer.createClient(
            EntityType.backstory, self.id)
        console: BackStoryConsole = BackStoryConsole(
            id=self.id,
            rpc_client=rpc_client,
            asyncData=self.asyncData,
            tracker=self,
            directoryHandler=self.dHandler,
            config=self.backstory.config.common)

        try:
            _inst: BackStoryTemplate = self.backstory.cls(
                console=console, options=self.options)
        except Exception as e:
            LOGGER.exception(
                "Unable to create BackStory %s ..." % (self.backstory.name))
            raise PlayerCreationError(e) from None

        if not isinstance(_inst, BackStoryTemplate):
            LOGGER.error(("BackStory {0} is not using the BackStoryTemplate! "
                          "{0} will be ignored!".format(self.backstory.name)))
            return

        self._inst = _inst

    def handleFact(self, fact: Fact) -> bool:
        return self._inst.handleFact(fact=fact)  # type: ignore

    @property
    def runtime(self) -> float:
        return self._runtime

    def addRuntime(self, runtime: float) -> None:
        self._runtime += runtime

    def save(self) -> Dict:
        data: Dict = {'id': self.id,
                      'name': self.backstory.name,
                      'memory': self.memory}
        return data

    @staticmethod
    def load(data: Dict, backstory: BackStory, rpcServer: RPCServer,
             asyncData: SimpleNamespace) -> 'BackStoryTracker':
        if not isinstance(backstory, BackStory):
            raise TypeError("Expected an 'BackStory' type")

        backstory_track: BackStoryTracker = BackStoryTracker(**{
            'id': data['id'],
            'backstory': backstory,
            'rpcServer': rpcServer,
            'asyncData': asyncData,
            'memory': data['memory']})
        return backstory_track


class PlayerTracker(object):
    """PlayerTracker

        This class tracks an individual Player and provides a unified
        way of creating its clones which actually invoke its functionality

        Args:
            id: The id of the player
            player: Instance of Player class
            rpcServer: RPCServer instance
    """
    def __init__(self, *, id: int, player: Player, rpcServer: RPCServer,
                 asyncData: SimpleNamespace, **kwargs) -> None:
        # Process parameters
        self.count: int = 0
        self.dHandler: PlayerDirectoryHandler = PlayerDirectoryHandler(id,
                                                                       True)

        # Shared dictionary all clones have access to
        self.memory: Dict = dict()

        # Dictionaries for each clone, must be stored here due to init
        self.cloneMemory: Dict = dict()

        # Track what interested facts this player has received
        self.factTracker: Dict = dict()

        # Since clones can be deleted keep track of them in a dict
        # instead of a list
        self.clones: Dict = dict()

        self.maxTurnTime: int = 0
        self.ignoredClones: List[int] = []

        self._runtime: float = 0.0

        self.__options: Optional[Dict] = None

        self.id: int = id
        self.player: Player = player
        self.rpcServer: RPCServer = rpcServer
        self.asyncData: SimpleNamespace = asyncData

        for (name, value) in kwargs.items():
            if name == 'count':
                self.count = value
            elif name == 'memory':
                self.memory = value
            elif name == 'cloneMemory':
                self.cloneMemory = value
            elif name == 'factTracker':
                self.factTracker = value
            else:
                raise TypeError("%s is an invalid kwarg" % (name))

        LOGGER.debug("Tracking Player '%s' with id %d"
                     % (self.player.name, self.id))

    @property
    def options(self) -> Optional[Dict]:
        if self.__options is None and self.player.config is not None:
            self.__options = self.player.registration.options.parse(
                self.player.config.options,
                self.player.config.common
            )

        return self.__options

    @property
    def state(self) -> PlayerState:
        playerState: PlayerState = PlayerState.stopped
        for (clone_id, clone) in self.clones.items():
            if clone_id in self.ignoredClones:
                continue
            # Go through clones 'running' is a more important state
            # than 'waiting' so only break if a clone is 'running'
            if clone.state == PlayerState.running:
                if self.maxTurnTime > 0 and clone.turnTime > self.maxTurnTime:
                    LOGGER.warning(
                        "Player instance has reached maxTurnTime and "
                        "will be ignored")
                    self.ignoredClones.append(clone_id)
                    # Clone has taken the maximum amount of time allowed
                    # ignore it for further time calculations
                    pass
                else:
                    playerState = clone.state
                    break
            elif clone.state == PlayerState.waiting:
                playerState = clone.state

        return playerState

    @property
    def states(self) -> List[PlayerState]:
        playerStates: List[PlayerState] = [
            clone.state for(clone_id, clone) in self.clones.items()]

        return playerStates

    @property
    def name(self) -> str:
        return self.player.name

    @property
    def runtime(self) -> float:
        return self._runtime

    def _addRuntime(self, local_runtime: float) -> None:
        self._runtime += local_runtime

    def createClone(self, clone_id: Optional[int] = None,
                    tainted: bool = False) -> Optional['CloneTracker']:
        if not self.player.config:
            LOGGER.error(("Player {0} does not have configs set".format(
                self.player.name)))
            return None

        if clone_id is None:
            # Get clone id
            clone_id = self.count
            self.count += 1

        # Create Clone Memory aka 'data'
        self.cloneMemory[clone_id] = dict()

        # Generate an RPC client
        rpc_client: RPCClient = self.rpcServer.createClient(
            EntityType.player, self.id, clone_id)

        # Generate GM Interface
        console: PlayerConsole = \
            PlayerConsole(id=self.id,
                          clone_id=clone_id,
                          tracker=self,
                          rpc_client=rpc_client,
                          asyncData=self.asyncData,
                          directoryHandler=self.dHandler,
                          config=self.player.config.common,
                          tainted=tainted)
        try:
            clone_inst: PlayerTemplate = self.player.cls(console=console,
                                                         options=self.options)
        except Exception:
            LOGGER.exception("Unable to create player %s instance"
                             % (self.player.name))
            return None

        if not isinstance(clone_inst, PlayerTemplate):
            LOGGER.error(("Player {0} is not using the PlayerTemplate! "
                          "{0} will be ignored!".format(self.player.name)))
            return None

        clone: CloneTracker = CloneTracker(id=clone_id,
                                           inst=clone_inst,
                                           console=console,
                                           tracker=self)

        self.clones[clone_id] = clone

        return clone

    def checkIfHandledFact(self, fact: Fact) -> bool:
        if fact._type not in self.factTracker:
            return False

        if fact.id not in self.factTracker[fact._type]:
            return False

        return True

    def handleFact(self, fact: Fact) -> None:
        if fact._type not in self.factTracker:
            self.factTracker[fact._type] = set()
        self.factTracker[fact._type].add(fact.id)
        clone: Optional[CloneTracker] = self.createClone()
        if clone is None:
            raise PlayerCreationError("Unable to create clone")
        clone.handleFact(fact=fact)

    def handleHypothesis(self, hyp: Fact):
        clone = self.createClone(tainted=True)
        if clone is None:
            raise PlayerCreationError("Unable to create clone")
        clone.handleHypothesis(hyp)

    def save(self) -> Dict:
        data = {'id': self.id,
                'name': self.player.name,
                'memory': self.memory,
                'cloneMemory': self.cloneMemory,
                'factTracker': self.factTracker,
                'count': self.count}

        clone_data: Dict = dict()
        for (id, clone) in self.clones.items():
            clone_data[id] = clone.save()
        data['clones'] = clone_data

        return data

    @staticmethod
    def load(data: Dict, player: Player, rpcServer: RPCServer,
             asyncData) -> 'PlayerTracker':
        if not isinstance(player, Player):
            raise TypeError("Expected 'Player' instance")

        player_track: PlayerTracker = \
            PlayerTracker(**{'id': data['id'],
                             'player': player,
                             'rpcServer': rpcServer,
                             'asyncData': asyncData,
                             'memory': data['memory'],
                             'cloneMemory': data['cloneMemory'],
                             'count': data['count'],
                             'factTracker': data['factTracker']})

        for (id, clone_data) in data['clones'].items():
            clone: Optional[CloneTracker] = player_track.createClone(id)
            if clone is not None:
                clone.load(clone_data)
        return player_track


class CloneTracker(object):
    """CloneTracker

        This class tracks an individual Clone and provides a unified
        way of invoking its functionalty including setting up its console
        and related communication queues

        Args:
            clone_id: The id of the clone
            clone_inst: The instance of the player class
            tracker: The player tracker that created this clone
    """
    def __init__(self, **kwargs):
        try:
            self.inst: PlayerTemplate = kwargs['inst']
            self.id: int = kwargs['id']
            self.tracker: PlayerTracker = kwargs['tracker']
            self.console: PlayerConsole = kwargs['console']
        except KeyError:
            LOGGER.exception("Unable to setup Clone Tracker")
            raise

        self.myThread: Optional[threading.Thread] = None
        self._state: PlayerState = PlayerState.stopped
        self._turnStart: float = 0
        self.factID: Optional[int] = None
        self.factType: Optional[str] = None

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def turnTime(self) -> float:
        if self._turnStart == 0:
            return 0

        return time.time() - self._turnStart

    def handlerThread(self, target, **kwargs) -> None:
        start = time.time()
        self._state = PlayerState.running
        self._turnStart = start
        try:
            target(**kwargs)
        except Exception:
            LOGGER.exception("Error running player handler")
        finally:
            self._state = PlayerState.stopped

        runtime: float = time.time() - start
        self.tracker._addRuntime(runtime)
        LOGGER.debug("Player '%s', Clone %d took %f seconds"
                     % (self.tracker.name,
                        self.id, runtime))
        self.tracker.rpcServer.destroyClient(self.console._rpc.id)

    def handleFact(self, fact: Fact) -> None:
        self.factID = fact.id
        self.factType = fact._type
        self.myThread = threading.Thread(
            name='cloneTracker.%d.%d' % (self.tracker.id, self.id),
            target=self.handlerThread,
            args=(self.inst.handleFact,),
            kwargs={"fact": fact})
        self.myThread.daemon = True
        self.myThread.start()

    def handleHypothesis(self, hyp: Fact) -> None:
        self.factID = hyp.id
        self.factType = hyp._type
        self.myThread = threading.Thread(
            name='cloneTracker.%d.%d' % (self.tracker.id, self.id),
            target=self.handlerThread,
            args=(self.inst.handleHypothesis,),
            kwargs={"hypothesis": hyp})
        self.myThread.daemon = True
        self.myThread.start()

    def save(self) -> Dict:
        if isinstance(self._state, Enum):
            state = self._state.value
        else:
            state = self._state
        data: Dict = {'state': state,
                      'factID': self.factID,
                      'factType': self.factType}

        return data

    def load(self, data: Dict) -> None:
        self.factID = data['factID']
        self.factType = data['factType']

        if data['state'] == PlayerState.waiting:
            # TODO FIXME XXX
            pass
        else:
            self._state = PlayerState(data['state'])
