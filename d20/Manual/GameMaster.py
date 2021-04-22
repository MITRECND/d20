import sys
import time
import threading
import asyncio
import yaml

from d20.version import (
    GAME_ENGINE_VERSION_RAW,
    GAME_ENGINE_VERSION,
    parseVersion)
from d20.Manual.Exceptions import (PlayerCreationError,
                                   DuplicateObjectError,
                                   TemporaryDirectoryError)
from d20.Manual.Logger import logging
from d20.Manual.Trackers import (NPCTracker,
                                 PlayerTracker,
                                 BackStoryTracker,
                                 BackStoryCategoryTracker)
from d20.Manual.BattleMap import (FactTable,
                                  HypothesisTable,
                                  ObjectList,
                                  FileObject)
from d20.Manual.RPC import (RPCServer,
                            RPCResponseStatus,
                            RPCCommands,
                            RPCStreamCommands)
from d20.Manual.Temporary import TemporaryHandler
from d20.Manual.Console import (PlayerState)
from d20.Manual.Config import Configuration
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.BackStories import (
    verifyBackStories,
    resolveBackStoryFacts)
from d20.Screens import verifyScreens

LOGGER = logging.getLogger(__name__)


class GameMaster(object):
    """GameMaster

        The GameMaster class is the entrypoint for d20, and coordinates
        all functionality by establishing, saving information, and
        invoking players/npcs.

        Args:
            extra_players: List of extra players paths
            extra_npcs: List of extra npc paths
            extra_backstories: List of extra backstory paths
            extra_screens: List of extra screen paths
            config: An instance of a Config object
            options: A Namespace object (basically args)
            save_state: A dict of saved state information from a previous run
    """
    def __init__(self, **kwargs):
        self.backstory_facts = list()
        self.gameThread = None
        self.objects = ObjectList()
        self.facts = FactTable()
        self.hyps = HypothesisTable()
        self.players = list()
        self.npcs = list()
        self.backstories = list()
        self.backstory_categories = dict()
        self.fact_interests = dict()
        self.hyp_interests = dict()
        self.screens = dict()
        self.newGamePlus = False
        self.gameRunning = False
        self._gameStartTime = 0
        self._idleCount = 0
        self._idleTicks = 100  # 'ticks' i.e., primarly loop cycles

        self.factWaitList = list()
        self.factStreamList = dict()
        self.hypStreamList = dict()
        self.objectStreamList = list()

        self.rpc = RPCServer()
        self.registerHandlers()

        self.extra_players = []
        self.extra_npcs = []
        self.extra_backstories = []
        self.extra_screens = []
        self.Config = Configuration()
        self.options = None
        self.save_state = None
        self.asyncData = type(
            'asyncData', (), {'enabled': False,
                              'eventloop': None,
                              'eventwatcher': None})
        self.tempHandler = None

        for (name, value) in kwargs.items():
            if name == 'extra_players':
                self.extra_players = value
            elif name == 'extra_npcs':
                self.extra_npcs = value
            elif name == 'extra_backstories':
                self.extra_backstories = value
            elif name == 'extra_screens':
                self.extra_screens = value
            elif name == 'config':
                self.Config = value
            elif name == 'options':
                self.options = value
            elif name == 'save_state':
                self.save_state = value
            else:
                raise TypeError("%s is an invalid keyword argument" % (name))

        if self.save_state is None and self.options is None:
            raise TypeError(("Either Save State or "
                             "options must be specified"))

        if self.save_state is None:
            if 'temporary' not in self.options:
                raise RuntimeError(
                    "Expected temporary directory to be specified in options")

            self.tempHandler = TemporaryHandler(self.options.temporary)

        # Idle Wait Default: 1 second
        self._idleWait = self.Config.d20.get('graceTime', 1)

        # Max Game Time Default unlimited (0 value)
        self._maxGameTime = self.Config.d20.get('maxGameTime', 0)

        # Max turn Time for each Player Default unlimited (0 value)
        self._maxTurnTime = self.Config.d20.get('maxTurnTime', 0)

        if self.save_state is not None:
            self.newGamePlus = True
        else:
            for inp in ['file', 'backstory_facts', 'backstory_facts_path']:
                if inp not in self.options:
                    setattr(self.options, inp, None)

            if all([inp is None for inp in [
                    self.options.file,
                    self.options.backstory_facts,
                    self.options.backstory_facts_path]]):
                raise TypeError((
                    "Expected one of 'file', 'backstory-facts', or "
                    "'backstory-facts-paths' in options"))

            # Load BackStories
            self.registerBackStories()
            # Load NPCS
            self.registerNPCs()
            # Load Player Information
            self.registerPlayers()

            if self.options.file is not None:
                # Load the file from options
                try:
                    with open(self.options.file, 'rb') as f:
                        data = f.read()
                except Exception:
                    LOGGER.exception(
                        "Unable to open file %s" % (self.options.file))
                    sys.exit(1)

                self.objects.addObject(
                    data,
                    _creator_="GameMaster",
                    metadata={'filename': self.options.file})
            elif self.options.backstory_facts is not None:
                backstory_facts = yaml.load(
                    self.options.backstory_facts, Loader=yaml.FullLoader)
                self.backstory_facts = resolveBackStoryFacts(backstory_facts)
            else:
                with open(self.options.backstory_facts_path, 'r') as f:
                    backstory_facts = yaml.load(
                        f.read(), Loader=yaml.FullLoader)
                self.backstory_facts = resolveBackStoryFacts(backstory_facts)

        # Unconditionally load screens
        self.registerScreens()

    def registerHandlers(self):
        self.rpc.registerIdleFunction(self.checkGameState)

        self.rpc.registerHandlers(
            [(RPCCommands.noop, self.handleNoop),
             (RPCCommands.print, self.handlePrint),
             (RPCCommands.addFact, self.handleAddFact),
             (RPCCommands.addHyp, self.handleAddHyp),
             (RPCCommands.addObject, self.handleAddObject),
             (RPCCommands.getObject, self.handleGetObject),
             (RPCCommands.getFact, self.handleGetFact),
             (RPCCommands.getHyp, self.handleGetHyp),
             (RPCCommands.getAllHyps, self.handleGetAllHyps),
             (RPCCommands.getAllFacts, self.handleGetAllFacts),
             (RPCCommands.getAllObjects, self.handleGetAllObjects),
             (RPCCommands.waitTillFact, self.handleWaitTillFact),
             (RPCCommands.addHyp, self.handleAddHyp),
             (RPCCommands.getHyp, self.handleGetHyp),
             (RPCCommands.getAllHyps, self.handleGetAllHyps),
             (RPCCommands.promote, self.handlePromote)])

        self.rpc.registerStreamHandlers(
            [(RPCStreamCommands.factStream,
              self.streamHandleFactStreamStart,
              self.streamHandleFactStreamStop),
             (RPCStreamCommands.childFactStream,
              self.streamHandleChildFactStreamStart,
              self.streamHandleChildFactStreamStop),
             (RPCStreamCommands.childObjectStream,
              self.streamHandleChildObjectStreamStart,
              self.streamHandleChildObjectStreamStop),
             (RPCStreamCommands.childHypStream,
              self.streamHandleChildHypStreamStart,
              self.streamHandleChildHypStreamStop)])

    def registerScreens(self):
        self.screens = verifyScreens(self.extra_screens,
                                     self.Config)

    def registerNPCs(self, load=False):
        npcs = verifyNPCs(self.extra_npcs,
                          self.Config)

        if load and self.save_state['npcs'] is not None:
            for saved_npc in self.save_state['npcs']:
                loaded_npc = None
                for npc in npcs:
                    if npc.name == saved_npc['name']:
                        loaded_npc = npc
                        break

                if loaded_npc is not None:
                    tracker = NPCTracker.load(saved_npc,
                                              loaded_npc,
                                              self.rpc,
                                              self.asyncData)
                    self.npcs.append(tracker)
                    npcs.remove(loaded_npc)

        for npc in npcs:
            # Get npc id based on list length
            npc_id = len(self.npcs)

            try:
                tracker = NPCTracker(id=npc_id,
                                     npc=npc,
                                     rpcServer=self.rpc,
                                     asyncData=self.asyncData)
            except PlayerCreationError:
                LOGGER.error("Unable to create NPC %s ... skipping"
                             % (npc.name))
                continue
            except Exception:
                LOGGER.exception("Unexpected issue creating NPC")
                continue

            # Add tracker to npc list
            self.npcs.append(tracker)

    def registerBackStories(self, load=False):
        backstories = verifyBackStories(
            self.extra_backstories, self.Config)

        if load and self.save_state['backstories'] is not None:
            for saved_backstory in self.save_state['backstories']:
                loaded_backstory = None
                for backstory in backstories:
                    if backstory.name == saved_backstory['name']:
                        loaded_backstory = backstory
                        break

                if loaded_backstory is not None:
                    tracker = BackStoryTracker.load(
                        saved_backstory, loaded_backstory,
                        self.rpc, self.asyncData)
                    self.backstories.append(tracker)
                    backstories.remove(loaded_backstory)

        for backstory in backstories:
            # Get backstory id based on list length
            backstory_id = len(self.backstories)
            category = backstory.registration.category

            if category not in self.backstory_categories.keys():
                self.backstory_categories[
                    category] = BackStoryCategoryTracker(category)

            try:
                tracker = BackStoryTracker(
                    id=backstory_id, backstory=backstory,
                    rpcServer=self.rpc, asyncData=self.asyncData)
            except PlayerCreationError:
                LOGGER.error(
                    "Unable to create BackStory %s ... skipping"
                    % (backstory.name))
                continue
            except Exception:
                LOGGER.exception("Unexpected issue creating BackStory")
                continue

            # Add tracker to backstory list
            self.backstories.append(tracker)
            self.backstory_categories[category].addBackStoryTracker(tracker)

    def registerPlayers(self, load=False):
        unloaded_players = verifyPlayers(self.extra_players,
                                         self.Config)

        if load and self.save_state['players'] is not None:
            for saved_player in self.save_state['players']:
                loaded_player = None
                for player in unloaded_players:
                    if player.name == saved_player['name']:
                        loaded_player = player
                        break

                if loaded_player is not None:
                    tracker = PlayerTracker.load(saved_player,
                                                 loaded_player,
                                                 self.rpc,
                                                 self.asyncData)
                    tracker.maxTurnTime = self._maxTurnTime
                    self.players.append(tracker)
                    unloaded_players.remove(loaded_player)

        for player in unloaded_players:
            # Get player id based on list length
            player_id = len(self.players)

            try:
                tracker = PlayerTracker(id=player_id,
                                        player=player,
                                        rpcServer=self.rpc,
                                        asyncData=self.asyncData)
                tracker.maxTurnTime = self._maxTurnTime
            except PlayerCreationError:
                LOGGER.error("Unable to create Player %s ... skipping"
                             % (player.name))
                continue
            except Exception:
                LOGGER.exception("Unexpected issue creating Player")
                continue

            # Add tracker top player list
            self.players.append(tracker)

        for tracker in self.players:
            player = tracker.player
            # Register player's interests
            for interest in player.registration.factInterests:
                if interest not in self.fact_interests:
                    self.fact_interests[interest] = []
                self.fact_interests[interest].append(tracker.id)

            for interest in player.registration.hypInterests:
                if interest not in self.hyp_interests:
                    self.hyp_interests[interest] = []
                self.hyp_interests[interest].append(tracker.id)

    async def watchGame(self):
        while self.gameRunning:
            await asyncio.sleep(.01)

        self.stop()

    def startGame(self, asyncio_enable=False):
        if self.newGamePlus:
            self.load()

        self._gameStartTime = time.time()
        self.gameThread = threading.Thread(
            target=self.runGame,
            name="GameThread")
        self.gameRunning = True
        self.gameThread.start()

        if not self.newGamePlus:
            if self.options.file is not None:
                FileObj = self.objects[0]
                for npc in self.npcs:
                    LOGGER.debug(
                        "Sending Object %d to npc %s" % (FileObj.id, npc.name))
                    try:
                        npc.handleData(data=FileObj)
                    except Exception:
                        LOGGER.exception(
                            "Error calling NPC handleData function")
            else:  # Engage backstories
                self.engageBackStories()

        if asyncio_enable:
            self.asyncData.enabled = True
            self.asyncData.eventloop = asyncio.get_event_loop()
            self.asyncData.eventwatcher = asyncio.get_child_watcher()
            try:
                self.asyncData.eventloop.run_until_complete(self.watchGame())
                # watchGame will call stop(), so just need to join to be safe
                self.join()
            except KeyboardInterrupt:
                self.astop()
                self.join()

    def engageBackStories(self):
        for fact in self.backstory_facts:
            for (category,
                 backstory_category) in self.backstory_categories.items():
                LOGGER.debug(
                    "Sending fact to %s backstories" % (category))
                try:
                    backstory_category.handleFact(fact=fact)
                except Exception:
                    LOGGER.exception(
                        "Error calling BackStory handleFact function")

    def join(self):
        self.gameThread.join()

    def _parse_screen_options(self, screen):
        options = screen.registration.options.parse(
            screen.config.options,
            screen.config.common
        )
        return options

    def provideData(self, screen_name, printable=False):
        if screen_name not in self.screens:
            raise ValueError("No screen by that name")

        options = self._parse_screen_options(
            self.screens[screen_name]
        )
        screen = self.screens[screen_name].cls(objects=self.objects,
                                               facts=self.facts,
                                               hyps=self.hyps,
                                               options=options)
        if printable:
            return screen.present()
        else:
            return screen.filter()

    def save(self):
        """Save current game state for later ingestion
        """
        save_state = {'players': list(),
                      'npcs': list(),
                      'objects': list(),
                      'facts': dict(),
                      'hyps': dict(),
                      'engine': GAME_ENGINE_VERSION_RAW}

        save_state['temp_base'] = self.tempHandler.temporary_base

        # Save PlayerTracker Information
        save_state['players'] = \
            [player.save() for player in self.players]

        save_state['npcs'] = \
            [npc.save() for npc in self.npcs]

        # Save Object List
        save_state['objects'] = \
            [obj.save() for obj in self.objects]

        save_state['facts'] = self.facts.save()
        save_state['hyps'] = self.hyps.save()

        return save_state

    def load(self):
        """Load a game from a save_state
        """
        try:
            state_version = parseVersion(self.save_state['engine'])
        except KeyError:
            state_version = parseVersion('0.0.0')

        if state_version < GAME_ENGINE_VERSION:
            LOGGER.warning(
                "Attempting to load older save state (v %s)"
                % (state_version))

        self.tempHandler = TemporaryHandler(self.save_state['temp_base'])
        self.facts = FactTable.load(self.save_state['facts'])
        self.hyps = HypothesisTable.load(self.save_state['hyps'])

        for obj in self.save_state['objects']:
            self.objects.append(FileObject.load(obj))

        self.registerBackStories(load=True)
        self.registerNPCs(load=True)
        self.registerPlayers(load=True)

        for (_type, column) in self.facts.items():
            if _type in self.fact_interests:
                for player_id in self.fact_interests[_type]:
                    for fact in column:
                        player = self.players[player_id]
                        if not player.checkIfHandledFact(fact):
                            player.handleFact(fact)

    def getEntityName(self, entity):
        if entity.isPlayer:
            name = self.players[entity.id].name
        elif entity.isNPC:
            name = self.npcs[entity.id].name
        elif entity.isBackStory:
            name = self.backstories[entity.id].name
        else:
            name = "Unknown!"

        return name

    def astop(self):
        try:
            # Cleanup async loop before calling stop function
            self.asyncData.eventloop.stop()
            self.asyncData.eventloop.close()
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
        except Exception:
            LOGGER.warning(
                "Exception trying to cleanup event loop", exc_info=True)
        self.stop()

    def stop(self):
        try:
            self.rpc.stop()
        except Exception:
            LOGGER.warning("Exception trying to stop GM", exc_info=True)

    def cleanup(self):
        if self.options.save_file is None and not self.newGamePlus:
            try:
                self.tempHandler.cleanup()
            except TemporaryDirectoryError:
                raise

    """ Game Thread Functions """
    def runGame(self):
        LOGGER.debug("Starting Game")
        self.rpc.start()
        self.rpc.join()
        self.gameRunning = False
        self._reportRuntime()

    def _reportRuntime(self):
        runtime_threshold = 0.00009
        npc_runtimes = sorted(
            [(npc.runtime, npc.name) for npc in self.npcs],
            key=lambda el: el[0],
            reverse=True
        )

        player_runtimes = sorted(
            [(player.runtime, player.name) for player in self.players],
            key=lambda el: el[0],
            reverse=True
        )

        max_name = max(
            [len(name) for (runtime, name) in npc_runtimes + player_runtimes])

        for (runtime, npc_name) in npc_runtimes:
            if runtime > runtime_threshold:
                LOGGER.info(
                    "NPC    '{0: <{2}}' - runtime {1: .4f}s".format(
                        npc_name, runtime, max_name))

        for (runtime, player_name) in player_runtimes:
            if runtime > runtime_threshold:
                LOGGER.info(
                    "Player '{0: <{2}}' - runtime {1: .4f}s".format(
                        player_name, runtime, max_name))

    def checkGameState(self, last_action_ts):
        waiting = False

        if self._maxGameTime > 0:
            runtime = time.time() - self._gameStartTime
            if runtime > self._maxGameTime:
                LOGGER.info(
                    f"Maximum game time ({self._maxGameTime}s) reached, "
                    "stopping game")
                return True

        for backstory_category in self.backstory_categories.values():
            # If any backstory is running, the game hasn't even started yet
            # return immediately
            if backstory_category.state == PlayerState.running:
                return False

        for player in self.players:
            # If any player is running, the game must continue
            # return immediately
            if player.state == PlayerState.running:
                return False
            elif player.state == PlayerState.waiting:
                waiting = True

        for npc in self.npcs:
            # NPCs are either 'running' or 'stopped'
            if npc.state == PlayerState.running:
                return False

        if waiting:
            self._idleCount = 0
            # Otherwise timeout after _idleWait seconds of no progress
            if time.time() - last_action_ts > self._idleWait:
                # Assume game has timed out?
                LOGGER.info("No game progress for %d second(s), stopping game"
                            % (self._idleWait))
                return True
        else:
            self._idleCount += 1
            if self._idleCount > self._idleTicks:
                LOGGER.info("All Players stopped running")
                return True

        return False

    def handleNoop(self, msg):
        """handleNoop is meant to reset the game timer"""

    def handlePrint(self, msg):
        name = self.getEntityName(msg.entity)

        if 'kwargs' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Missing required field in args")
            return

        if 'args' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Missing required field in args")
            return

        sep = ' '
        for (key, value) in msg.args.kwargs.items():
            if key == 'sep':
                sep = value
            else:
                self.rpc.sendErrorResponse(
                    msg, reason="Unexpected field in kwargs")
                return

        out_str = "%s: " % (name)

        if len(msg.args.args) == 1:
            try:
                print_string = str(msg.args.args[0])
            except Exception:
                LOGGER.exception("Unable to format string for printing")
                self.rpc.sendErrorResponse(
                    msg, reason="Unable to convert contents to string")
                return
        else:
            try:
                print_string = sep.join([str(arg) for arg in msg.args.args])
            except Exception:
                LOGGER.exception("Unable to format string for printing")
                self.rpc.sendErrorResponse(
                    msg, reason="Unable to convert arguments to string")
                return

        LOGGER.info(out_str + print_string)

    def _checkFactStreamerConditions(self, fact, msg, stream_msg):
        if msg.entity == stream_msg.entity:
            return False

        if stream_msg.stream.command == RPCStreamCommands.childFactStream:
            args = stream_msg.stream.args
            if (args.object_id is not None and
                    args.object_id not in fact.parentObjects):
                return False
            elif (args.fact_id is not None and
                    args.fact_id not in fact.parentFacts):
                return False
            elif (args.hyp_id is not None and
                    args.hyp_id not in fact.parentHyps):
                return False

        return True

    def _checkHypStreamerConditions(self, hyp, msg, stream_msg):
        if msg.entity == stream_msg.entity:
            return False

        if stream_msg.stream.command == RPCStreamCommands.childHypStream:
            args = stream_msg.stream.args
            if (args.object_id is not None and
                    args.object_id not in hyp.parentObjects):
                return False
            elif (args.fact_id is not None and
                    args.fact_id not in hyp.parentFacts):
                return False
            elif (args.hyp_id is not None and
                    args.hyp_id not in hyp.parentHyps):
                return False

        return True

    def _checkObjectStreamerConditions(self, obj, msg, stream_msg):
        if msg.entity == stream_msg.entity:
            return False

        if stream_msg.stream.command == RPCStreamCommands.childObjectStream:
            args = stream_msg.stream.args
            if (args.object_id is not None and
                    args.object_id not in obj.parentObjects):
                return False
            elif (args.fact_id is not None and
                    args.fact_id not in obj.parentFacts):
                return False
            elif (args.hyp_id is not None and
                    args.hyp_id not in obj.parentHyps):
                return False
        return True

    def handleAddFact(self, msg):
        if 'fact' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'fact' not found in args")
            return

        fact = msg.args.fact

        try:
            fact_id = self.facts.add(fact)
        except TypeError as e:
            self.rpc.sendErrorResponse(
                msg, reason=str(e))
            return

        for pobj in fact.parentObjects:
            obj = self.objects[pobj]
            obj.addChildFact(fact_id)
        for pfct in fact.parentFacts:
            fct = self.facts.findById(pfct)
            fct.addChildFact(fact_id)
        for phyp in fact.parentHyps:
            hyp = self.hyps.findById(phyp)
            hyp.addChildFact(fact_id)

        self.rpc.sendOKResponse(msg)

        # Send Facts to streamers
        if fact._type in self.factStreamList:
            result = {'fact': fact}
            for stream_msg in self.factStreamList[fact._type]:
                if self._checkFactStreamerConditions(fact, msg, stream_msg):
                    self.rpc.sendOKResponse(stream_msg, result=result)

        # Send Facts to wait list
        updatedList = list()
        for (fact_types, msg) in self.factWaitList:
            if fact._type in fact_types:
                result = {'fact': fact}
                self.rpc.sendOKResponse(msg, result=result)
            else:
                updatedList.append((fact_types, msg))
        self.factWaitList = updatedList

        # Send Facts to interested players
        if fact._type in self.fact_interests:
            for player in self.fact_interests[fact._type]:
                if msg.entity.isPlayer and msg.entity.id == player:
                    continue
                try:
                    self.players[player].handleFact(fact)
                except PlayerCreationError:
                    LOGGER.error("Unable to send fact to player %s"
                                 % (self.players[player].name))
                except Exception:
                    LOGGER.exception(("Unexpected exception sending fact "
                                      "to player"))

    def handleAddHyp(self, msg):
        if 'hyp' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'hyp' not found in args")
            return

        hyp = msg.args.hyp

        try:
            hyp_id = self.hyps.add(hyp)
        except TypeError as e:
            self.rpc.sendErrorResponse(
                msg, reason=str(e))
            return

        for pobj in hyp.parentObjects:
            obj = self.objects[pobj]
            obj.addChildHyp(hyp_id)
        for pfct in hyp.parentFacts:
            fct = self.facts.findById(pfct)
            fct.addChildHyp(hyp_id)
        for phyp in hyp.parentHyps:
            hyp = self.hyps.findById(phyp)
            hyp.addChildHyp(hyp_id)

        self.rpc.sendOKResponse(msg)

        # Send Facts to streamers
        if hyp._type in self.hypStreamList:
            result = {'hyp': hyp}
            for stream_msg in self.hypStreamList[hyp._type]:
                if self._checkHypStreamerConditions(hyp, msg, stream_msg):
                    self.rpc.sendOKResponse(stream_msg, result=result)

        # Send Hypotheses to interested players
        if hyp._type in self.hyp_interests:
            for player in self.hyp_interests[hyp._type]:
                if msg.entity.isPlayer and msg.entity.id == player:
                    continue
                try:
                    self.players[player].handleHypothesis(hyp)
                except PlayerCreationError:
                    LOGGER.error("Unable to send hypothesis to player %s"
                                 % (self.players[player].name))
                except Exception:
                    LOGGER.exception(("Unexpected exception sending hyp "
                                      "to player"))

    def promoteHyp(self, hyp_id):
        item = self.hyps.remove(hyp_id)
        item._untaint()
        fact_id = self.facts.add(item)

        # Iterate through all relationships and update link
        for pobj in item.parentObjects:
            obj = self.objects[pobj]
            obj.remChildHyp(hyp_id)
            obj.addChildFact(fact_id)
        for pfct in item.parentFacts:
            fct = self.facts.findById(pfct)
            fct.remChildHyp(hyp_id)
            fct.addChildFact(fact_id)
        for phyp in item.parentHyps:
            hyp = self.hyps.findById(phyp)
            hyp.remChildHyp(hyp_id)
            hyp.addChildFact(fact_id)
        for cobj in item.childObjects:
            obj = self.objects[cobj]
            obj.remParentHyp(hyp_id)
            obj.addParentFact(fact_id)
        for cfct in item.childFacts:
            fct = self.facts.findById(cfct)
            fct.remParentHyp(hyp_id)
            fct.addParentFact(fact_id)
        for chyp in item.childHyps:
            hyp = self.hyps.findById(chyp)
            hyp.remParentHyp(hyp_id)
            hyp.addParentFact(fact_id)

        return item

    def handlePromote(self, msg):
        if 'hyp_id' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'hyp_id' not found in args")
            return

        hyp_id = msg.args.hyp_id
        try:
            item = self.promoteHyp(hyp_id)
        except Exception:
            self.rpc.sendErrorResponse(
                msg, reason="Unable to promote hyp to fact")
            return

        self.rpc.sendOKResponse(msg, result={'fact': item})

    def handleAddObject(self, msg):
        try:
            object_data = msg.args.object_data
            creator = msg.args.creator
            parentObjects = msg.args.parentObjects
            parentFacts = msg.args.parentFacts
            parentHyps = msg.args.parentHyps
            metadata = msg.args.metadata
            encoding = msg.args.encoding
        except AttributeError as e:
            self.rpc.sendErrorResponse(msg, reason=str(e))
            return

        isduplicate = False
        try:
            FileObj = self.objects.addObject(
                object_data,
                _creator_=creator,
                _parentObjects_=parentObjects,
                _parentFacts_=parentFacts,
                _parentHyps_=parentHyps,
                metadata=metadata,
                encoding=encoding)
        except DuplicateObjectError:
            isduplicate = True
            FileObj = self.objects.getObjectByData(object_data)
        except Exception as e:
            self.rpc.sendErrorResponse(
                msg,
                reason="Unable to track object: %s" % (str(e)))
            return

        if parentObjects:
            for pid in parentObjects:
                pobj = self.objects[pid]
                pobj.addChildObject(FileObj.id)
        if parentFacts:
            for fid in parentFacts:
                pfct = self.facts.findById(fid)
                pfct.addChildObject(FileObj.id)
        if parentHyps:
            for hid in parentHyps:
                phyp = self.hypotheses.findById(hid)
                phyp.addChildObject(FileObj.id)

        result = {'object_id': FileObj.id}
        self.rpc.sendOKResponse(msg, result=result)

        # Send object to streamers
        for stream_msg in self.objectStreamList:
            result = {'object': FileObj}
            if self._checkObjectStreamerConditions(FileObj, msg, stream_msg):
                self.rpc.sendOKResponse(stream_msg, result=result)

        # Only send to NPCs if it's not a duplicate
        if not isduplicate:
            for npc in self.npcs:
                LOGGER.debug("Sending Object %d to npc %s"
                             % (FileObj.id, npc.name))
                try:
                    npc.handleData(data=FileObj)
                except Exception:
                    LOGGER.exception("Error calling NPC handleData function")

    def handleGetObject(self, msg):
        try:
            # Try to reference fields to ensure msg has required fields
            msg.entity.isPlayer
            msg.entity.id
            object_id = msg.args.object_id
        except AttributeError as e:
            self.rpc.sendErrorResponse(msg, reason=str(e))
            return

        try:
            FileObj = self.objects[object_id]
        except KeyError:
            self.rpc.sendErrorResponse(msg, reason="No object by that id")
            return

        result = {'object': FileObj}
        self.rpc.sendOKResponse(msg, result=result)

    def handleGetAllObjects(self, msg):
        result = {'object_list': self.objects.tolist()}
        self.rpc.sendOKResponse(msg, result=result)

    def handleGetFact(self, msg):
        if 'fact_id' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'fact_id' not found in args")
            return

        fact_id = msg.args.fact_id

        fact = self.facts.findById(fact_id)

        if fact is not None:
            result = {'fact': fact}
            self.rpc.sendOKResponse(msg, result=result)
        else:
            self.rpc.sendErrorResponse(msg, reason="not found")

    def handleGetAllFacts(self, msg):
        if 'fact_type' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'fact_type' not found in args")
            return

        fact_types = msg.args.fact_type
        fact_list = list()

        try:
            for ft in fact_types:
                fc = self.facts.getColumn(ft)
                if fc is not None:
                    fact_list.extend(fc.tolist())
        except Exception:
            self.rpc.sendErrorResponse(msg,
                                       reason="Unable to parse fact types")
            return

        result = {'fact_list': fact_list}
        self.rpc.sendOKResponse(msg, result=result)

    def handleGetHyp(self, msg):
        if 'hyp_id' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'hyp_id' not found in args")
            return

        hyp_id = msg.args.hyp_id
        hyp = self.hyps.findById(hyp_id)

        if hyp is not None:
            result = {'hyp': hyp}
            self.rpc.sendOKResponse(msg, result=result)
        else:
            self.rpc.sendErrorResponse(msg, reason="not found")

    def handleGetAllHyps(self, msg):
        if 'hyp_type' not in msg.args:
            self.rpc.sendErrorResponse(
                msg, reason="Required field 'hyp_type' not found in args")
            return

        hyp_types = msg.args.hyp_type
        hyp_list = list()

        try:
            for ft in hyp_types:
                fc = self.hyps.getColumn(ft)
                if fc is not None:
                    hyp_list.extend(fc.tolist())
        except Exception:
            self.rpc.sendErrorResponse(msg,
                                       reason="Unable to parse hyp types")
            return

        result = {'hyp_list': hyp_list}
        self.rpc.sendOKResponse(msg, result=result)

    def handleWaitTillFact(self, msg):
        fact_type = msg.args.fact_type
        last_fact = msg.args.last_fact

        # Based on last_fact, see if any facts have been added
        # If any have been added respond back immediately with the first one
        if last_fact is not None:
            newer_fact = None
            for ft in fact_type:
                facts = self.facts.getColumn(ft)
                if facts is not None:
                    for fact in facts:
                        if not newer_fact:
                            if fact.id > last_fact:
                                newer_fact = fact
                        else:
                            if fact.id > last_fact and fact.id < newer_fact.id:
                                newer_fact = fact

            if newer_fact:
                result = {'fact': newer_fact}
                self.rpc.sendResponse(msg, RPCResponseStatus.ok, result=result)
                return
        # else need to put data into wait list
        self.factWaitList.append((fact_type, msg))

    def streamHandleFactStreamStart(self, msg):
        fact_types = msg.stream.args.fact_types
        only_latest = msg.stream.args.only_latest

        if not only_latest:
            for ft in fact_types:
                factColumn = self.facts.getColumn(ft)
                if factColumn is not None:
                    for fact in factColumn:
                        result = {'fact': fact}
                        self.rpc.sendResponse(msg,
                                              RPCResponseStatus.ok,
                                              result=result)

        for ft in fact_types:
            if ft not in self.factStreamList:
                self.factStreamList[ft] = list()
            self.factStreamList[ft].append((msg))

    def streamHandleFactStreamStop(self, msg):
        stream_id = msg.args.stream_id
        for (fact_type, streamers) in self.factStreamList.items():
            delList = list()
            for streamer in streamers:
                if (streamer.id == stream_id and
                        streamer.entity == msg.entity):
                    delList.append(streamer)

            for streamer in delList:
                streamers.remove(streamer)

    def streamHandleHypStreamStart(self, msg):
        hyp_types = msg.stream.args.hyp_types
        only_latest = msg.stream.args.only_latest

        if not only_latest:
            for ft in hyp_types:
                hypColumn = self.hyps.getColumn(ft)
                if hypColumn is not None:
                    for hyp in hypColumn:
                        result = {'hyp': hyp}
                        self.rpc.sendResponse(msg,
                                              RPCResponseStatus.ok,
                                              result=result)

        for ft in hyp_types:
            if ft not in self.hypStreamList:
                self.hypStreamList[ft] = list()
            self.hypStreamList[ft].append((msg))

    def streamHandleHypStreamStop(self, msg):
        stream_id = msg.args.stream_id
        for (hyp_type, streamers) in self.hypStreamList.items():
            delList = list()
            for streamer in streamers:
                if (streamer.id == stream_id and
                        streamer.entity == msg.entity):
                    delList.append(streamer)

            for streamer in delList:
                streamers.remove(streamer)

    def streamHandleChildFactStreamStart(self, msg):
        fact_id = msg.stream.args.fact_id
        object_id = msg.stream.args.object_id
        hyp_id = msg.stream.args.hyp_id
        fact_types = msg.stream.args.fact_types
        only_latest = msg.stream.args.only_latest

        if not only_latest:
            for ft in fact_types:
                factColumn = self.facts.getColumn(ft)
                if factColumn is not None:
                    for fact in factColumn:
                        if (object_id is not None and
                                object_id not in fact.parentObjects):
                            continue
                        elif(fact_id is not None and
                                fact_id not in fact.parentFacts):
                            continue
                        elif(hyp_id is not None and
                                hyp_id not in fact.parentHyps):
                            continue
                        result = {'fact': fact}
                        self.rpc.sendResponse(msg,
                                              RPCResponseStatus.ok,
                                              result=result)
        for ft in fact_types:
            if ft not in self.factStreamList:
                self.factStreamList[ft] = list()
            self.factStreamList[ft].append(msg)

    def streamHandleChildFactStreamStop(self, msg):
        self.streamHandleFactStreamStop(msg)

    def streamHandleChildHypStreamStart(self, msg):
        fact_id = msg.stream.args.fact_id
        object_id = msg.stream.args.object_id
        hyp_id = msg.stream.args.hyp_id
        types = msg.stream.args.types
        only_latest = msg.stream.args.only_latest

        if not only_latest:
            for ft in types:
                hypColumn = self.hyps.getColumn(ft)
                if hypColumn is not None:
                    for hyp in hypColumn:
                        if (object_id is not None and
                                object_id not in hyp.parentObjects):
                            continue
                        elif(fact_id is not None and
                                fact_id not in hyp.parentFacts):
                            continue
                        elif(hyp_id is not None and
                                hyp_id not in hyp.parentHyps):
                            continue
                        result = {'hyp': hyp}
                        self.rpc.sendResponse(msg,
                                              RPCResponseStatus.ok,
                                              result=result)
        for ft in types:
            if ft not in self.hypStreamList:
                self.hypStreamList[ft] = list()
            self.hypStreamList[ft].append(msg)

    def streamHandleChildHypStreamStop(self, msg):
        self.streamHandleHypStreamStop(msg)

    def streamHandleChildObjectStreamStart(self, msg):
        fact_id = msg.stream.args.fact_id
        hyp_id = msg.stream.args.hyp_id
        object_id = msg.stream.args.object_id
        only_latest = msg.stream.args.only_latest

        if not only_latest:
            for obj in self.objects:
                if (object_id is not None and
                        object_id not in obj.parentObjects):
                    continue
                elif(fact_id is not None and
                        fact_id not in obj.parentFacts):
                    continue
                elif(hyp_id is not None and
                        hyp_id not in obj.parentHyps):
                    continue
                result = {'object': obj}
                self.rpc.sendResponse(msg,
                                      RPCResponseStatus.ok,
                                      result=result)

        self.objectStreamList.append(msg)

    def streamHandleChildObjectStreamStop(self, msg):
        stream_id = msg.args.stream_id
        delList = list()
        for streamer in self.objectStreamList:
            if (streamer.id == stream_id and
                    streamer.entity == msg.entity):
                delList.append(streamer)

        for streamer in delList:
            self.objectStreamList.remove(streamer)
