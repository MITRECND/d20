import sys
import os
import argparse
import time
import textwrap
import yaml


from d20.version import GAME_ENGINE_VERSION
from d20.Manual.Logger import logging
from d20.Manual.Facts import loadFacts
from d20.Manual.Config import Configuration
from d20.Manual.Shell import ShellCmd
from d20.Players import verifyPlayers
from d20.NPCS import verifyNPCs
from d20.BackStories import verifyBackStories
from d20.Screens import verifyScreens
from d20.Actions import (setupActionLoader, ACTION_INVENTORY)
from d20.Manual.GameMaster import GameMaster
from d20.Manual.Options import _empty

LOGGER = logging.getLogger(__name__)


def __fix_default(value):
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, bytes):
        return str(value, 'utf-8')
    else:
        return str(value)


def __generate_config_file(args, config):
    players = verifyPlayers(args.extra_players, config)
    npcs = verifyNPCs(args.extra_npcs, config)
    backstories = verifyBackStories(args.extra_backstories, config)
    screens = verifyScreens(args.extra_screens, config)
    # actions are handled by the setupActionLoader and inclusion in other code

    TAB = "    "
    default_config = ""

    for (section, entities) in (
            ("Actions", ACTION_INVENTORY.values()),
            ("Backstories", backstories),
            ("NPCS", npcs),
            ("Players", players),
            ("Screens", screens.values())):

        default_config += f"{section}:\n"
        entity_configs = dict()
        for entity in entities:
            entity_config = ""
            entity_config += f"# {TAB}{entity.registration.name}:\n"
            for (name, details) in entity.registration.options.docs.items():
                if details['help'] is not None:
                    entity_config += f"# {TAB}{TAB}{details['help']}\n"
                entity_config += f"# {TAB}{TAB}{name}: "
                if details['default'] != _empty:
                    entity_config += (
                        __fix_default(details['default']) +
                        f"  # {str(details['type'].__name__)}\n")
                else:
                    entity_config += f"  # {str(details['type'].__name__)}\n"

            entity_configs[entity.registration.name] = entity_config
        for name in sorted(entity_configs.keys()):
            default_config += entity_configs[name]

    if args.generate_config_file != "-":
        with open(args.generate_config_file, 'w') as outfile:
            outfile.write(default_config)
    else:
        print(default_config)


def __setup(args, console=False):
    logging.setupLogger(
            debug=args.debug,
            verbose=args.verbose,
            console=console
    )

    Config = Configuration(configFile=args.config, args=args)

    if args.temporary is None:
        args.temporary = "/tmp/d20-%d" % time.time()

    setupActionLoader(args.extra_actions, Config)
    loadFacts(args.extra_facts)
    return Config


