import time
import threading
import queue
from enum import Enum

from d20.Manual.Exceptions import PlayerCreationError
from d20.Manual.Logger import logging
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
from d20.Manual.RPC import EntityType

LOGGER = logging.getLogger(__name__)


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
    def __init__(self, *, id, npc, rpcServer, asyncData, **kwargs):
        # Process parameters
        self._state = PlayerState.stopped
        self.memory = dict()
        self._inst = None
        self._runtime = 0.0
        self.dataQueue = queue.Queue()
        self.dHandler = PlayerDirectoryHandler(id, False)

        try:
            self.id = id
            self.npc = npc
            self.rpcServer = rpcServer
            self.asyncData = asyncData
        except KeyError as e:
            LOGGER.exception("Unable to create NPC Tracker")
            raise PlayerCreationError(e) from None

        for (name, value) in kwargs.items():
            if name == 'memory':
                self.memory = value
            else:
                raise TypeError("%s is an invalid kwarg" % (name))

        LOGGER.debug("Tracking NPC '%s' with id %d" % (self.npc.name, self.id))

        self.createNPC()
        self.npc_thread = threading.Thread(
            name='npcTracker.%d' % (self.id),
            target=self.npcThread)
        self.npc_thread.daemon = True
        self.npc_thread.start()

    @property
    def state(self):
        return self._state

    @property
    def name(self):
        return self.npc.name

    def npcThread(self):
        while 1:
            data = self.dataQueue.get()
            try:
                start = time.time()
                self._state = PlayerState.running
                self._inst.handleData(data=data)
            except Exception:
                LOGGER.exception("Error running NPC %s" % (self.npc.name))
            finally:
                runtime = time.time() - start
                self._runtime += runtime
                LOGGER.debug("NPC '%s' took %f seconds"
                             % (self.npc.name, runtime))
                self._state = PlayerState.stopped

    def createNPC(self):
        # Set Options
        options = self.npc.registration.options.parse(
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
            _inst = self.npc.cls(console=console,
                                 options=options)
        except Exception as e:
            LOGGER.exception("Unable to create NPC %s ..." % (self.npc.name))
            raise PlayerCreationError(e) from None

        if not isinstance(_inst, NPCTemplate):
            LOGGER.error(("NPC {0} is not using the NPCTemplate! "
                          "{0} will be ignored!".format(self.npc.name)))
            return

        self._inst = _inst

    def handleData(self, data):
        self.dataQueue.put(data)

    @property
    def runtime(self):
        return self._runtime

    def save(self):
        data = {'id': self.id,
                'name': self.npc.name,
                'memory': self.memory}
        return data

    @staticmethod
    def load(data, npc, rpcServer, asyncData):
        if not isinstance(npc, NPC):
            raise TypeError("Expected an 'NPC' type")

        npc = NPCTracker(**{'id': data['id'],
                            'npc': npc,
                            'rpcServer': rpcServer,
                            'asyncData': asyncData,
                            'memory': data['memory']})
        return npc


class BackStoryCategoryTracker:
    """This class tracks a category of BackStories, ensuring facts are passed
    to them in weighted order and if a BackStory returns 'True'
    short-circuits the execution chain
    """
    def __init__(self, category, **kwargs):
        self._state = PlayerState.stopped
        self.factQueue = queue.Queue()
        self.category = category
        self.backstory_trackers = list()

        self.backstory_thread = threading.Thread(
            name='backstoryTracker.%s' % (category),
            target=self.backStoryCategoryThread)
        self.backstory_thread.daemon = True
        self.backstory_thread.start()

    @property
    def state(self):
        return self._state

    def addBackStoryTracker(self, backstory_tracker):
        self.backstory_trackers.append(backstory_tracker)
        self.backstory_trackers = sorted(
            self.backstory_trackers, key=lambda i: i.weight)

    def backStoryCategoryThread(self):
        while 1:
            fact = self.factQueue.get()
            for backstory_tracker in self.backstory_trackers:
                try:
                    start = time.time()
                    self._state = PlayerState.running
                    result = backstory_tracker.handleFact(fact=fact)
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

    def handleFact(self, fact):
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
    def __init__(self, *, id, backstory, rpcServer, asyncData, **kwargs):
        # Process parameters
        self.memory = dict()
        self._inst = None
        self._runtime = 0.0
        self.factQueue = queue.Queue()
        self.dHandler = PlayerDirectoryHandler(id, False)
        self.__options = None

        try:
            self.id = id
            self.backstory = backstory
            self.rpcServer = rpcServer
            self.asyncData = asyncData
        except KeyError as e:
            LOGGER.exception("Unable to create BackStory Tracker")
            raise PlayerCreationError(e) from None

        for (name, value) in kwargs.items():
            if name == 'memory':
                self.memory = value
            else:
                raise TypeError("%s is an invalid kwarg" % (name))

        LOGGER.debug(
            "Tracking BackStory '%s' with id %d"
            % (self.backstory.name, self.id))

        self.weight = backstory.registration.default_weight
        config_weight = backstory.config.options.get('weight', None)
        if config_weight is not None:
            self.weight = config_weight

        self.createBackStory()

    @property
    def name(self):
        return self.backstory.name

    @property
    def options(self):
        if self.__options is None:
            self.__options = self.backstory.registration.options.parse(
                self.backstory.config.options,
                self.backstory.config.common
            )

        return self.__options

    def createBackStory(self):
        # Generate GM Interface
        rpc_client = self.rpcServer.createClient(EntityType.backstory, self.id)
        console = BackStoryConsole(
            id=self.id,
            rpc_client=rpc_client,
            asyncData=self.asyncData,
            tracker=self,
            directoryHandler=self.dHandler,
            config=self.backstory.config.common)
        try:
            _inst = self.backstory.cls(
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

    def handleFact(self, fact):
        return self._inst.handleFact(fact=fact)

    @property
    def runtime(self):
        return self._runtime

    def addRuntime(self, runtime):
        self._runtime += runtime

    def save(self):
        data = {'id': self.id,
                'name': self.backstory.name,
                'memory': self.memory}
        return data

    @staticmethod
    def load(data, backstory, rpcServer, asyncData):
        if not isinstance(backstory, BackStory):
            raise TypeError("Expected an 'BackStory' type")

        backstory = BackStoryTracker(**{
            'id': data['id'],
            'backstory': backstory,
            'rpcServer': rpcServer,
            'asyncData': asyncData,
            'memory': data['memory']})
        return backstory


class PlayerTracker(object):
    """PlayerTracker

        This class tracks an individual Player and provides a unified
        way of creating its clones which actually invoke its functionality

        Args:
            id: The id of the player
            player: Instance of Player class
            rpcServer: RPCServer instance
    """
    def __init__(self, *, id, player, rpcServer, asyncData, **kwargs):
        # Process parameters
        self.count = 0
        self.dHandler = PlayerDirectoryHandler(id, True)

        # Shared dictionary all clones have access to
        self.memory = dict()

        # Dictionaries for each clone, must be stored here due to init
        self.cloneMemory = dict()

        # Track what interested facts this player has received
        self.factTracker = dict()

        # Since clones can be deleted keep track of them in a dict
        # instead of a list
        self.clones = dict()

        self.maxTurnTime = 0
        self.ignoredClones = []

        self._runtime = 0.0

        self.__options = None

        try:
            self.id = id
            self.player = player
            self.rpcServer = rpcServer
            self.asyncData = asyncData
        except KeyError as e:
            LOGGER.exception("Unable to setup Player Tracker")
            raise PlayerCreationError(e) from None

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
    def options(self):
        if self.__options is None:
            self.__options = self.player.registration.options.parse(
                self.player.config.options,
                self.player.config.common
            )

        return self.__options

    @property
    def state(self):
        playerState = PlayerState.stopped
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
    def states(self):
        playerStates = [
            clone.state for(clone_id, clone) in self.clones.items()]

        return playerStates

    @property
    def name(self):
        return self.player.name

    @property
    def runtime(self):
        return self._runtime

    def _addRuntime(self, local_runtime):
        self._runtime += local_runtime

    def createClone(self, clone_id=None, tainted=False):
        if clone_id is None:
            # Get clone id
            clone_id = self.count
            self.count += 1

        # Create Clone Memory aka 'data'
        self.cloneMemory[clone_id] = dict()

        # Generate an RPC client
        rpc_client = self.rpcServer.createClient(
            EntityType.player, self.id, clone_id)

        # Generate GM Interface
        console = PlayerConsole(id=self.id,
                                clone_id=clone_id,
                                tracker=self,
                                rpc_client=rpc_client,
                                asyncData=self.asyncData,
                                directoryHandler=self.dHandler,
                                config=self.player.config.common,
                                tainted=tainted)
        try:
            clone_inst = self.player.cls(console=console,
                                         options=self.options)
        except Exception:
            LOGGER.exception("Unable to create player %s instance"
                             % (self.player.name))
            return None

        if not isinstance(clone_inst, PlayerTemplate):
            LOGGER.error(("Player {0} is not using the PlayerTemplate! "
                          "{0} will be ignored!".format(self.player.name)))
            return None

        clone = CloneTracker(id=clone_id,
                             inst=clone_inst,
                             console=console,
                             tracker=self)

        self.clones[clone_id] = clone

        return clone

    def checkIfHandledFact(self, fact):
        if fact._type not in self.factTracker:
            return False

        if fact.id not in self.factTracker[fact._type]:
            return False

        return True

    def handleFact(self, fact):
        if fact._type not in self.factTracker:
            self.factTracker[fact._type] = set()
        self.factTracker[fact._type].add(fact.id)
        clone = self.createClone()
        if clone is None:
            raise PlayerCreationError("Unable to create clone")
        clone.handleFact(fact=fact)

    def handleHypothesis(self, hyp):
        clone = self.createClone(tainted=True)
        if clone is None:
            raise PlayerCreationError("Unable to create clone")
        clone.handleHypothesis(hypothesis=hyp)

    def save(self):
        data = {'id': self.id,
                'name': self.player.name,
                'memory': self.memory,
                'cloneMemory': self.cloneMemory,
                'factTracker': self.factTracker,
                'count': self.count}

        clone_data = dict()
        for (id, clone) in self.clones.items():
            clone_data[id] = clone.save()
        data['clones'] = clone_data

        return data

    @staticmethod
    def load(data, player, rpcServer, asyncData):
        if not isinstance(player, Player):
            raise TypeError("Expected 'Player' instance")

        player = PlayerTracker(**{'id': data['id'],
                                  'player': player,
                                  'rpcServer': rpcServer,
                                  'asyncData': asyncData,
                                  'memory': data['memory'],
                                  'cloneMemory': data['cloneMemory'],
                                  'count': data['count'],
                                  'factTracker': data['factTracker']})

        for (id, clone_data) in data['clones'].items():
            clone = player.createClone(id)
            clone.load(clone_data)
        return player


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
            self.inst = kwargs['inst']
            self.id = kwargs['id']
            self.tracker = kwargs['tracker']
            self.console = kwargs['console']
        except KeyError:
            LOGGER.exception("Unable to setup Clone Tracker")
            raise

        self.myThread = None
        self._state = PlayerState.stopped
        self._turnStart = 0
        self.factID = None
        self.factType = None

    @property
    def state(self):
        return self._state

    @property
    def turnTime(self):
        if self._turnStart == 0:
            return 0

        return time.time() - self._turnStart

    def handlerThread(self, target, **kwargs):
        start = time.time()
        self._state = PlayerState.running
        self._turnStart = start
        try:
            target(**kwargs)
        except Exception:
            LOGGER.exception("Error running player handler")
        finally:
            self._state = PlayerState.stopped

        runtime = time.time() - start
        self.tracker._addRuntime(runtime)
        LOGGER.debug("Player '%s', Clone %d took %f seconds"
                     % (self.tracker.name,
                        self.id, runtime))
        self.tracker.rpcServer.destroyClient(self.console._rpc.id)

    def handleFact(self, fact):
        self.factID = fact.id
        self.factType = fact._type
        self.myThread = threading.Thread(
            name='cloneTracker.%d.%d' % (self.tracker.id, self.id),
            target=self.handlerThread,
            args=(self.inst.handleFact,),
            kwargs={"fact": fact})
        self.myThread.daemon = True
        self.myThread.start()

    def handleHypothesis(self, hyp):
        self.factID = hyp.id
        self.factType = hyp._type
        self.myThread = threading.Thread(
            name='cloneTracker.%d.%d' % (self.tracker.id, self.id),
            target=self.handlerThread,
            args=(self.inst.handleHypothesis,),
            kwargs={"hypothesis": hyp})
        self.myThread.daemon = True
        self.myThread.start()

    def save(self):
        if isinstance(self._state, Enum):
            state = self._state.value
        else:
            state = self._state
        data = {'state': state,
                'factID': self.factID,
                'factType': self.factType}

        return data

    def load(self, data):
        self.factID = data['factID']
        self.factType = data['factType']

        if data['state'] == PlayerState.waiting:
            # TODO FIXME XXX
            pass
        else:
            self._state = PlayerState(data['state'])
