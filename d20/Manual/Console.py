import time
from collections.abc import Iterable
from enum import Enum
from types import SimpleNamespace
from typing import List, Dict, Optional, Collection, Union, Tuple, Generator

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

from d20.Manual.BattleMap import FileObject
from d20.Manual.Logger import logging, Logger
from d20.Manual.Exceptions import (ConsoleError, RPCTimeoutError,
                                   WaitTimeoutError)
from d20.Manual.Facts import resolveFacts, Fact
from d20.Manual.RPC import (RPCClient, RPCResponseStatus,
                            RPCCommands, RPCResponse,
                            RPCStreamCommands)
from d20.Manual.Temporary import PlayerDirectoryHandler
import d20.Manual.Trackers as Tracker


LOGGER: Logger = logging.getLogger(__name__)


class PlayerState(Enum):
    running = 0
    waiting = 1
    stopped = 2


class ConsoleInterface(object):
    """Base console class

        This class is the base console for NPCs and Players and provides
        convenience functions to make writing a player/npc easier

        Args:
            id: The id of this console/instance
            cloneID: If a player, the id of the clone
            directoryHandler: The handler for file system functions
            rpc_client: RPC Client instance
            config: The config for this console instance

    """
    def __init__(self, **kwargs) -> None:
        try:
            self._id: str = kwargs['id']
            self._cloneID: Optional[str] = kwargs.get('cloneID', None)
            self._directoryHandler: PlayerDirectoryHandler = \
                kwargs['directoryHandler']
            self._rpc: RPCClient = kwargs['rpc_client']
            self._async: SimpleNamespace = kwargs['asyncData']
            self._config_: Union[str, Dict, None] = kwargs.get('config', None)
        except KeyError:
            LOGGER.critical("Expected argument not passed to init",
                            exc_info=True)
            raise

        self._session: Optional[Session] = None
        self._sessionConfig: Dict = dict()
        self._sessionRetryConfig: Dict = dict()
        # Setup RPC handler for the console

    def __getSession(self, total: int = 5,
                     status_forcelist: Optional[Collection[int]] = None,
                     backoff_factor: float = 0.2,
                     method_whitelist: Optional[Collection[str]] =
                     Retry.DEFAULT_METHOD_WHITELIST,
                     **kwargs: str) -> Session:

        # XXX TODO Retry.DEFAULT_METHOD_WHITELIST is deprecated in favor
        # of Retry.DEFAULT_METHODS_ALLOWED and method_whitelist is deprecated
        # in favor of allowed_methods, both of which do not seem to exist in
        # the version of urllib that gets pulled in
        retryConfig: Retry = Retry(total=total,
                                   status_forcelist=status_forcelist,
                                   backoff_factor=backoff_factor,
                                   method_whitelist=method_whitelist,
                                   raise_on_redirect=False, **kwargs)

        session: Session = Session()

        proxies: Dict[str, str] = dict()
        if isinstance(self._config_, dict):
            if 'http_proxy' in self._config_:
                proxies['http'] = self._config_['http_proxy']
            if 'https_proxy' in self._config_:
                proxies['https'] = self._config_['https_proxy']

        if len(proxies.keys()) > 0:
            session.proxies = proxies

        for (key, value) in self._sessionConfig.items():
            try:
                setattr(session, key, value)
            except Exception:
                LOGGER.exception("Unable to configure session as expected")

        session.mount('http://', HTTPAdapter(max_retries=retryConfig))
        session.mount('https://', HTTPAdapter(max_retries=retryConfig))

        return session

    @property
    def async_(self) -> SimpleNamespace:
        """asyncio support data

            This property/method returns a data object that contains three
            elements:

            enabled(bool) - Whether asyncio support is enabled or not. Please
                check this variable before doing any further asyncio work

            In most cases, it is best for entities to create their own
            eventloop as they are running in their own thread, but in case
            asyncio objects related to main are needed, the following are
            also provided:

            eventloop(object) - The main eventloop
            eventwatcher(object) - The child watcher attached to the main event
                loop
        """
        return self._async

    @property
    def requests(self) -> Session:
        """Configured requests session

            This property/method returns a configured Session object
            making it easier to make web requests. See
            http://docs.python-requests.org/en/master/api/#request-sessions for
            more information
        """
        if self._session is None:
            self._session = self.__getSession(**self._sessionRetryConfig)
        return self._session

    def configureRequestsRetry(self, **kwargs) -> None:
        """Configuration options for the Retry class

            This function allows you to customize the behavior of the Retry
            object which is attached to the HTTPAdapter as part of the session
            configuration.
        """
        self._sessionRetryConfig = kwargs

    def configureRequestsSession(self, config: Dict) -> None:
        """Configuration options for Session object

            This function takes a dict with k/v pairs that coorespond to
            exposed properties of the Session object
        """
        if not isinstance(config, dict):
            raise TypeError("Expected dict type")

        # Check that fields at least exist
        session = Session()
        for key in config.keys():
            if getattr(session, key, None) is None:
                raise ValueError("Unable to find %s in requests Session"
                                 % (key))

        self._sessionConfig = config
        # Set old session to None so it will be recreated on next access
        self._session = None

    @property
    def myDirectory(self) -> str:
        """Returns entity's directory information"""
        return self._directoryHandler.myDir

    def createTempDirectory(self) -> str:
        """Creates and returns a temporary directory"""
        return self._directoryHandler.tempdir()

    def _noop(self) -> None:
        self._rpc.sendAndIgnore(command=RPCCommands.noop)

    def print(self, *args, **kwargs) -> None:
        """Prints out stuff, similar to python built-in print

            Entities should not use the built-in print since this provides
            more predictable results. In the future the built-in print/stdout
            may be supressed
        """
        self._rpc.sendAndIgnore(command=RPCCommands.print,
                                args={'args': args, 'kwargs': kwargs})

    def _addObject(self, object_data: bytes, creator: str,
                   parentObjects: Optional[List[FileObject]],
                   parentFacts: Optional[List[Fact]],
                   parentHyps: Optional[List[Fact]],
                   metadata: Optional[Dict],
                   encoding: Optional[str]) -> RPCResponse:
        """Adds an object to the object list

            Args:
                object_data: The data of the object

            Returns: The object id
        """
        if (parentObjects is not None
                and not isinstance(parentObjects, Iterable)):
            raise ValueError("parent objects must be a list")

        if (parentFacts is not None
                and not isinstance(parentFacts, Iterable)):
            raise ValueError("parent facts must be a list")

        if (parentHyps is not None
                and not isinstance(parentHyps, Iterable)):
            raise ValueError("parent hypotheses must be a list")

        resp: RPCResponse = self._rpc.sendAndWait(
            command=RPCCommands.addObject,
            args={'object_data': object_data,
                  'parentObjects': parentObjects,
                  'parentFacts': parentFacts,
                  'parentHyps': parentHyps,
                  'metadata': metadata,
                  'encoding': encoding,
                  'creator': creator})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp

    def _addFact(self, fact: Fact, creator: str,
                 require_parentage: bool = True) -> RPCResponse:
        """Adds an item to the fact table

            Args:
                fact: The fact to add to the table

            Returns: None

            Raises: ValueError if all parents are empty
        """

        if (require_parentage and
                (not fact.parentObjects
                 and not fact.parentFacts
                 and not fact.parentHyps)):
            raise ValueError("Fact's parentage must be populated")

        fact._creator_ = creator
        resp: RPCResponse = self._rpc.sendAndWait(command=RPCCommands.addFact,
                                                  args={'fact': fact})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp

    def _addHyp(self, hyp: Fact, creator: str,
                require_parentage: bool = True) -> RPCResponse:
        """Adds an item to the hypothesis table

            Args:
                hyp: The hyp to add to the table

            Returns: None

            Raises: ValueError if all parents are empty
        """

        if (require_parentage and
                (not hyp.parentObjects
                 and not hyp.parentFacts
                 and not hyp.parentHyps)):
            raise ValueError("Hyp's parentage must be populated")

        hyp._creator_ = creator
        hyp._taint()
        resp: RPCResponse = self._rpc.sendAndWait(command=RPCCommands.addHyp,
                                                  args={'hyp': hyp})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp


class BackStoryConsole(ConsoleInterface):
    """Object passed to backstories to interface with the game

        Args:
            id: The id of this console/instance
            directoryHandler: The handler for file system functions
            rpc_client: Instance of the RPCClient
            config: The config for this console instance
            backstorytracker: The internal tracker class for this backstory

    """
    def __init__(self, **kwargs):
        super().__init__(id=kwargs['id'],
                         directoryHandler=kwargs['directoryHandler'],
                         rpc_client=kwargs['rpc_client'],
                         asyncData=kwargs['asyncData'],
                         config=kwargs.get('config'))

        self.__tracker_: Tracker.BackStoryTracker = kwargs['tracker']

    @property
    def memory(self) -> Dict:
        """Property to store backstory-level memory"""
        return self.__tracker_.memory

    def addObject(self, object_data: bytes,
                  parentObjects: Optional[List[FileObject]] = None,
                  parentFacts: Optional[List[Fact]] = None,
                  parentHyps: Optional[List[Fact]] = None,
                  metadata: Dict = None, encoding: str = None) -> int:
        """Adds an object to the object list

            Args:
                object_data: The data of the object

            Returns: The object id
        """
        resp: RPCResponse = super()._addObject(object_data,
                                               self.__tracker_.name,
                                               parentObjects, parentFacts,
                                               parentHyps, metadata, encoding)

        return resp.result.object_id

    def addFact(self, fact: Fact) -> None:
        """Adds an item to the fact table

            Args:
                fact: The fact to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """
        super()._addFact(fact, self.__tracker_.name, require_parentage=False)

    def addHyp(self, hyp: Fact) -> None:
        """Adds an item to the hyp table

            Args:
                hyp: The hyp to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """
        super()._addHyp(hyp, self.__tracker_.name, require_parentage=False)