def main():
    parser = argparse.ArgumentParser(description="Roll the dice")

    input_group = parser.add_mutually_exclusive_group()

    input_group.add_argument(
        "-f", "--file", type=str, default=None,
        dest="file", help="Input file to process")
    input_group.add_argument(
        "--backstory-facts", type=str, default=None,
        dest="backstory_facts",
        help="A yaml/json string to provide to backtories")
    input_group.add_argument(
        "--backstory-facts-path", type=str, default=None,
        dest="backstory_facts_path",
        help=("A path to a yaml/json file with facts to "
              "present to backstories"))

    information_group = parser.add_argument_group('Informational')

    information_group.add_argument(
        "-l", "--list-players", action="store_true",
        dest="list_players", help="Show available players")
    information_group.add_argument(
        "-i", "--info-player", action="store",
        dest="info_player", default=None,
        help="Show information about a specific player")
    information_group.add_argument(
        "-n", "--list-npcs", action="store_true",
        dest="list_npcs", help="Show available npcs")
    information_group.add_argument(
        "-s", "--list-backstories", action="store_true",
        dest="list_backstories",
        help="Show available backstories")
    information_group.add_argument(
        "--list-screens", action="store_true",
        dest="list_screens", help="Show available screens")
    information_group.add_argument(
        '--version', action="store_true", default=False,
        dest="version", help="Print version and exit")

    parser.add_argument(
        "-c", "--config", type=str, default=None,
        help=("Path to a configuration file that will pass "
              "options to players, screens and npcs"))
    parser.add_argument(
        "--extra-players", dest="extra_players",
        nargs="*", default=list(),
        help="Directories where extra players may be found")
    parser.add_argument(
        "--extra-npcs", dest="extra_npcs", default=list(),
        nargs="*", help="Directories where extra npcs may be found")
    parser.add_argument(
        "--extra-backstories", dest="extra_backstories",
        default=list(), nargs="*",
        help="Directories where extra backstories may be found")
    parser.add_argument(
        "--extra-actions", dest="extra_actions",
        default=list(), nargs="*",
        help="Directories where extra actions may be found")
    parser.add_argument(
        "--extra-facts", dest="extra_facts", default=list(),
        nargs="*", help=("Directories where extra facts may be found"))
    parser.add_argument(
        "--extra-screens", dest="extra_screens",
        nargs="*", default=list(),
        help="Directories where extra game screens may be found")

    parser.add_argument(
        "--use-screen", dest="use_screen",
        default="json",
        help="What screen to use to present data after game has completed")
    parser.add_argument(
        "-t", "--temporary", dest="temporary", action="store",
        default=None,
        help=("Base directory to store temporary contents, "
              "Defaults to /tmp/d20-<timestamp>/"))
    parser.add_argument(
        "--dump-objects", dest="dump_objects",
        action="store", default=None, metavar="DUMP_OBJECTS_DIRECTORY",
        help="On program exit, dump all objects to the given directory ")
    parser.add_argument(
        "--save", action="store", dest="save_file",
        default=None, help="Location/file to save state")
    parser.add_argument(
        "--load", action="store", dest="load_file",
        default=None, help="Location/file to restore state")
    parser.add_argument(
        '--debug', action="store_true", default=False,
        dest="debug", help="Enable debugging output")
    parser.add_argument(
        '-v', '--verbose', action="store_true", default=False,
        dest="verbose", help="Enable verbose output")

    parser.add_argument(
        '--generate-config-file', action="store", default=None,
        dest="generate_config_file", metavar="CONFIG_FILE_PATH",
        help="Walk entities and generate a default configuration file")

    args = parser.parse_args()

    if args.version:
        print("d20: Engine %s" % (GAME_ENGINE_VERSION))
        sys.exit(0)

    Config = __setup(args, console=True)

    if args.list_players:
        print("Registered Players:")
        players = verifyPlayers(args.extra_players,
                                Config)
        if len(players) == 0:
            print("\tNo Players :(")
        else:
            for player in players:
                print("\t%s" % (player.name))
        sys.exit(0)

    if args.list_npcs:
        print("Registered NPCs:")
        npcs = verifyNPCs(args.extra_npcs, Config)
        if len(npcs) == 0:
            print("\tNo NPCs")
        else:
            for npc in npcs:
                print("\t%s" % (npc.name))
        sys.exit(0)

    if args.list_backstories:
        print("Registered BackStories:")
        backstories = verifyBackStories(args.extra_backstories, Config)
        if len(backstories) == 0:
            print("\tNo BackStories")
        else:
            for npc in backstories:
                print("\t%s" % (npc.name))
        sys.exit(0)

    if args.list_screens:
        print("Installed Screens:")
        screens = verifyScreens(args.extra_screens,
                                Config)
        if len(screens) == 0:
            print("\tNo Screens")
        else:
            for screen in screens.values():
                print("\t%s" % (screen.name))
        sys.exit(0)

    if args.info_player is not None:
        players = verifyPlayers(args.extra_players,
                                Config)
        for player in players:
            if player.name == args.info_player:
                print("%s:" % player.registration.name)
                print("\tCreator: %s" % (player.registration.creator))
                print("\tVersion: %s" % (player.registration.version))
                print("\tGame Engine: %s"
                      % (player.registration.engine_version))

                desc_lines = textwrap.wrap(player.registration.description,
                                           width=50)
                if len(desc_lines) > 1:
                    prefix = "\t%13s" % (' ')
                    print("\tDescription: %s" % (desc_lines.pop(0)))
                    print(prefix + (prefix.join(desc_lines)))
                else:
                    print("\tDescription: %s"
                          % (player.registration.description))
                # print("\tInterests:")
                # for ft in sorted(list(player.registration.interests)):
                #     print("\t\t%s" % (str(ft)))
                if len(player.registration.facts_consumed) > 0:
                    print("\tFacts Consumed:")
                    for fc in sorted(list(player.registration.facts_consumed)):
                        print("\t\t%s" % (str(fc)))
                if len(player.registration.facts_generated) > 0:
                    print("\tFacts Generated:")
                    for fg in sorted(
                            list(player.registration.facts_generated)):
                        print("\t\t%s" % (str(fg)))
                if isinstance(player.registration.help, str):
                    help_lines = textwrap.wrap(player.registration.help,
                                               width=60)
                    help_msg = "\n\t\t".join(help_lines)
                    print("\n\tHelp:\n\t\t%s" % (help_msg))

        sys.exit(0)

    if args.generate_config_file is not None:
        __generate_config_file(args, Config)
        sys.exit(0)

    exclude_arguments = [
        "list_players",
        "list_screens",
        "list_backstories",
        "list_npcs",
        "info_players",
        "version",
        "generate_config_file"
    ]

    arguments = vars(args)
    arguments.update({
        "_config": Config,
        "printable": True
    })
    for argument in exclude_arguments:
        if argument in arguments:
            del arguments[argument]

    try:
        results = play(**arguments)
        print(results)
    except ValueError as e:
        print(str(e))
        sys.exit(1)


