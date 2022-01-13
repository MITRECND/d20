import copy
import base64
import hashlib
import time
import threading
import os
import pathlib
import re
import sys
from io import BytesIO
from typing import (Dict, ItemsView, Iterator, List,
                    Match, Optional, Set, Type,
                    TypeVar, Union, ValuesView)

from d20.Manual.Exceptions import (DuplicateObjectError, NotFoundError)
from d20.Manual.Facts import (Fact, loadFact, RegisteredFacts)
from d20.Manual.Temporary import (
    TemporaryObjectOnDisk,
    TemporaryObjectStream
)


FactType = TypeVar('FactType', bound='FactTable')

# Fact and Hypothesis 'table' is organized using a python dict
# The dict pairs up a fact type from the RegisteredFacts
# list to a 'TableColumn'

# Each 'TableColumn' is a python list of 'Fact' types


class TableColumn(object):
    """A 'column' in the table

        This class uses a list to store the rows of a given column
    """

    def __init__(self, type: str, **kwargs) -> None:
        self._table_type: str = type
        self.column: List[Fact] = list()

    def append(self, fact: Fact) -> None:
        if fact._type != self._table_type:
            raise ValueError("Cannot add fact to column of different type")
        self.column.append(fact)

    def remove(self, fact: Fact) -> None:
        self.column.remove(fact)

    def __iter__(self) -> Iterator[Fact]:
        return self.column.__iter__()

    def index(self, value, start=0, stop=sys.maxsize) -> int:
        return self.column.index(value, start, stop)

    def __getitem__(self, *args, **kwargs):
        return self.column.__getitem__(*args, **kwargs)

    def tolist(self) -> List[Fact]:
        return copy.copy(self.column)

    def save(self) -> Dict:
        data = {
            'type': self._table_type,
            'column': [item.save() for item in self.column]
        }
        return data


class FactTable(object):
    """The table of facts

        This class is the master fact table of all facts for a given run
        and consists of multiple TableColumns, each column of a given fact type
    """
    _tainted_: bool = False

    def __init__(self, *args, **kwargs) -> None:
        self._ids: int = 0
        self._columns: Dict = dict()
        self._byId: Dict = dict()

    def __iter__(self) -> Iterator:
        return self._columns.__iter__()

    def items(self) -> ItemsView:
        return self._columns.items()

    def columns(self) -> ValuesView:
        return self._columns.values()

    @property
    def tainted(self) -> bool:
        return self._tainted_

    def findById(self, id: int) -> Optional[Fact]:
        """Return an item instance by a given id"""
        if id in self._byId.keys():
            return self._byId[id]
        else:
            return None

    def add(self, item: Fact, id: Optional[int] = None) -> int:
        """Add an item to the table

            This function adds an item to the table. If an id is not provided,
            it will create one. Ids should only be provided on load
        """

        if item.tainted != self.tainted:
            raise TypeError(("Attempt to add tainted/untainted item to "
                             "wrong table"))
        if item._type is None:
            raise TypeError(("Item was not created correctly - missing type"))

        self.addColumn(item._type)
        if id is None:
            id = self._ids
            self._ids += 1
        item._setID(id)
        self._columns[item._type].append(item)
        self._byId[id] = item

        return id

    def addColumn(self, _type: str) -> None:
        """Adds a TableColumn of the given type if not present"""
        if _type not in RegisteredFacts:
            raise ValueError("Unrecognized type")

        if _type not in self._columns.keys():
            self._columns[_type] = TableColumn(_type)

    def getColumn(self, _type: str) -> Optional[TableColumn]:
        """Returns a TableColumn of the given type"""
        if _type not in RegisteredFacts:
            raise ValueError("Unrecognized type")

        if _type not in self._columns.keys():
            return None
        else:
            return self._columns[_type]

    def hasColumn(self, _type: str) -> bool:
        """Returns a boolean whether a TableColumn for the given type exists"""
        if _type not in RegisteredFacts:
            raise ValueError("Unrecognized type")

        if _type in self._columns.keys():
            return True

        return False

    def save(self) -> Dict:
        data = {
            'ids': self._ids,
            'columns': {
                _type: column.save()
                for (_type, column) in self._columns.items()
            }
        }
        return data

    @classmethod
    def load(cls: Type[FactType], data: Dict) -> FactType:
        ft = cls()
        ft._ids = data['ids']
        for (_type, column) in data['columns'].items():
            for item in column['column']:
                loaded_item = loadFact(item)
                ft.add(loaded_item, loaded_item.id)
        return ft


class HypothesisTable(FactTable):
    _tainted_: bool = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def remove(self, hyp_id: int) -> Fact:
        item: Optional[Fact] = self.findById(hyp_id)
        if item is None:
            raise NotFoundError("No hyp by that id")
        del self._byId[hyp_id]
        self._columns[item._type].remove(item)
        return item


