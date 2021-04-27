import sys
import shlex
import cmd
import collections
import datetime
import copy
import yaml
import os.path
from builtins import input
from texttable import Texttable

from d20.Manual.Exceptions import NotFoundError
from d20.Manual.Facts import Fact
from d20.Manual.Facts.Fields import (SimpleField,
                                     NumericalField,
                                     StrOrBytesField)
from d20.Manual.BattleMap import FileObject


def tsTodt(input):
    dt = datetime.datetime.utcfromtimestamp(input).\
        strftime('%Y-%m-%d %H:%M:%S.%f UTC')
    return dt


def prettyTable(rows, maxChars=250, debug=False):
    headers = rows[0]._fields

    table = Texttable()
    table.set_deco(Texttable.HEADER | Texttable.VLINES)
    table.set_max_width(maxChars)
    table.header(headers)

    for row in rows:
        table.add_row(list(row))

    return table.draw()


def prettyList(data, debug=False):
    """Function which takes a dict and prints out data into a prettyish table
    """
    if len(data) == 0:
        return "None"

    table = ""
    hwidth = len(max(list(data.keys()), key=lambda x: len(x)))
    if debug:
        print(hwidth)
    for key, value in list(data.items()):
        filler = len(key) - hwidth
        if (isinstance(
                value,
                collections.Iterable) and not isinstance(value, str)):
            table += "%s %*s\n" % (key, filler, '')
            for d in value:
                table += "%*s %*s%s\n" % (len(key), '', filler, '', d)
        else:
            table += "%s %*s= %s\n" % (key, filler, '',  value)

    return table


def parse_args(arg_string):
    try:
        args = shlex.split(arg_string)
        return args
    except Exception:
        return None


def askPrompt(prompt="Are you sure?"):
    while 1:
        resp = input("%s (y/n) " % (prompt))
        if resp.lower() in ['y', 'yes']:
            return True
        elif resp.lower() in ['n', 'no']:
            return False
        else:
            print("Invalid Response")


def list_objects(gm):
    objectMetadata = collections.namedtuple('objectMetadata',
                                            ['id',
                                             'creator',
                                             'created',
                                             'filename'])
    rows = []
    for obj in gm.objects:
        created = tsTodt(obj._created_)
        filename = obj.metadata.get('filename', '')
        md = objectMetadata(str(obj.id), obj._creator_, created, filename)
        rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No objects found\n"


def list_facts(gm):
    factMetadata = collections.namedtuple('factMetadata',
                                          ['id',
                                           'type',
                                           'creator',
                                           'created'])
    rows = []
    for (factType, factColumn) in gm.facts.items():
        for fact in factColumn:
            created = tsTodt(fact.created)
            md = factMetadata(str(fact.id), factType,
                              fact.creator, created)
            rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No facts found\n"


def list_hyps(gm):
    hypMetadata = collections.namedtuple('hypMetadata',
                                         ['id',
                                          'type',
                                          'creator',
                                          'created'])
    rows = []
    for (hypType, hypColumn) in gm.hyps.items():
        for hyp in hypColumn:
            created = tsTodt(hyp.created)
            md = hypMetadata(str(hyp.id), hypType,
                             hyp.creator, created)
            rows.append(md)

    if len(rows) > 0:
        output = prettyTable(rows)
        return "\n%s\n" % (output)
    else:
        return "No hyps found\n"


def create_objects_list(typ, gm, source):
    objectMetadata = collections.namedtuple('objectMetadata',
                                            ['id',
                                             'creator',
                                             'created',
                                             'filename'])
    rows = []
    for objid in getattr(source, '%sObjects' % (typ)):
        obj = gm.objects[objid]
        created = tsTodt(obj._created_)
        filename = obj.metadata.get('filename', '')
        md = objectMetadata(str(obj.id), obj._creator_, created, filename)
        rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


def create_facts_list(typ, gm, source):
    factMetadata = collections.namedtuple('factMetadata',
                                          ['id',
                                           'type',
                                           'creator',
                                           'created'])
    rows = []
    for (factType, factColumn) in gm.facts.items():
        for fact in factColumn:
            if fact.id in getattr(source, '%sFacts' % (typ)):
                created = tsTodt(fact.created)
                md = factMetadata(str(fact.id), factType,
                                  fact.creator, created)
                rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


