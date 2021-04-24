# d20 #

D20 is an asynchronous framework that attempts to aid analysts in dissecting a binary (or other file) in a non-serial manner. This means malicious programs that exhibit complex workflows, which might not be parsable in a serialized fashion can be looked at in an automated fashion using D20.

D20's core approach to gaining deep insights and overcoming the problems of serialized workflows is based on the [Blackboard System](https://en.wikipedia.org/wiki/Blackboard_system). Three components comprise the Blackboard within D20:

* Object Table
* Fact Table
* Hypothesis Table

When you run D20 against a file, it is entered into the Object Table as Object 0. All available [NPCs](https://d20-framework.readthedocs.io/en/latest/authoring/npcs.html) will then execute against Object 0 and apply their expertise to add Facts to the Fact table or Hyps to the Hypothesis Table. As additional objects are uncovered (say...unzipping Object 0), they can be added as additional objects to the table and are treated the same way with all NPCs executing against it. If a block of data is added to the object table that is identical to an existing object, it will not be duplicated, but a relationship will be created to reflect it.

The Fact and Hypothesis tables are effectively identical. The only difference is that Fact objects added to the Hypothesis table are marked "tainted" so you know it is a best-guess based on the information at hand. Each column in the Fact Table is of a specific [FactType](https://d20-framework.readthedocs.io/en/latest/authoring/facts.html). When a Fact of a given type is added, it will be added to the associated column (like a new single-cell row).

Any [Player](https://d20-framework.readthedocs.io/en/latest/authoring/players.html) registered with the system that has an interest in the Fact that is added will get cloned and instructed to use that Fact to perform additional analysis, adding more Facts to the table. More Facts are added, and more players are cloned and executed. Some Players can even put themselves into a WAITING state if they are looking for a specific Fact to hit the Fact Table that it needs to perform additional steps (ex: identifying an encrypted blob and waiting for a decryption key to be added to the table).

This process continues until all Players have either finished adding Facts, or are sitting in a WAITING state and will not get any additional Facts to work with. The game will end at this point. The Game Master will execute the chosen [Screen](https://d20-framework.readthedocs.io/en/latest/authoring/screens.html) to look at all of the information available in the system (from all three table), and present the data. It can print the data in a certain format, save it to a file, generate a host of files with information in them, push the data to a database, pull data from another system and combine it with the results to do something else, etc. What happens to the results at this point is really up to your creativity.

For more detailed information, check [readthedocs](https://d20-framework.readthedocs.io/)

Approved for Public Release; Distribution Unlimited. Public Release Case Number 21-0601

&copy;2021 The MITRE Corporation. ALL RIGHTS RESERVED.
