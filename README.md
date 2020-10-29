# Roll35

A Discord bot for rolling against various tables for Pathfinder 1e and
related games.

## Features

* Roll for random magic items in a single command. This automatically
  handles all the sequential rolls required to produce an exact magic
  item.
* Roll random spells, optionally for a specific level or class.
* Roll random mundane weapons and armor.

## Planned Features

* Proper handling for magic double weapons.
* Roll against arbitrary data tables.
* Support for rolling for intelligence/special markings on magic items.
* Finish adding in variant forms for all the magic items that have them:
  - Defiant Armor
  - Bane Weapons
* The ability to enable and disable specific items at runtime (with
  per-server config).
* Support for hyperlinks in rolled items.
* Support for rolling specific base weapons or armor as magic items.
* Support for simply rolling dice.

## Limitations

* No support for special materials for magic weapons and armor. This is
  actually _really_ complicated because of the limitations on how different
  materials can be used for specific items. I would like to support it,
  but it's likely to take a long time.
* No support for rolling associated skills on headband items that boost
  INT. This is intentionally left to the GM to determine, as in many cases
  which skills are picked are not truly random. May be added at some
  point in the future once per-server configuration support is added.

## Data Sets

Roll35 comes bundled with a usable dataset for Pathfinder
1e. This includes the data for the official tables from
[D20PFSRD](https://www.d20pfsrd.com/) that are needed for all of the
features the bot provides.

Note that this data set includes some slight differences from the official
tables. In particular:
* In cases where the table is obviously indicating a desired one-in-three
  split for three items or a 1:2 ratio for two items, the proportions are
  annotated in the datset to actually provide this.
* In a couple of places, we group multiple items that are identical in
  cost and proportion relative to each other into a single item which rolls
  for the variant automatically. This is done to make the datast maller
  and slightly improve performance and resource usage of the bot itself.
* In a handful of places, the official tables are, quite simply, broken
  (they either have missing ranges of dice values, or have specific values
  that correlate to multiple items). If ranges are missing, we behave as
  if they simply did not exist (that is, all the other items keep their
  proper relative proportions), and if there are duplicate values we
  adjust accordingly. All such cases are documented in comments in the
  [data.yaml](./data.yaml) file.
* There are a number of weapons and armors that are only rarely used
  or are logically unlikely to be encountered 'in the wild'. These are
  included in the dataset, but are not enabled by default (so they will
  not appear in rolled items). They can be manually enabled by editing
  the [data.yaml](./data.yaml) file.

However, it's usable for any system that follows the same general pattern
that Pathfinder 1e does, it just needs a different data set. See
[template.yaml](./template.yaml) for a template to use for creating such
a dataset.
