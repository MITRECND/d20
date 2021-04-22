D20 Shell
=========

The D20 shell provides the ability for an analyst to interace with the save state of a D20 run.
Allowing them to navigate the information gathered and promote any hyps in the data set.
If any hyps are promoted to facts, the save state can be resaved and then loaded back into D20 to continue the game.
To invoke the shell run `d20-shell` long with save state file.

The following is the help output of ``d20-shell``

.. code-block:: bash

    usage: d20-shell [-h] [-c CONFIG]
                    [--extra-players [EXTRA_PLAYERS [EXTRA_PLAYERS ...]]]
                    [--extra-npcs [EXTRA_NPCS [EXTRA_NPCS ...]]]
                    [--extra-actions [EXTRA_ACTIONS [EXTRA_ACTIONS ...]]]
                    [--extra-facts [EXTRA_FACTS [EXTRA_FACTS ...]]] [--debug]
                    [-v]
                    statefile

    d20 Interactive Console

    positional arguments:
    statefile             Location/file to restore state

    optional arguments:
    -h, --help            show this help message and exit
    -c CONFIG, --config CONFIG
                            Path to a configuration file that will pass options to
                            players, screens and npcs
    --extra-players [EXTRA_PLAYERS [EXTRA_PLAYERS ...]]
                            Directories where extra players may be found
    --extra-npcs [EXTRA_NPCS [EXTRA_NPCS ...]]
                            Directories where extra npcs may be found
    --extra-actions [EXTRA_ACTIONS [EXTRA_ACTIONS ...]]
                            Directories where extra actionsmay be found
    --extra-facts [EXTRA_FACTS [EXTRA_FACTS ...]]
                            Directories where extra factsmay be found
    --debug               Enable debugging output
    -v, --verbose         Enable verbose output

Running the Shell
-----------------

The following is an example of how you'd run ``d20-shell`` using the savestate
file ``mysave.d20``

.. code-block:: bash

    d20-shell -c ~/myd20confg.yml mysave.d20

After starting the shell an interactive prompt will be shown:

.. code-block:: text

    Reading state file, please wait ...
    Loading GM ...
    d20 >

To get a list of commands you can use type either ``?`` or ``help``:

.. code-block:: text

    d20 > ?

    Documented commands (type help <topic>):
    ========================================
    back  bc  exit  fact  help  hyp  list  object  save

    d20 > help

    Documented commands (type help <topic>):
    ========================================
    back  bc  exit  fact  help  hyp  list  object  save

    d20 >

To get help on a given command type ``? <command>``:

.. code-block:: text

    d20 > ? list
    List available objects or facts
    d20 >

If a command requires parameters or is used incorrectly, it will prompt with
its proper usage:

.. code-block:: text

    d20 > list
    list objects|facts|hys
    d20 >

Navigating Data
---------------

Using the commands available you can navigate around available data:

.. code-block:: text

    d20 > list facts

    id | type         | creator     | created
    ---+--------------+-------------+---------------------------
    4  | sha256       | HashNPC     | 2018-09-19 12:49:30.336911
    2  | mimetype     | MimeTypeNPC | 2018-09-19 12:49:30.324888
    3  | ascii_string | TestPlayer  | 2018-09-19 12:49:30.326102
    0  | md5          | HashNPC     | 2018-09-19 12:49:30.308111
    1  | sha1         | HashNPC     | 2018-09-19 12:49:30.320824
    5  | ssdeep       | HashNPC     | 2018-09-19 12:49:30.376674

    d20 > fact 1
    fact 1 > info

    Fact 1:
    --------------
    id      = 1
    type    = sha1
    creator = HashNPC
    created = 2018-09-19 12:49:30.320824
    value   = d2b54044a477eb0d5003dd317fafd3ada0b03e3d
    --------------

    fact 1 > ?

    Documented commands (type help <topic>):
    ========================================
    back  children  fact    get   hyp   list    parents
    bc    exit      fields  help  info  object  save

    fact 1 > parents
    Parent Objects:
    id | creator    | created                    | filename
    ---+------------+----------------------------+---------
    0  | GameMaster | 2018-09-19 12:49:30.299334 | test.zip

    Parent Facts:
    None

    Parent Hyps:
    None

    fact 1 > bc
    0 - fact 1
    fact 1 > object 0
    object 0 > info

    Object 0:
    --------------
    id      = 0
    creator = GameMaster
    created = 2018-09-19 12:49:30.299334
    --------------

BreadCrumbs
~~~~~~~~~~~

At any time, if you'd like to see how you've gotten to the entity you are at,
you can use the breadcrumbs (``bc``) command to print a listing

.. code-block:: text

    fact 5 > bc
    0 - fact 1
    1 - object 0
    2 - fact 5

You can then go back to a previous entity by using the back command and
specifying the breadcrumb id from the list

.. code-block:: text

    fact 5 > back 0
    fact 1 > bc
    0 - fact 1
    fact 1 >

If you'd like to return all the way back to the root prompt you can run
``back root``

.. code-block:: text

    fact 5 > bc
    0 - fact 1
    1 - object 0
    2 - fact 5
    fact 5 > back root
    d20 > bc
    At root
    d20 >

Promoting Hyps
--------------

The shell is one way a ``hyp`` can be promoted into a ``fact``.
This allows an analyst to update the knowledge-base, create a new save state and then continue the game using this new information.

The following is an example of promoting a ``hyp`` to a ``fact`` via the shell:

.. code-block:: text

    d20 > list hyps

    id | type     | creator    | created
    ---+----------+------------+--------------------
    0  | mimetype | TestPlayer | 2018-09-17 13:39:22.881252

    d20 > hyp 0
    hyp 0 > ?

    Documented commands (type help <topic>):
    ========================================
    back  children  fact    get   hyp   list    parents  save
    bc    exit      fields  help  info  object  promote

    hyp 0 > promote
    Are you sure? (y/n) y
    Hyp Promoted, fact id: 5
    d20 > bc
    At root
    d20 > list hyps
    No hyps found
    d20 > list facts

    id | type     | creator     | created
    ---+----------+-------------+---------------------------
    1  | mimetype | MimeTypeNPC | 2018-09-17 13:39:22.878769
    5  | mimetype | TestPlayer  | 2018-09-17 13:39:22.881252
    3  | sha256   | HashNPC     | 2018-09-17 13:39:22.902110
    0  | md5      | HashNPC     | 2018-09-17 13:39:22.875597
    2  | sha1     | HashNPC     | 2018-09-17 13:39:22.887539
    4  | ssdeep   | HashNPC     | 2018-09-17 13:39:22.929160

    d20 >

Saving a new state
------------------

If you've modified the data in any way, you can save a new state or overwrite
the existing state file using the ``save`` command:

.. code-block:: text

    d20 > save mysave2.d20
    Saving to mysave2.d20 ... Saved
    d20 >

Note that if the destination file exists, the shell will prompt to ensure
the file is not accidentally overwritten.