def play(**kwargs):
    """play the game

    This method allows one to call d20 from another python program returning
    data about a given object based on provided options/inputs

    **kwargs:
        file(str): Path to a file to analyze

        backstory_facts(str): A yaml/json string of facts

        backstory_facts_path(backstory): A path to a yaml/json string
            with facts for backstories

        config(str): Path to a config file with configuration options set

        use_screen(str): Which screen to use to process data, string should be
            friendly name of the screen

        temporary(str): The path to use to store temporary files/folders

        dump_objects(str): The path to use to dump process objects

        save_file(str): The path to write the save state of game progress
            after completion

        load_file(str): The path to read in a save state when a game needs
            to be continued. Loaded save states take priority over file paths

        extra_players(list[str]): A list of paths where extra players may be
            loaded

        extra_npcs(list[str]): A list of paths where extra npcs may be loaded

        extra_backstories(list[str]): A list of paths where extra backstories
            may be loaded

        extra_actions(list[str]): A list of paths where extra actions may be
            loaded

        extra_facts(list[str]): A list of paths where extra facts may be
            loaded

        extra_screens(list[str]): A list of paths where extra screens may be
            loaded

        disable_async(bool): Disable asyncio support if code is not
            asyncio friendly

    Returns:
        results: An object, usually a dict, containing the processed data

        Please reference documentation for the chosen screen to determine what
        type of data it returns.

    Raises:
        TypeError: If an argument provided is of an unaccepted type.
        ValueError: If an argument is not provided or have a value that cannot
            be understood
        RuntimeError: Any error from the running game

    """

    args = argparse.Namespace()

    # The following are the recognized keyword arguments
    args.disable_async = False
    args.file = None
    args.backstory_facts = None
    args.backstory_facts_path = None
    args.config = None
    args.use_screen = "json"
    args.temporary = None
    args.dump_objects = None
    args.save_file = None
    args.load_file = None
    args.debug = False
    args.verbose = False
    args.graceTime = 1
    args.maxGameTime = 0
    args.maxTurnTime = 0
    args.extra_players = list()
    args.extra_npcs = list()
    args.extra_backstories = list()
    args.extra_actions = list()
    args.extra_facts = list()
    args.extra_screens = list()
    args.printable = False

    # Internally used arguments
    args._config = None

    string_args = [
        'file',
        'backstory_facts',
        'backstory_facts_path',
        'config',
        'use_screen',
        'temporary',
        'dump_objects',
        'save_file',
        'load_file']

    list_args = [
        'extra_players',
        'extra_npcs',
        'extra_backstories',
        'extra_actions',
        'extra_facts',
        'extra_screens']

    bool_args = [
        'disable_async',
        'debug',
        'verbose',
        'printable'
    ]

    int_args = [
        'graceTime',
        'maxGameTime',
        'maxTurnTime'
    ]

    for (name, value) in kwargs.items():
        if value is None:
            continue
        if name in args:
            if name in string_args:
                if not isinstance(value, str):
                    raise TypeError(f"{name} should be str type")
            elif name in list_args:
                if not isinstance(value, list):
                    raise TypeError(f"{name} should be list type")
            elif name in bool_args:
                if not isinstance(value, bool):
                    raise TypeError(f"{name} should be bool type")
            elif name in int_args:
                if not isinstance(value, int):
                    raise TypeError(f"{name} should be int type")
            setattr(args, name, value)
        else:
            raise ValueError(f"Unexpected keyword {name}")

    if all([inp is None for inp in [
            args.file,
            args.backstory_facts,
            args.backstory_facts_path]]) and args.load_file is None:
        raise ValueError("File/BackStory Facts or Save State required")

    if args._config is not None:
        Config = args._config
    else:
        Config = __setup(args)

    save_state = None
    if args.load_file is not None:
        with open(args.load_file, 'r') as f:
            save_state = yaml.load(f.read(), Loader=yaml.FullLoader)

    try:
        gm = GameMaster(extra_players=args.extra_players,
                        extra_npcs=args.extra_npcs,
                        extra_backstories=args.extra_backstories,
                        extra_screens=args.extra_screens,
                        config=Config,
                        options=args,
                        save_state=save_state)
    except Exception:
        raise RuntimeError("Unable to init the GM")

    try:
        gm.startGame(asyncio_enable=(not args.disable_async))
    except Exception:
        raise RuntimeError("Issue starting/running game")

    # If async is enabled, startGame will block, when disabled
    # status needs to be polled
    if args.disable_async:
        try:
            while gm.gameRunning:
                time.sleep(.01)
        except KeyboardInterrupt:
            gm.stop()

        gm.join()

    results = None
    if args.use_screen != "none":
        results = gm.provideData(
            args.use_screen,
            printable=args.printable)

    if args.save_file is not None:
        save_state = gm.save()
        with open(args.save_file, 'w') as f:
            f.write(yaml.dump(save_state))

    if args.dump_objects is not None:
        os.makedirs(args.dump_objects, exist_ok=True)

        for obj in gm.objects:
            filename = obj.metadata.get('filename', 'nofilename')
            creator = obj._creator_
            outname = "%d-%s-%s-%s" % (obj.id, creator, obj.hash, filename)
            with open(os.path.join(args.dump_objects, outname), 'wb') as f:
                f.write(obj.data)

    gm.cleanup()

    return results


