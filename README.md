# d20 #

## Development ##

Code base developed against Python 3.6, tested with Python 3.6 - 3.9.

To develop, setup a virtualenv (or not) and do:

`pip install -e .`

This will install the package in development mode allowing changes to be made.

## Installation ##

To install the code regularly just do:

`pip install .`

## Usage ##

To run the code, after installing via pip, `d20` should be in your path:

```text
> d20 --help
usage: d20 [-h]
           [-f FILE | --backstory-facts BACKSTORY_FACTS | --backstory-facts-path BACKSTORY_FACTS_PATH]
           [-l] [-i INFO_PLAYER] [-n] [-s] [--list-screens] [--version]
           [-c CONFIG] [--extra-players [EXTRA_PLAYERS [EXTRA_PLAYERS ...]]]
           [--extra-npcs [EXTRA_NPCS [EXTRA_NPCS ...]]]
           [--extra-backstories [EXTRA_BACKSTORIES [EXTRA_BACKSTORIES ...]]]
           [--extra-actions [EXTRA_ACTIONS [EXTRA_ACTIONS ...]]]
           [--extra-facts [EXTRA_FACTS [EXTRA_FACTS ...]]]
           [--extra-screens [EXTRA_SCREENS [EXTRA_SCREENS ...]]]
           [--use-screen USE_SCREEN] [-t TEMPORARY]
           [--dump-objects DUMP_OBJECTS_DIRECTORY] [--save SAVE_FILE]
           [--load LOAD_FILE] [--debug] [-v]
           [--generate-config-file CONFIG_FILE_PATH]

Roll the dice

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Input file to process
  --backstory-facts BACKSTORY_FACTS
                        A yaml/json string to provide to backtories
  --backstory-facts-path BACKSTORY_FACTS_PATH
                        A path to a yaml/json file with facts to present to
                        backstories
  -c CONFIG, --config CONFIG
                        Path to a configuration file that will pass options to
                        players, screens and npcs
  --extra-players [EXTRA_PLAYERS [EXTRA_PLAYERS ...]]
                        Directories where extra players may be found
  --extra-npcs [EXTRA_NPCS [EXTRA_NPCS ...]]
                        Directories where extra npcs may be found
  --extra-backstories [EXTRA_BACKSTORIES [EXTRA_BACKSTORIES ...]]
                        Directories where extra backstories may be found
  --extra-actions [EXTRA_ACTIONS [EXTRA_ACTIONS ...]]
                        Directories where extra actions may be found
  --extra-facts [EXTRA_FACTS [EXTRA_FACTS ...]]
                        Directories where extra facts may be found
  --extra-screens [EXTRA_SCREENS [EXTRA_SCREENS ...]]
                        Directories where extra game screens may be found
  --use-screen USE_SCREEN
                        What screen to use to present data after game has
                        completed
  -t TEMPORARY, --temporary TEMPORARY
                        Base directory to store temporary contents, Defaults
                        to /tmp/d20-<timestamp>/
  --dump-objects DUMP_OBJECTS_DIRECTORY
                        On program exit, dump all objects to the given
                        directory
  --save SAVE_FILE      Location/file to save state
  --load LOAD_FILE      Location/file to restore state
  --debug               Enable debugging output
  -v, --verbose         Enable verbose output
  --generate-config-file CONFIG_FILE_PATH
                        Walk entities and generate a default configuration
                        file

Informational:
  -l, --list-players    Show available players
  -i INFO_PLAYER, --info-player INFO_PLAYER
                        Show information about a specific player
  -n, --list-npcs       Show available npcs
  -s, --list-backstories
                        Show available backstories
  --list-screens        Show available screens
  --version             Print version and exit

```

## Components ##

d20 consists of multiple components and pieces to actually operate. The high
level components consist of

* Players
* NPCs
* BackStories
* Actions
* Manual
  * Facts
* Screens

### Manual ###

The Manual is the internal piece of d20 that is used to run the game

### Players ###

A 'player' is a component that will attempt to dissect an object or objects
based on facts that have been presented to it

### NPCs ###

An NPC is a component that automatically runs on an object when it is created
to create some basic metadata to start the game. These components have minimal
logic and are intended to kick of the scenario to give the players enough
information to get going.

### BackStories ###

A BackStory is a component that can be run at the beginning of the game with pre-seeded facts to enable object-less operation. This allows one to programmatically kick of D20 using BackStories to obtain binaries dynamically.

### Actions ###

Actions are functions or code that might be often reused. Actions must be
proper python packages and must follow any development guidance that applies
to the core of d20.

### Screens ###

Screens are used to take the gained knowledge from the game and do something
with it. It can be output to the screen, sent to another system, etc. When run,
a screen is selected as an argument.

### Feature Integration ###

D20 can be expanded with new features by creating your own Players, NPCs,
Facts, Actions, and Screens.

Approved for Public Release; Distribution Unlimited. Public Release Case Number 21-0601

&copy;2021 The MITRE Corporation. ALL RIGHTS RESERVED.
