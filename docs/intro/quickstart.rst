QuickStart
==========

Running D20
-----------

D20 is run by using the ``d20`` command on the command line.  Here is the help of the ``d20`` command:

.. code-block:: bash

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


The simplest way to run ``d20`` is with a binary file to analyze:

.. code-block:: bash

    > d20 foo.exe

This will run any available NPCs and in turn Players on the given file and then execute the default ``json`` screen.

The easiest way to repeatably run D20 is using a configuration file. To generate a template configuration file with options for all included components run:

.. code-block:: bash

    > d20 --generate-config-file myconfig.yml


This will generate a yaml file with options you can tweak:

.. code-block:: yaml
    :linenos:

    Actions:
    Backstories:
    NPCS:
    #     HashNPC:
    #     MimeTypeNPC:
    Players:
    Screens:
    #     json:
    #         exclude:   # list
    #         exclude_objects: false  # bool
    #         convert_bytes: true  # bool
    #         include_core_facts: false  # bool
    #     yaml:
