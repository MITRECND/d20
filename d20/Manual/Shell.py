import sys
import cmd
import collections
import collections.abc
import datetime
import copy
import yaml
import os.path
from builtins import input
from collections import OrderedDict
from texttable import Texttable
from typing import Optional, Dict, Tuple, Union, List

from d20.Manual.Exceptions import NotFoundError
from d20.Manual.Facts import Fact
from d20.Manual.Facts.Fields import (SimpleField,
                                     NumericalField,
                                     StrOrBytesField)
from d20.Manual.BattleMap import FactTable, FileObject
from d20.Manual.GameMaster import GameMaster


def tsTodt(input: float) -> str:
    dt = datetime.datetime.utcfromtimestamp(input).\
        strftime('%Y-%m-%d %H:%M:%S.%f UTC')
    return dt


def prettyTable(rows: List, maxChars: int = 250,
                debug: bool = False) -> str:
    headers = rows[0]._fields

    table: Texttable = Texttable()
    table.set_deco(Texttable.HEADER | Texttable.VLINES)
    table.set_max_width(maxChars)
    table.header(headers)

    for row in rows:
        table.add_row(list(row))

    return table.draw()


def prettyList(data: Dict, debug: bool = False) -> str:
    """Function which takes a dict and prints out data into a prettyish table
    """
    if len(data) == 0:
        return "None"

    table: str = ""
    hwidth: int = len(max(list(data.keys()), key=lambda x: len(x)))
    if debug:
        print(hwidth)
    for key, value in list(data.items()):
        filler: int = len(key) - hwidth
        if (isinstance(
                value,
                collections.abc.Iterable) and not isinstance(value, str)):
            table += "%s %*s\n" % (key, filler, '')
            for d in value:
                table += "%*s %*s%s\n" % (len(key), '', filler, '', d)
        else:
            table += "%s %*s= %s\n" % (key, filler, '',  value)

    return table


def askPrompt(prompt: str = "Are you sure?") -> bool:
    while 1:
        resp = input("%s (y/n) " % (prompt))
        if resp.lower() in ['y', 'yes']:
            return True
        elif resp.lower() in ['n', 'no']:
            return False
        else:
            print("Invalid Response")


def listObjects(gm: GameMaster) -> str:
    objectMetadata: Tuple = collections.namedtuple('objectMetadata',
                                                   ['id',
                                                    'creator',
                                                    'created',
                                                    'filename'])
    rows: List[Tuple] = []
    for obj in gm.objects:
        created: str = tsTodt(obj._created_)
        filename: str = obj.metadata.get('filename', '')
        md: Tuple = objectMetadata(str(obj.id), obj._creator_, created,
                                   filename)
        rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No objects found\n"


def listFacts(gm: GameMaster) -> str:
    factMetadata: Tuple = collections.namedtuple('factMetadata',
                                                 ['id',
                                                  'type',
                                                  'creator',
                                                  'created'])
    rows: List[Tuple] = []
    for (factType, factColumn) in gm.facts.items():
        for fact in factColumn:
            created: str = tsTodt(fact.created)
            md: Tuple = factMetadata(str(fact.id), factType,
                                     fact.creator, created)
            rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No facts found\n"


def listHyps(gm: GameMaster) -> str:
    hypMetadata: Tuple = collections.namedtuple('hypMetadata',
                                                ['id',
                                                 'type',
                                                 'creator',
                                                 'created'])
    rows: List[Tuple] = []
    for (hypType, hypColumn) in gm.hyps.items():
        for hyp in hypColumn:
            created: str = tsTodt(hyp.created)
            md: Tuple = hypMetadata(str(hyp.id), hypType,
                                    hyp.creator, created)
            rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No hyps found\n"


def createObjectsList(typ: str, gm: GameMaster,
                      source: Union[Fact, FileObject]) -> str:
    objectMetadata: Tuple = collections.namedtuple('objectMetadata',
                                                   ['id',
                                                    'creator',
                                                    'created',
                                                    'filename'])
    rows: List[Tuple] = []
    for objid in getattr(source, '%sObjects' % (typ)):
        obj: FileObject = gm.objects[objid]
        created: str = tsTodt(obj._created_)
        filename: str = obj.metadata.get('filename', '')
        md: Tuple = objectMetadata(str(obj.id), obj._creator_, created,
                                   filename)
        rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


def createFactsList(typ: str, gm: GameMaster,
                    source: Union[Fact, FileObject]) -> str:
    factMetadata: Tuple = collections.namedtuple('factMetadata',
                                                 ['id',
                                                  'type',
                                                  'creator',
                                                  'created'])
    rows: List[Tuple] = []
    for (factType, factColumn) in gm.facts.items():
        for fact in factColumn:
            if fact.id in getattr(source, '%sFacts' % (typ)):
                created: str = tsTodt(fact.created)
                md: Tuple = factMetadata(str(fact.id), factType,
                                         fact.creator, created)
                rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


def createHypsList(typ: str, gm: GameMaster,
                   source: Union[Fact, FileObject]) -> str:
    hypMetadata: Tuple = collections.namedtuple('hypMetadata',
                                                ['id',
                                                 'type',
                                                 'creator',
                                                 'created'])
    rows: List[Tuple] = []
    for (hypType, hypColumn) in gm.hyps.items():
        for hyp in hypColumn:
            if hyp.id in getattr(source, '%sHyps' % (typ)):
                created: str = tsTodt(hyp.created)
                md: Tuple = hypMetadata(str(hyp.id), hypType,
                                        hyp.creator, created)
                rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


class BaseCmd(cmd.Cmd):
    def __init__(self, gameMaster: GameMaster,
                 depthList: Optional[List] = None):
        super().__init__()
        self.gm: GameMaster = gameMaster
        if depthList is None:
            self.depthList = []
        else:
            self.depthList = depthList

        self.backTo: Union[bool, int] = False

    def precmd(self, line: str) -> str:
        if line == 'EOF':
            self.do_exit('')

        return line

    def do_exit(self, arg) -> None:
        """Exit the shell"""
        sys.stdout.write('\n')
        exit(0)

    def do_save(self, arg: Optional[str]) -> None:
        """Save the state"""

        if arg:
            filename: str = arg
        elif self.gm.options:
            filename = self.gm.options.statefile
        else:
            sys.stdout.write("No save path was found\n")
            return

        if os.path.exists(filename) and not os.path.isfile(filename):
            sys.stdout.write("%s exists but is not a file\n" % (filename))
            return

        if os.path.isfile(filename):
            if not askPrompt("Overwrite existing file?"):
                sys.stdout.write("State not saved\n")
                return

        sys.stdout.write("Saving to %s ... " % (filename))
        sys.stdout.flush()
        save_state: Dict = self.gm.save()
        with open(filename, 'w') as f:
            f.write(yaml.dump(save_state))
        sys.stdout.write("Saved\n")

    def do_list(self, arg: Optional[str]) -> None:
        """List available objects, facts or hyps

        Syntax: list objects|facts|hyps
        """
        if arg == 'objects':
            output: str = listObjects(self.gm)
        elif arg == 'facts':
            output = listFacts(self.gm)
        elif arg == 'hyps':
            output = listHyps(self.gm)
        else:
            sys.stdout.write("list objects|facts|hyps\n")
            return

        sys.stdout.write(output)

    def do_back(self, arg: Optional[str]) -> bool:
        """Return to previous level"""
        if len(self.depthList) == 0:
            sys.stdout.write("Already at root\n")
            return False

        if arg is not None and len(arg) > 0:
            if arg == 'root':
                self.backTo = True
            else:
                try:
                    self.backTo = int(arg)
                except Exception:
                    sys.stdout.write("Unexpected value to back\n")
                    return False

        return True

    def _parse_bc(self) -> List[Tuple[int, str, int]]:
        bc: List[Tuple[int, str, int]] = list()
        for i, item in enumerate(self.depthList):
            if isinstance(item, FileObject):
                t = 'object'
            elif isinstance(item, Fact):
                if item.tainted:
                    t = 'hyp'
                else:
                    t = 'fact'
            else:
                raise RuntimeError("Unknown type")

            bc.append((i, t, item.id))

        return bc

    def do_bc(self, arg) -> None:
        """Print out breadcrumbs"""

        if len(self.depthList) == 0:
            sys.stdout.write("At root\n")
            return

        bc: List[Tuple[int, str, int]] = self._parse_bc()

        for (bcid, bctype, itemid) in bc:
            sys.stdout.write("%d - %s %d\n" % (bcid, bctype, itemid))

    def checkBackTo(self, downBackTo: Union[int, bool]) -> bool:
        if downBackTo is True:
            self.backTo = True
            return True
        elif downBackTo is not False:
            if ((len(self.depthList) - 1) == downBackTo):
                return False
            else:
                self.backTo = downBackTo
                return True
        return False

    def _find_object(self, obj_id: str) -> FileObject:
        try:
            objID = int(obj_id)
        except (ValueError, TypeError):
            raise

        inst: Optional[FileObject] = None
        for obj in self.gm.objects:
            if obj.id == objID:
                inst = obj
                break

        if inst is None:
            raise NotFoundError("No object by that id")

        return inst

    def do_object(self, arg: Optional[str]) -> bool:
        """Explore object with a given id"""

        if arg is None:
            sys.stdout.write("Object id required\n")
            return False

        try:
            inst: FileObject = self._find_object(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Object id must be an integer value")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            objcmd: ObjectCmd = ObjectCmd(self.gm, inst,
                                          copy.deepcopy(self.depthList))
            objcmd.cmdloop()
            return self.checkBackTo(objcmd.backTo)

        return False

    def _find_fact(self, fact_id: str) -> Fact:
        try:
            factID: int = int(fact_id)
        except (ValueError, TypeError):
            raise

        inst: Optional[Fact] = None
        for (factType, factColumns) in self.gm.facts.items():
            for fact in factColumns:
                if fact.id == factID:
                    inst = fact
                    break

        if inst is None:
            raise NotFoundError("No fact by that id")

        return inst

    def do_fact(self, arg: Optional[str]) -> bool:
        """Explore fact with a given id"""

        if arg is None:
            sys.stdout.write("Fact id required\n")
            return False

        try:
            inst: Fact = self._find_fact(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Fact id must be integer value\n")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            factcmd: FactCmd = FactCmd(self.gm, inst,
                                       copy.deepcopy(self.depthList))
            factcmd.cmdloop()
            return self.checkBackTo(factcmd.backTo)

        return False

    def _find_hyp(self, hyp_id: str) -> Fact:
        try:
            hypID = int(hyp_id)
        except (ValueError, TypeError):
            raise

        inst: Optional[Fact] = None
        for (hypType, hypColumns) in self.gm.hyps.items():
            for hyp in hypColumns:
                if hyp.id == hypID:
                    inst = hyp
                    break

        if inst is None:
            raise NotFoundError("No hyp by that id")

        return inst

    def do_hyp(self, arg: Optional[str]) -> bool:
        """Explore hyp with a given id"""

        if arg is None:
            sys.stdout.write("Hyp id required\n")
            return False

        try:
            inst: Fact = self._find_hyp(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Hyp id must be integer value")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            hypcmd: HypCmd = HypCmd(self.gm, inst,
                                    copy.deepcopy(self.depthList))
            hypcmd.cmdloop()
            return self.checkBackTo(hypcmd.backTo)

        return False

    def run(self) -> None:
        while 1:
            try:
                self.cmdloop()
            except KeyboardInterrupt:
                sys.stdout.write('\n')
                continue
            break


class ShellCmd(BaseCmd):
    def __init__(self, gameMaster: GameMaster) -> None:
        super().__init__(gameMaster)
        self.prompt: str = "d20 > "

    def do_object(self, arg: Optional[str]):
        """Explore an object with a given id"""
        super().do_object(arg)

    def do_fact(self, arg: Optional[str]):
        """Explore a fact with a given id"""
        super().do_fact(arg)

    def do_hyp(self, arg: Optional[str]):
        """Explore a hyp with a given id"""
        super().do_hyp(arg)


class ObjectCmd(BaseCmd):
    def __init__(self, gameMaster: GameMaster, obj: FileObject,
                 depthList: Optional[List] = None) -> None:
        super().__init__(gameMaster, depthList)
        # Append object to depth list
        self.depthList.append(obj)
        self.prompt: str = "object %d > " % (obj.id)
        self.obj: FileObject = obj

    def write_list(self, out: str) -> None:
        sys.stdout.write("\nObject %d:\n" % (self.obj.id))
        sys.stdout.write("--------------\n")
        sys.stdout.write(out)
        sys.stdout.write("--------------\n\n")

    def do_metadata(self, arg) -> None:
        """Print metadata about object"""
        out = prettyList(self.obj.metadata)
        self.write_list(out)

    def do_info(self, arg) -> None:
        """Print basic info about object"""
        created: str = tsTodt(self.obj._created_)
        out: str = prettyList({'id': self.obj.id,
                               'creator': self.obj._creator_,
                               'created': created})
        self.write_list(out)

    def do_parents(self, arg) -> None:
        """Print out parents of this object"""

        parentObjects: str = createObjectsList('parent', self.gm, self.obj)
        sys.stdout.write("Parent Objects:\n%s\n" % (parentObjects))

        parentFacts: str = createFactsList('parent', self.gm, self.obj)
        sys.stdout.write("Parent Facts:\n%s\n" % (parentFacts))

        parentHyps: str = createHypsList('parent', self.gm, self.obj)
        sys.stdout.write("Parent Hyps: \n%s\n" % (parentHyps))

    def do_children(self, args) -> None:
        """Print out children of this object"""

        childObjects: str = createObjectsList('child', self.gm, self.obj)
        sys.stdout.write("Child Objects:\n%s\n" % (childObjects))

        childFacts: str = createFactsList('child', self.gm, self.obj)
        sys.stdout.write("Child Facts:\n%s\n" % (childFacts))

        childHyps: str = createHypsList('child', self.gm, self.obj)
        sys.stdout.write("Child Hyps:\n%s\n" % (childHyps))

    def _find_items(self, data: FactTable, children: List[int]) -> List[Tuple]:
        itemMetadata: Tuple = collections.namedtuple('itemMetadata',
                                                     ['id',
                                                      'type',
                                                      'creator',
                                                      'created'])
        rows: List[Tuple] = []
        for (itemType, itemColumn) in data.items():
            for item in itemColumn:
                if item.id in children:
                    created: str = tsTodt(item.created)
                    md: Tuple = itemMetadata(str(item.id), itemType,
                                             item.creator, created)
                    rows.append(md)

        return rows

    def _do_items(self, _type: str,
                  data: FactTable,
                  children: List[int]
                  ) -> None:
        """Print items related to this object"""
        rows: List[Tuple] = self._find_items(data, children)

        if len(rows) > 0:
            out: str = prettyTable(rows)
            sys.stdout.write("\n%s\n" % (out))
        else:
            sys.stdout.write('No %s associated with object\n' % (_type))

    def do_facts(self, arg) -> None:
        """Print facts related to this object"""
        self._do_items("facts", self.gm.facts, self.obj.childFacts)

    def do_hyps(self, arg) -> None:
        """Print hyps related to this object"""
        self._do_items("hyps", self.gm.hyps, self.obj.childHyps)


