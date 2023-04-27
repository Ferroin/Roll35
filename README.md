# Roll35

A Discord bot for rolling against various tables for Pathfinder 1e and
related games.

## Features

- Shows itself as typing while processing commands.
- Roll for random magic items in a single command. This automatically
  handles most of the sequential rolls required to produce an exact
  magic item.
- Automatically roll random spells for scrolls, potions, and wands.
- Roll random spells, optionally for a specific level, class, or category.
- Roll random mundane weapons and armor.
- Roll specific base weapons or armor as magic items.
- Roll wands or scrolls for a specific class.

## Planned Features

- Roll for magic item availability in settlements.
- Roll wands or scrolls for a specific spell level.
- Roll for random weather conditions.
- Automatically roll random spells present in items that store spells.
- Automatically roll for intelligence/special markings on magic items.
- Respond to DMs without requring the command prefix.
- Mention the user who requested the command when responding in a server channel.
- Respond with embeds containing relevent information about the rolled
  item, including hyperlinks to relevant reference material.
- Fetch data on specific items directly without rolling for them randomly.

## Limitations

- No support for special materials for magic weapons and armor. This is
  actually _really_ complicated because of the limitations on how different
  materials can be used for specific items. I would like to support it,
  but it's likely to take a long time.
- No support for rolling associated skills on headband items that boost
  INT. This is intentionally left to the GM to determine, as in many cases
  which skills are picked are not truly random. May be added at some
  point in the future once per-server configuration support is added.

## Using the Bot

All bot commands start with the prefix `/r35`.

You can see interactive help by running `/r35 help`

Commands, including the prefix, are case-insensitive.

If the command prefix is not correct, then the bot will not respond at all.

The bot supports responding to DMs, but currently still requires the
command prefix for them.

## Running the Bot

Roll35 is designed to be packaged as and run from a Docker image. Images
built from the official repo with the standard data set are available on
[Docker Hub](https://hub.docker.com/repository/docker/ahferroin7/roll35).

The following environment variables are used by the image:

- `DISCORD_TOKEN`: Specifies the Discord bot account token to use
  to connect to Discord. See the excellent [guide provided by
  `discord.py`](https://discordpy.readthedocs.io/en/latest/discord.html)
  for info on how to create a bot account and invite it to your server.
- `LOG_LEVEL`: Specifies the minimum severity level of log messages to
  produce. Valid values (in descending order of severity) are:
  `emergency`, `alert`, `critical`, `error`, `warning`, `notice`,
  `info`, `debuga`. It is not recommended to set this any higher than
  `error`.

If you just want to run the bot locally to test it though, you can do
so using the `scripts/run.sh` script. It utilizes the exact same
environment variables that the Docker image does.

## Data Sets

Roll35 comes bundled with a usable dataset for Pathfinder
1e. This includes the data for the official tables from
[D20PFSRD](https://www.d20pfsrd.com/) that are needed for all of the
features the bot provides. In all cases where it matters, this uses data
from unchained class variants (this primarily affects spell availability,
as the unchained variant of the summoner has a different spell list from
the regular variant).

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
  (they either have missing ranges of dice values, or have specific
  values that correlate to multiple items, or have ranges that are
  logically swapped). If ranges are missing, we behave as if they
  simply did not exist (that is, all the other items keep their
  proper relative proportions), and if there are duplicate values we
  adjust accordingly. All such cases are documented in comments in the
  files in `apps/roll35_core/priv`.

Spell data is pulled from the spell database on
[D20PFSRD](https://www.d20pfsrd), converted to the required format
using the `convert_spells_csv.py` script bundled with the app, with a
few manual fixes to the dataset (mostly correcting tags).

## Versions

The project uses semantic versioning, but it only increases the major
and minor versions for **user visible** changes. In other words, a change
that only alters the internal API without resulting in any user-visible
changes will translate to a patch release at the project level, not a
major relese. Additionally, some non-breaking changes at the project
level may result in a major release at the project level simply because
they are so impactful that they warrant a major release.

#### Why are there no published images for versions prior to 1.2.0?

My initial plan was to make the code public and publish Docker images
with version 1.0.0. However, there were a handful of bugs I found
just after preparing v1.0.0, as well as a number of other refactoring
changes I decided to make before going public. I would much rather not
rewrite git history just to make versions sync up correctly with tags,
so I opted to just release v1.2.0 as the first public verson.