class FileObject(object):
    """Class representing an 'object'

        This class represents an object in the framework which is usually some
        binary object data

        Args:
            metadata, _metadata_: The metdata associated with this object
            encoding: The str encoding to use when converting to bytes
            _creator_: The creator of this object
            _created_: The timestamp when this object was created
            _parentObjects_: A list of id's of 'parent' objects
            _parentFacts_: A list of id's of 'parent' facts
            _parentHyps_: A list of id's of 'parent' hyp's
            _childObjects_: A list of id's of 'child' objects
            _childFacts_: A list of id's of 'child' facts
            _childHyps_: A list of id's of 'child' hyp's
    """

    # TODO FIXME this approach is naive, need better detection of
    # Windows paths
    isWindowsRegex = re.compile(r'^[a-zA-Z]:\\')

    def __init__(self, data: Union[bytes, bytearray, str], id: int, **kwargs):
        self._id: int = id
        self._data: Union[bytes, bytearray, str] = data
        self._size: Optional[int] = None
        self._metadata: Dict = dict()
        self._creator_: Optional[str] = None
        self._created_: float = time.time()
        self._ondisk_: Optional[TemporaryObjectOnDisk] = None
        self._stream_: Optional[TemporaryObjectStream] = None
        self._encoding: str = 'utf-8'
        self._parentObjects_: Set[int] = set()
        self._parentFacts_: Set[int] = set()
        self._parentHyps_: Set[int] = set()
        self._childObjects_: Set[int] = set()
        self._childFacts_: Set[int] = set()
        self._childHyps_: Set[int] = set()

        for (name, value) in kwargs.items():
            if name == '_metadata_':
                if value is not None:
                    self._metadata = value
            elif name == 'metadata':
                if value is not None:
                    for (mname, mvalue) in value.items():
                        self.add_metadata(mname, mvalue)
            elif name == '_creator_':
                self._creator_ = value
            elif name == '_created_':
                self._created_ = value
            elif name == 'encoding':
                if value is not None:
                    self._encoding = value
            elif name == '_parentObjects_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("parent objects must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentObjects_ = set(value)
            elif name == '_parentFacts_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("parent facts must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentFacts_ = set(value)
            elif name == '_parentHyps_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("parent hypotheses must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._parentHyps_ = set(value)
            elif name == '_childObjects_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("child objects must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childObjects_ = set(value)
            elif name == '_childFacts_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("child facts must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childFacts_ = set(value)
            elif name == '_childHyps_':
                if value is not None:
                    try:
                        if not all(isinstance(i, int) for i in list(value)):
                            raise TypeError(("child hypotheses must be a "
                                             "list of ints"))
                    except TypeError:
                        raise
                    self._childHyps_ = set(value)
            else:
                pass  # TODO XXX

        if not isinstance(self._data, bytes):
            if isinstance(self._data, bytearray):
                try:
                    self._data = bytes(self._data)
                except Exception:
                    raise TypeError(
                        "Unable to convert provided 'bytearray' into 'bytes'"
                    )
            elif isinstance(self._data, str):
                try:
                    self._data = bytes(self._data, self._encoding)
                except Exception:
                    raise TypeError("Unable to convert provided data into"
                                    " 'bytes' using %s encoding" %
                                    (self._encoding))
            else:
                raise TypeError("Expected a bytes or str type")

        self._hash = hashlib.sha256(self._data).hexdigest()
        self._size = len(self._data)

    @property
    def id(self) -> int:
        return self._id

    @property
    def parentObjects(self) -> List[int]:
        return list(self._parentObjects_)

    def addParentObject(self, parent: int) -> None:
        self._parentObjects_.add(parent)

    def remParentObject(self, parent: int) -> None:
        self._parentObjects_.discard(parent)

    @property
    def parentFacts(self) -> List[int]:
        return list(self._parentFacts_)

    def addParentFact(self, parent: int) -> None:
        self._parentFacts_.add(parent)

    def remParentFact(self, parent: int) -> None:
        self._parentFacts_.discard(parent)

    @property
    def parentHyps(self) -> List[int]:
        return list(self._parentHyps_)

    def addParentHyp(self, parent: int) -> None:
        self._parentHyps_.add(parent)

    def remParentHyp(self, parent: int) -> None:
        self._parentHyps_.discard(parent)

    @property
    def childObjects(self) -> List[int]:
        return list(self._childObjects_)

    def addChildObject(self, child: int) -> None:
        self._childObjects_.add(child)

    def remChildObject(self, child: int) -> None:
        self._childObjects_.discard(child)

    @property
    def childFacts(self) -> List[int]:
        return list(self._childFacts_)

    def addChildFact(self, child: int) -> None:
        self._childFacts_.add(child)

    def remChildFact(self, child: int) -> None:
        self._childFacts_.discard(child)

    @property
    def childHyps(self) -> List[int]:
        return list(self._childHyps_)

    def addChildHyp(self, child: int) -> None:
        self._childHyps_.add(child)

    def remChildHyp(self, child: int) -> None:
        self._childHyps_.discard(child)

    def __addMetadataFilename(self, filename: str):
        isWindows: Optional[Match[str]] = self.isWindowsRegex.match(filename)
        try:
            if isWindows:
                path: Union[pathlib.PureWindowsPath, pathlib.PurePosixPath] = \
                    pathlib.PureWindowsPath(filename)
            else:
                path = pathlib.PurePosixPath(filename)

            self._metadata['filename'] = path.name
            self._metadata['filepath'] = str(path.parent)
        except Exception:
            self._metadata['filename'] = filename

    @property
    def metadata(self) -> Dict:
        """Returns a copy of the objects metadata"""
        return copy.deepcopy(self._metadata)

    def add_metadata(self, key: str, value: str) -> None:
        """Setter function to add metadata to object"""
        if key == 'filename':
            self.__addMetadataFilename(value)
        else:
            self._metadata[key] = value

    @property
    def hash(self) -> str:
        return self._hash

    @property
    def size(self) -> int:
        return self._size  # type: ignore

    @property
    def data(self) -> bytes:
        return self._data  # type: ignore

    @property
    def onDisk(self) -> str:
        """Function to return object on file system"""
        if self._ondisk_ is None:
            self._ondisk_ = TemporaryObjectOnDisk(self._id, self._data)
        return self._ondisk_.path

    @property
    def stream(self) -> BytesIO:
        """Function to return object as a data stream"""
        if isinstance(self._data, bytes) and self._stream_ is None:
            self._stream_ = TemporaryObjectStream(self._id, self._data)
        return self._stream_.stream  # type: ignore

    @property
    def _creationInfo(self) -> Dict:
        data = {'_creator_': self._creator_, '_created_': self._created_}

        return data

    @property
    def _internalInfo(self) -> Dict:
        data = {
            "_parentObjects_": self._parentObjects_,
            "_parentFacts_": self._parentFacts_,
            "_parentHyps_": self._parentHyps_,
            "_childObjects_": self._childObjects_,
            "_childFacts_": self._childFacts_,
            "_childHyps_": self._childHyps_,
            "encoding": self._encoding
        }
        return data

    @property
    def _coreInfo(self) -> Dict:
        data = {}
        if isinstance(self._data, bytes):
            data = {
                'id': self._id,
                'metadata': self._metadata,
                'hash': self._hash,
                'size': self._size,
                'data': base64.b64encode(self._data).decode("utf-8")
            }

        return data

    def save(self) -> Dict:
        data = self._creationInfo
        data.update(self._coreInfo)
        data.update(self._internalInfo)
        return data

    @staticmethod
    def load(data) -> 'FileObject':
        data['data'] = base64.b64decode(data['data'])
        return FileObject(**data)