class FactHypBaseCmd(BaseCmd):
    def __init__(self, _type: str, gameMaster: GameMaster, item: Fact,
                 depthList: Optional[List] = None) -> None:
        super().__init__(gameMaster, depthList)
        if item.id is not None:
            # Append item to depth list
            self._type: str = _type
            self.depthList.append(item)
            self.prompt: str = "%s %d > " % (self._type, item.id)
            self.item: Fact = item
        else:
            sys.stdout.write("Something went wrong, Fact had no ID\n")

    def write_list(self, out: str) -> None:
        if self.item.id is not None:
            sys.stdout.write("\n%s %d:\n" % (self._type.capitalize(),
                                             self.item.id))
            sys.stdout.write("--------------\n")
            sys.stdout.write(out)
            sys.stdout.write("--------------\n\n")
        else:
            sys.stdout.write("Something went wrong, Fact had no ID\n")

    def _find_info(self) -> OrderedDict:
        created: str = tsTodt(self.item.created)
        item_info: OrderedDict = collections.OrderedDict([
                        ('id', self.item.id),
                        ('type', self.item._type),
                        ('creator', self.item.creator),
                        ('created', created)])

        if self.item._fields_:
            for fieldName in self.item._fields_:
                descriptor = getattr(self.item, '_%s__' % fieldName)
                if (isinstance(descriptor, SimpleField) or
                        isinstance(descriptor, NumericalField) or
                        isinstance(descriptor, StrOrBytesField)):
                    try:
                        item_info[fieldName] = descriptor.getShell()
                    except AttributeError:
                        item_info[fieldName] = None
                else:
                    if 'fields' not in item_info:
                        item_info['fields'] = list()
                    item_info['fields'].append(fieldName)

            return item_info

        else:
            raise Exception

    def do_info(self, arg) -> None:
        """Print info about item"""
        item_info: OrderedDict = self._find_info()
        out: str = prettyList(item_info)
        self.write_list(out)

    def do_parents(self, arg) -> None:
        """Print out parents of this item"""

        parentObjects: str = createObjectsList('parent', self.gm, self.item)
        sys.stdout.write("Parent Objects:\n%s\n" % (parentObjects))

        parentFacts: str = createFactsList('parent', self.gm, self.item)
        sys.stdout.write("Parent Facts:\n%s\n" % (parentFacts))

        parentHyps: str = createHypsList('parent', self.gm, self.item)
        sys.stdout.write("Parent Hyps:\n%s\n" % (parentHyps))

    def do_children(self, args) -> None:
        """Print out children of this item"""

        childObjects: str = createObjectsList('child', self.gm, self.item)
        sys.stdout.write("Child Objects:\n%s\n" % (childObjects))

        childFacts: str = createFactsList('child', self.gm, self.item)
        sys.stdout.write("Child Facts:\n%s\n" % (childFacts))

        childHyps: str = createHypsList('child', self.gm, self.item)
        sys.stdout.write("Child Hyps:\n%s\n" % (childHyps))

    def do_fields(self, arg) -> None:
        """Print out the names of available fields"""
        if self.item._fields_ and len(self.item._fields_) > 0:
            for name in self.item._fields_:
                sys.stdout.write("%s\n" % (name))
        else:
            sys.stdout.write("No fields available\n")

    def do_get(self, arg: Optional[str]) -> None:
        """Print out value of a given field"""
        if self.item._fields_ is None or arg not in self.item._fields_:
            sys.stdout.write("No field by that name\n")
            return

        descriptor = getattr(self.item, '_%s__' % arg)

        try:
            output = descriptor.getShell()
        except AttributeError:
            output = "%s field was unset/undefined" % (arg)
        sys.stdout.write("%s\n" % (output))


class FactCmd(FactHypBaseCmd):
    def __init__(self, gameMaster: GameMaster, fact: Fact,
                 depthList: Optional[List] = None) -> None:
        super().__init__("fact", gameMaster, fact, depthList)


class HypCmd(FactHypBaseCmd):
    def __init__(self, gameMaster: GameMaster, fact: Fact,
                 depthList: Optional[List] = None) -> None:
        super().__init__("hyp", gameMaster, fact, depthList)

    def do_promote(self, arg: Optional[str]) -> bool:
        """Promote a hyp to a fact"""
        if askPrompt() and self.item.id is not None:
            promoted = self.gm.promoteHyp(self.item.id)
            if promoted.id is not None:
                sys.stdout.write("Hyp Promoted, fact id: %d\n"
                                 % (promoted.id))
                return self.do_back(arg)
        return False
