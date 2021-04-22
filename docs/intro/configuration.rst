Configuration
=============

D20 can be configured using a yaml configuration file that consists of many sections.

D20 Config
~~~~~~~~~~

The ``d20`` section provides configuration to the d20 program itself and has many of the same features seen in the help output above.

.. code-block:: yaml

    d20:
        extra-players: /data/d20_extras/players
        extra-npcs:
            - /data/d20_extras/npcs
            - /tmp/development/npcs
        extra-facts: /data/d20_extras/facts
        extra-screens: /data/d20_extras/screens
        graceTime: 5
        temporary: /tmp/d20-test


**extra-players**
    A string or list of strings indicating where to find extra players

**extra-npcs**
    A string or list of strings indicating where to find extra npcs

**extra-facts**
    A string or list of strings indicating where to find extra facts

**extra-actions**
    A string or list of strings indicating where to find extra actions

**extra-screens**
    A string or list of strings indicating where to find extra screens

**graceTime**
    An integer value indicating how many seconds the Game Master should wait before determining the game is in a state in which it can't continue.
    This defaults to 1.

**temporary**
    A string value indicating the base directory to store temporary contents.
    This is equivalent to using the `-t` flag.


Common Config
~~~~~~~~~~~~~

The ``common`` section is used to specify information that doesn't apply to any specific section and gets injected into the config for every element (player, npc, screen, etc).

.. code-block:: yaml

    common:
        http_proxy: "http://internal.proxy.localdomain"


Element Configs
~~~~~~~~~~~~~~~

Players, NPCs, Actions and Screens have their own section in the config, allowing individual pieces to be configured individually.
The syntax is to provide a dictionary of data which will then be passed into each element

.. code-block:: yaml

    Screens:
        json:
            exclude_objects: True
    Actions:
    NPCS:
    Players:
    BackStories:


To find out what configuration options are available please read the
documentation for that element