class ObjectList(object):
    """Master list of objects

        This class is a container of the objects being tracked by the framework

        Args:
            temporary: The temporary path for objects on disk
    """

    def __init__(self, *args, **kwargs):
        self.objects: List[FileObject] = list()
        self.__tmpbase_: Optional[str] = None
        self.__hashes_: Dict = dict()
        self.object_lock: threading.Lock = threading.Lock()

        for (name, value) in kwargs.items():
            if name == 'temporary':
                self.__tmpbase_ = os.path.join(value, 'objects')

        if (self.__tmpbase_ is not None
                and not os.path.exists(self.__tmpbase_)):
            os.path.mkdirs(self.__tmpbase_)

    def getObjectByData(self, data: bytes) -> Optional[FileObject]:
        hsh: str = hashlib.sha256(data).hexdigest()
        return self.getObjectByHash(hsh)

    def getObjectByHash(self, hsh: str) -> Optional[FileObject]:
        try:
            return self.__getitem__(self.__hashes_[hsh])
        except Exception:
            return None

    def addObject(self,
                  data: Union[bytes, bytearray, str],
                  **kwargs
                  ) -> FileObject:
        with self.object_lock:
            id: int = len(self.objects)
            obj: FileObject = FileObject(data, id, **kwargs)
            self.append(obj)

        return obj

    def append(self, file_object: FileObject) -> None:
        if not isinstance(file_object, FileObject):
            raise TypeError("Expected 'FileObject' type")

        if file_object.hash in self.__hashes_.keys():
            raise DuplicateObjectError("Object already exists in list")

        self.__hashes_[file_object.hash] = file_object.id
        self.objects.append(file_object)

    def __getitem__(self, key: int) -> FileObject:
        return self.objects.__getitem__(key)

    def __iter__(self) -> Iterator:
        return self.objects.__iter__()

    def __len__(self) -> int:
        return self.objects.__len__()

    def tolist(self) -> List[FileObject]:
        return copy.copy(self.objects)