def shellmain():
    parser = argparse.ArgumentParser(description="d20 Interactive Console")
    parser.add_argument("statefile", action="store",
                        help="Location/file to restore state")
    parser.add_argument("-c", "--config", type=str, default=None,
                        help=("Path to a configuration file that will pass "
                              "options to players, screens and npcs"))
    parser.add_argument("--extra-players", dest="extra_players",
                        nargs="*", default=list(),
                        help=("Directories where "
                              "extra players may be found"))
    parser.add_argument("--extra-npcs", dest="extra_npcs", default=list(),
                        nargs="*", help=("Directories where extra "
                                         "npcs may be found"))
    parser.add_argument("--extra-backstories", dest="extra_backstories",
                        default=list(), nargs="*",
                        help=("Directories where extra "
                              "backstories may be found"))
    parser.add_argument("--extra-actions", dest="extra_actions",
                        default=list(), nargs="*",
                        help=("Directories where extra actions"
                              "may be found"))
    parser.add_argument("--extra-facts", dest="extra_facts", default=list(),
                        nargs="*", help=("Directories where extra facts"
                                         "may be found"))
    parser.add_argument('--debug', action="store_true", default=False,
                        dest="debug", help="Enable debugging output")
    parser.add_argument('-v', '--verbose', action="store_true", default=False,
                        dest="verbose", help="Enable verbose output")

    args = parser.parse_args()

    logging.setupLogger(
            debug=args.debug,
            verbose=args.verbose,
            console=True
    )

    Config = Configuration(configFile=args.config, args=args)

    setupActionLoader(args.extra_actions, Config)
    loadFacts(args.extra_facts)

    print("Reading state file, please wait ... ")
    with open(args.statefile, 'r') as f:
        save_state = yaml.load(f.read(), Loader=yaml.FullLoader)

    try:
        gm = GameMaster(extra_players=args.extra_players,
                        extra_npcs=args.extra_npcs,
                        extra_backstories=args.extra_backstories,
                        config=Config,
                        options=args,
                        save_state=save_state)
    except Exception:
        LOGGER.exception("Unable to init the GM")
        sys.exit(1)

    print("Loading GM ...")
    gm.load()
    shell = ShellCmd(gm)
    shell.run()
