defmodule Roll35Bot.Commands.Spell do
  @moduledoc """
  A command to roll random spells.
  """

  @behaviour Roll35Bot.Command

  use Alchemy.Cogs

  alias Roll35Core.Data.Spell

  Cogs.set_parser(:spell, &List.wrap/1)

  Cogs.def spell(options) do
    Roll35Bot.Command.run_cmd(
      "spell",
      options,
      [
        strict: [
          level: :integer,
          class: :string,
          tag: :string
        ]
      ],
      message,
      __MODULE__,
      &Cogs.say/1
    )
  end

  @impl Roll35Bot.Command
  def cmd(args, options) do
    if args == [] do
      Spell.random({:via, Registry, {Roll35Core.Registry, :spell}}, options)
    else
      {:error, "`/roll35 spell` command does not take any positional parameters.`"}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random spells."

  @impl Roll35Bot.Command
  def help do
    """
    Usage:

    `/roll35 spell [--level <level>] [--class <class>] [--tag <tag>]`

    Roll a random spell, optionally limited by level, class, or tag.

    Examples:

    Roll a random first level wizard spell:
    `/roll35 spell --level 1 --class wizard`

    Roll a random necromancy spell from the cleric spell list:
    `/roll35 spell --tag necromancy --class cleric`

    Roll a spell from a random class
    `/roll35 spell --class random`

    The level specifier must be an integer between 0 and 9 inclusive.

    The class specifier must be a lower-case class name with any spaces replaced with `_`, or one of the following special terms:

    * `minimum`: Evaluate the level based on the minimum level the spell appears on any class list. This is the default behavior if no class is specified. This is the bheaviour expected for potions and wands found as magic items.
    * `random`: Pick a class at random and roll a spell from that class.
    * `spellpage_arcane`: Use the rules for an arcane ‘Page of Spell Knowledge’ to evaluate the level (more specifically, if the spell is on the wizard list, use the level it appears ther,e otherwise use the highest level it appears on any arcane spellcaster class’s list).
    * `spellpage_divine`: Same as `spellpage_arcane`, but for a divine ‘Page of Spell Knowledge’ (using divne spellcasting classes and the cleric list).
    * `spellpage`: Pick one of `spellpage_arcane` or `spellpage_divine` at random.

    The tag specifier must be all lower-case with any spaces or `-` replaced with `_`. It matches on any of the school, sub-school, or descriptors for the spell.
    """
  end
end