def create_hyps_list(typ, gm, source):
    hypMetadata = collections.namedtuple('hypMetadata',
                                         ['id',
                                          'type',
                                          'creator',
                                          'created'])
    rows = []
    for (hypType, hypColumn) in gm.hyps.items():
        for hyp in hypColumn:
            if hyp.id in getattr(source, '%sHyps' % (typ)):
                created = tsTodt(hyp.created)
                md = hypMetadata(str(hyp.id), hypType,
                                 hyp.creator, created)
                rows.append(md)

    if len(rows) > 0:
        return prettyTable(rows)
    else:
        return "None\n"


class BaseCmd(cmd.Cmd):
    def __init__(self, gameMaster, depthList=None):
        super().__init__()
        self.gm = gameMaster
        if depthList is None:
            self.depthList = []
        else:
            self.depthList = depthList

        self.backTo = False

    def precmd(self, line):
        if line == 'EOF':
            self.do_exit('')

        return line

    def do_exit(self, arg):
        """Exit the shell"""
        sys.stdout.write('\n')
        exit(0)

    def do_save(self, arg):
        """Save the state"""

        if arg:
            filename = arg
        else:
            filename = self.gm.options.statefile

        if os.path.exists(filename) and not os.path.isfile(filename):
            sys.stdout.write("%s exists but is not a file\n" % (filename))
            return

        if os.path.isfile(filename):
            if not askPrompt("Overwrite existing file?"):
                sys.stdout.write("State not saved\n")
                return

        sys.stdout.write("Saving to %s ... " % (filename))
        sys.stdout.flush()
        save_state = self.gm.save()
        with open(filename, 'w') as f:
            f.write(yaml.dump(save_state))
        sys.stdout.write("Saved\n")

    def do_list(self, arg):
        """List available objects, facts or hyps

        Syntax: list objects|facts|hyps
        """
        if arg == 'objects':
            output = list_objects(self.gm)
        elif arg == 'facts':
            output = list_facts(self.gm)
        elif arg == 'hyps':
            output = list_hyps(self.gm)
        else:
            sys.stdout.write("list objects|facts|hyps\n")
            return

        sys.stdout.write(output)

    def do_back(self, arg):
        """Return to previous level"""
        if len(self.depthList) == 0:
            sys.stdout.write("Already at root\n")
            return

        if arg is not None and len(arg) > 0:
            if arg == 'root':
                self.backTo = True
            else:
                try:
                    self.backTo = int(arg)
                except Exception:
                    sys.stdout.write("Unexpected value to back\n")
                    return

        return True

    def _parse_bc(self):
        bc = list()
        for i, item in enumerate(self.depthList):
            if isinstance(item, FileObject):
                t = 'object'
            elif isinstance(item, Fact):
                if Fact.tainted:
                    t = 'hyp'
                else:
                    t = 'fact'
            else:
                raise RuntimeError("Unknown type")

            bc.append((i, t, item.id))

        return bc

    def do_bc(self, arg):
        """Print out breadcrumbs"""

        if len(self.depthList) == 0:
            sys.stdout.write("At root\n")
            return

        bc = self._parse_bc()

        for (bcid, bctype, itemid) in bc:
            sys.stdout.write("%d - %s %d\n" % (bcid, bctype, itemid))

    def checkBackTo(self, downBackTo):
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

    def _find_object(self, obj_id):
        try:
            objID = int(obj_id)
        except (ValueError, TypeError):
            raise

        inst = None
        for obj in self.gm.objects:
            if obj.id == objID:
                inst = obj
                break

        if inst is None:
            raise NotFoundError("No object by that id")

        return inst

    def do_object(self, arg):
        """Explore object with a given id"""

        if arg is None:
            sys.stdout.write("Object id required\n")
            return

        try:
            inst = self._find_object(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Object id must be an integer value")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            objcmd = ObjectCmd(self.gm, inst, copy.deepcopy(self.depthList))
            objcmd.cmdloop()
            return self.checkBackTo(objcmd.backTo)

    def _find_fact(self, fact_id):
        try:
            factID = int(fact_id)
        except (ValueError, TypeError):
            raise

        inst = None
        for (factType, factColumns) in self.gm.facts.items():
            for fact in factColumns:
                if fact.id == factID:
                    inst = fact
                    break

        if inst is None:
            raise NotFoundError("No fact by that id")

        return inst

    def do_fact(self, arg):
        """Explore fact with a given id"""

        if arg is None:
            sys.stdout.write("Fact id required\n")
            return

        try:
            inst = self._find_fact(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Fact id must be integer value")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            factcmd = FactCmd(self.gm, inst, copy.deepcopy(self.depthList))
            factcmd.cmdloop()
            return self.checkBackTo(factcmd.backTo)

    def _find_hyp(self, hyp_id):
        try:
            hypID = int(hyp_id)
        except (ValueError, TypeError):
            raise

        inst = None
        for (hypType, hypColumns) in self.gm.hyps.items():
            for hyp in hypColumns:
                if hyp.id == hypID:
                    inst = hyp
                    break

        if inst is None:
            raise NotFoundError("No hyp by that id")

        return inst

    def do_hyp(self, arg):
        """Explore hyp with a given id"""

        if arg is None:
            sys.stdout.write("Hyp id required\n")
            return

        try:
            inst = self._find_hyp(arg)
        except (ValueError, TypeError):
            sys.stdout.write("Hyp id must be integer value")
        except NotFoundError as e:
            sys.stdout.write("%s\n" % (str(e)))
        else:
            hypcmd = HypCmd(self.gm, inst, copy.deepcopy(self.depthList))
            hypcmd.cmdloop()
            return self.checkBackTo(hypcmd.backTo)

    def run(self):
        while 1:
            try:
                self.cmdloop()
            except KeyboardInterrupt:
                sys.stdout.write('\n')
                continue
            break


class ShellCmd(BaseCmd):
    def __init__(self, gameMaster):
        super().__init__(gameMaster)
        self.prompt = "d20 > "

    def do_object(self, arg):
        """Explore an object with a given id"""
        super().do_object(arg)

    def do_fact(self, arg):
        """Explore a fact with a given id"""
        super().do_fact(arg)

    def do_hyp(self, arg):
        """Explore a hyp with a given id"""
        super().do_hyp(arg)


class ObjectCmd(BaseCmd):
    def __init__(self, gameMaster, obj, depthList=None):
        super().__init__(gameMaster, depthList)
        # Append object to depth list
        self.depthList.append(obj)
        self.prompt = "object %d > " % (obj.id)
        self.obj = obj

    def write_list(self, out):
        sys.stdout.write("\nObject %d:\n" % (self.obj.id))
        sys.stdout.write("--------------\n")
        sys.stdout.write(out)
        sys.stdout.write("--------------\n\n")

    def do_metadata(self, arg):
        """Print metadata about object"""
        out = prettyList(self.obj.metadata)
        self.write_list(out)

    def do_info(self, arg):
        """Print basic info about object"""
        created = tsTodt(self.obj._created_)
        out = prettyList({'id': self.obj.id,
                          'creator': self.obj._creator_,
                          'created': created})
        self.write_list(out)

    def do_parents(self, arg):
        """Print out parents of this object"""

        parentObjects = create_objects_list('parent', self.gm, self.obj)
        sys.stdout.write("Parent Objects:\n%s\n" % (parentObjects))

        parentFacts = create_facts_list('parent', self.gm, self.obj)
        sys.stdout.write("Parent Facts:\n%s\n" % (parentFacts))

        parentHyps = create_hyps_list('parent', self.gm, self.obj)
        sys.stdout.write("Parent Hyps: \n%s\n" % (parentHyps))

    def do_children(self, args):
        """Print out children of this object"""

        childObjects = create_objects_list('child', self.gm, self.obj)
        sys.stdout.write("Child Objects:\n%s\n" % (childObjects))

        childFacts = create_facts_list('child', self.gm, self.obj)
        sys.stdout.write("Child Facts:\n%s\n" % (childFacts))

        childHyps = create_hyps_list('child', self.gm, self.obj)
        sys.stdout.write("Child Hyps:\n%s\n" % (childHyps))

    def _find_items(self, data, children):
        itemMetadata = collections.namedtuple('itemMetadata',
                                              ['id',
                                               'type',
                                               'creator',
                                               'created'])
        rows = []
        for (itemType, itemColumn) in data.items():
            for item in itemColumn:
                if item.id in children:
                    created = tsTodt(item.created)
                    md = itemMetadata(str(item.id), itemType,
                                      item.creator, created)
                    rows.append(md)

        return rows

    def _do_items(self, _type, data, children):
        """Print items related to this object"""
        rows = self._find_items(data, children)

        if len(rows) > 0:
            out = prettyTable(rows)
            sys.stdout.write("\n%s\n" % (out))
        else:
            sys.stdout.write('No %s associated with object\n' % (_type))

    def do_facts(self, arg):
        """Print facts related to this object"""
        self._do_items("facts", self.gm.facts, self.obj.childFacts)

    def do_hyps(self, arg):
        """Print hyps related to this object"""
        self._do_items("hyps", self.gm.hyps, self.obj.childHyps)


class FactHypBaseCmd(BaseCmd):
    def __init__(self, _type, gameMaster, item, depthList=None):
        super().__init__(gameMaster, depthList)
        # Append item to depth list
        self._type = _type
        self.depthList.append(item)
        self.prompt = "%s %d > " % (self._type, item.id)
        self.item = item

    def write_list(self, out):
        sys.stdout.write("\n%s %d:\n" % (self._type.capitalize(),
                                         self.item.id))
        sys.stdout.write("--------------\n")
        sys.stdout.write(out)
        sys.stdout.write("--------------\n\n")

    def _find_info(self):
        created = tsTodt(self.item.created)
        item_info = collections.OrderedDict([
                        ('id', self.item.id),
                        ('type', self.item._type),
                        ('creator', self.item.creator),
                        ('created', created)])

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

    def do_info(self, arg):
        """Print info about item"""
        item_info = self._find_info()
        out = prettyList(item_info)
        self.write_list(out)

    def do_parents(self, arg):
        """Print out parents of this item"""

        parentObjects = create_objects_list('parent', self.gm, self.item)
        sys.stdout.write("Parent Objects:\n%s\n" % (parentObjects))

        parentFacts = create_facts_list('parent', self.gm, self.item)
        sys.stdout.write("Parent Facts:\n%s\n" % (parentFacts))

        parentHyps = create_hyps_list('parent', self.gm, self.item)
        sys.stdout.write("Parent Hyps:\n%s\n" % (parentHyps))

    def do_children(self, args):
        """Print out children of this item"""

        childObjects = create_objects_list('child', self.gm, self.item)
        sys.stdout.write("Child Objects:\n%s\n" % (childObjects))

        childFacts = create_facts_list('child', self.gm, self.item)
        sys.stdout.write("Child Facts:\n%s\n" % (childFacts))

        childHyps = create_hyps_list('child', self.gm, self.item)
        sys.stdout.write("Child Hyps:\n%s\n" % (childHyps))

    def do_fields(self, arg):
        """Print out the names of available fields"""
        if len(self.item._fields_) > 0:
            for name in self.item._fields_:
                sys.stdout.write("%s\n" % (name))
        else:
            sys.stdout.write("No fields available\n")

    def do_get(self, arg):
        """Print out value of a given field"""
        if arg not in self.item._fields_:
            sys.stdout.write("No field by that name\n")
            return

        descriptor = getattr(self.item, '_%s__' % arg)

        try:
            output = descriptor.getShell()
        except AttributeError:
            output = "%s field was unset/undefined" % (arg)
        sys.stdout.write("%s\n" % (output))


class FactCmd(FactHypBaseCmd):
    def __init__(self, gameMaster, fact, depthList=None):
        super().__init__("fact", gameMaster, fact, depthList)


class HypCmd(FactHypBaseCmd):
    def __init__(self, gameMaster, fact, depthList=None):
        super().__init__("hyp", gameMaster, fact, depthList)

    def do_promote(self, arg):
        """Promote a hyp to a fact"""
        if askPrompt():
            promoted = self.gm.promoteHyp(self.item.id)
            sys.stdout.write("Hyp Promoted, fact id: %d\n" % (promoted.id))
            return self.do_back(arg)