class NPCConsole(ConsoleInterface):
    """Object passed to npcs to interface with the game

        Args:
            id: The id of this console/instance
            directoryHandler: The handler for file system functions
            rpc_client: Instance of the RPCClient
            config: The config for this console instance
            npctracker: The internal tracker class for this npc

    """
    def __init__(self, **kwargs):
        super().__init__(id=kwargs['id'],
                         directoryHandler=kwargs['directoryHandler'],
                         rpc_client=kwargs['rpc_client'],
                         asyncData=kwargs['asyncData'],
                         config=kwargs.get('config'))

        self.__tracker_: Tracker.NPCTracker = kwargs['tracker']

    @property
    def memory(self) -> Dict:
        """Property to store npc-level memory"""
        return self.__tracker_.memory

    def addObject(self, object_data: bytes,
                  parentObjects: Optional[List[FileObject]] = None,
                  parentFacts: Optional[List[Fact]] = None,
                  parentHyps: Optional[List[Fact]] = None,
                  metadata: Dict = None, encoding: str = None) -> int:
        """Adds an object to the object list

            Args:
                object_data: The data of the object

            Returns: The object id
        """
        resp: RPCResponse = super()._addObject(object_data,
                                               self.__tracker_.name,
                                               parentObjects, parentFacts,
                                               parentHyps, metadata, encoding)

        return resp.result.object_id

    def addFact(self, fact: Fact) -> None:
        """Adds an item to the fact table

            Args:
                fact: The fact to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """
        super()._addFact(fact, self.__tracker_.name)

    def addHyp(self, hyp: Fact) -> None:
        """Adds an item to the hyp table

            Args:
                hyp: The hyp to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """
        super()._addHyp(hyp, self.__tracker_.name)


class PlayerConsole(ConsoleInterface):
    """Object passed to players to interace with the game

        Args:
            id: The id of this player
            clone_id: If a player, the id of the clone
            directoryHandler: The handler for file system functions
            config: The config for this console instance
            tracker: The internal tracker of a player
    """
    def __init__(self, **kwargs):
        super().__init__(id=kwargs['id'],
                         directoryHandler=kwargs['directoryHandler'],
                         rpc_client=kwargs['rpc_client'],
                         asyncData=kwargs['asyncData'],
                         cloneID=kwargs['clone_id'],
                         config=kwargs.get('config', None))

        self.__tainted_: bool = kwargs['tainted']
        self.__tracker_: Tracker.PlayerTracker = kwargs['tracker']

    @property
    def id(self) -> Tuple[str, Optional[str]]:
        return (self._id, self._cloneID)

    @property
    def memory(self) -> Dict:
        return self.__tracker_.memory

    @property
    def __clone_(self) -> Optional[str]:
        return self.__tracker_.clones[self._cloneID]

    @property
    def data(self) -> bytes:
        return self.__tracker_.cloneMemory[self._cloneID]

    def setWaiting(self) -> None:
        self.__tracker_.clones[self._cloneID] \
            ._state = PlayerState.waiting

    def setRunning(self) -> None:
        self.__tracker_.clones[self._cloneID] \
            ._state = PlayerState.running
        self.__tracker_.clones[self._cloneID] \
            ._turnStart = time.time()

    def getClones(self) -> None:
        pass

    def getObject(self, object_id: int):
        """Returns the object with the given id
        """
        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getObject,
                                args={'object_id': object_id})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.object

    def getAllObjects(self) -> List[FileObject]:
        """Returns a list of all objects
        """
        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getAllObjects)

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.object_list

    def getFact(self, factID: int) -> Fact:
        """Returns a specific fact based on id
        """
        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getFact,
                                args={'fact_id': factID})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.fact

    def getHyp(self, hypID: int) -> Fact:
        """Returns a specific hypothesis based on id
        """
        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getHyp,
                                args={'hyp_id': hypID})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.hyp

    def getAllFacts(self, fact_type: Union[str, List[str]]) -> List[Fact]:
        """Returns a list of all facts of a given type
        """

        if isinstance(fact_type, str):
            fact_type = [fact_type]

        fact_type = resolveFacts(*fact_type)

        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getAllFacts,
                                args={'fact_type': fact_type})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.fact_list

    def getAllHyps(self, hyp_type: Union[str, List[str]]) -> List[Fact]:
        """Returns a list of all hypotheses of a given type
        """

        if isinstance(hyp_type, str):
            hyp_type = [hyp_type]

        hyp_type = resolveFacts(*hyp_type)

        resp: RPCResponse = self._rpc.sendAndWait(
                                command=RPCCommands.getAllFacts,
                                args={'hyp_type': hyp_type})

        if resp.status == RPCResponseStatus.error:
            raise ConsoleError(resp.reason)

        return resp.result.hyp_list

    def _waitOn(self, stream_id: int) -> Generator[RPCResponse, None, None]:
        # Set the state to waiting before entering the loop
        # since the generator will block
        self.setWaiting()

        try:
            for msg in self._rpc.getStream(stream_id):
                try:
                    # Set the state to running while the player
                    # does stuff with the yielded info
                    self.setRunning()
                    yield msg
                finally:
                    # Ensure player state is set back to waiting
                    # in preparation for being blocked
                    self.setWaiting()
        finally:
            self._rpc.stopStream(stream_id)
            # Ensure player state is set back to running
            # after this function/generator exits
            self.setRunning()

    def waitOnFacts(self, facts: Union[str, List[str]],
                    only_latest: bool = False) -> Generator[Fact, None, None]:
        """Waits on facts until player breaks out of generator
        """

        if isinstance(facts, str):
            facts = [facts]
        facts = resolveFacts(*facts)

        stream_id: int = self._rpc.startStream(
                                command=RPCStreamCommands.factStream,
                                args={'fact_types': facts,
                                      'only_latest': only_latest})

        for msg in self._waitOn(stream_id):
            yield msg.result.fact

    def waitOnHyps(self, hyps: Union[str, List[str]],
                   only_latest: bool = False) -> Generator[Fact, None, None]:
        """Waits on hypotheses until player breaks out of generator
        """

        if isinstance(hyps, str):
            hyps = [hyps]
        hyps = resolveFacts(*hyps)

        stream_id: int = self._rpc.startStream(
                                    command=RPCStreamCommands.hypStream,
                                    args={'hyp_types': hyps,
                                          'only_latest': only_latest})

        for msg in self._waitOn(stream_id):
            yield msg.result.hyp

    def waitOnChildFacts(self, object_id: Optional[int] = None,
                         fact_id: Optional[int] = None,
                         hyp_id: Optional[int] = None,
                         facts: Union[str, List[str]] = None,
                         only_latest: bool = False
                         ) -> Generator[Fact, None, None]:
        """Wait on facts of given types, for a given object id, fact id, or
            hyp id until player breaks out of generator
        """

        if all(item is None for item in [object_id, fact_id, hyp_id]):
            raise ValueError(("One of object_id, fact_id, or hyp_id must "
                              "be used"))

        if sum(item is not None for item in [object_id, fact_id, hyp_id]) > 1:
            raise ValueError(("Only one of object id, fact_id, or hyp_id "
                              "may be used"))

        if facts is None:
            raise TypeError("'facts' is a required argument")

        if isinstance(facts, str):
            facts = [facts]
        facts = resolveFacts(*facts)

        stream_id: int = self._rpc.startStream(
            command=RPCStreamCommands.childFactStream,
            args={'object_id': object_id,
                  'fact_id': fact_id,
                  'hyp_id': hyp_id,
                  'fact_types': facts,
                  'only_latest': only_latest})

        for msg in self._waitOn(stream_id):
            yield msg.result.fact

    def waitOnChildHyps(self, object_id: Optional[int] = None,
                        fact_id: Optional[int] = None,
                        hyp_id: Optional[int] = None,
                        types: Union[str, List[str]] = None,
                        only_latest: bool = False
                        ) -> Generator[Fact, None, None]:
        """Wait on hypotheses of given types, for a given object id, fact id,
            or hypothesis id until player breaks out of generator
        """

        if all(item is None for item in [object_id, fact_id, hyp_id]):
            raise ValueError(("One of  object_id, fact_id, or hyp_id must "
                              "be used"))

        if sum(item is not None for item in [object_id, fact_id, hyp_id]) > 1:
            raise ValueError(("Only one of object id, fact_id, or hyp_id "
                              "maybe used"))

        if types is None:
            raise TypeError("'types' is a required argument")

        if isinstance(types, str):
            types = [types]
        types = resolveFacts(*types)

        stream_id: int = self._rpc.startStream(
            command=RPCStreamCommands.childHypStream,
            args={'object_id': object_id,
                  'fact_id': fact_id,
                  'hyp_id': hyp_id,
                  'types': types,
                  'only_latest': only_latest})

        for msg in self._waitOn(stream_id):
            yield msg.result.hyp

    def waitOnChildObjects(self, object_id: Optional[int] = None,
                           fact_id: Optional[int] = None,
                           hyp_id: Optional[int] = None,
                           only_latest: bool = False
                           ) -> Generator[FileObject, None, None]:
        """Wait on child objects of a given object id, fact id, or
            hypothesis id
        """

        if all(item is None for item in [object_id, fact_id, hyp_id]):
            raise ValueError(("One of  object_id, fact_id, or hyp_id must "
                              "be used"))

        if sum(item is not None for item in [object_id, fact_id, hyp_id]) > 1:
            raise ValueError(("Only one of object id, fact_id, or hyp_id "
                              "maybe used"))

        stream_id: int = self._rpc.startStream(
            command=RPCStreamCommands.childObjectStream,
            args={'object_id': object_id,
                  'fact_id': fact_id,
                  'hyp_id': hyp_id,
                  'only_latest': only_latest})

        for msg in self._waitOn(stream_id):
            yield msg.result.object

    def waitTillFact(self, fact_type: Union[str, List[str]],
                     last_fact: Optional[int] = None,
                     timeout: int = 0) -> None:
        """Waits up till timeout (default forever) for fact to show up

            If timeout is reached will return None
        """
        if isinstance(fact_type, str):
            fact_type = [fact_type]

        fact_type = resolveFacts(*fact_type)

        msg_id: int = self._rpc.sendMessage(command=RPCCommands.waitTillFact,
                                            args={'fact_type': fact_type,
                                                  'last_fact': last_fact})

        self.setWaiting()
        try:
            resp = self._rpc.waitForResponse(msg_id, timeout)
        except RPCTimeoutError:
            pass
        self.setRunning()

        if resp is not None:
            return resp.result.fact
        else:
            raise WaitTimeoutError()
            # TODO FIXME XXX

    def addObject(self, object_data: bytes,
                  parentObjects: Optional[List[FileObject]] = None,
                  parentFacts: Optional[List[Fact]] = None,
                  parentHyps: Optional[List[Fact]] = None,
                  metadata: Dict = None, encoding: str = None) -> int:
        """Adds an object to the object list

            returns the object id
        """
        resp = super()._addObject(object_data,
                                  self.__tracker_.name,
                                  parentObjects, parentFacts, parentHyps,
                                  metadata, encoding)

        return resp.result.object_id

    def addFact(self, fact: Fact, yesreally: bool = False) -> None:
        """Adds an item to the fact table

            Args:
                fact - The fact object to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """

        if self.__tainted_ and not yesreally:
            raise ValueError(("Adding a fact based on a hypothesis, requires "
                              "the 'yesreally' argument to be set to True"))

        super()._addFact(fact, self.__tracker_.name)

    def addHyp(self, hyp: Fact) -> None:
        """Adds an item to the hyp table

            Args:
                hyp - The hyp object to add to the table

            Returns: None

            Raises: ValueError if object id and reference are not set
        """

        hyp._taint()
        super()._addHyp(hyp, self.__tracker_.name)
