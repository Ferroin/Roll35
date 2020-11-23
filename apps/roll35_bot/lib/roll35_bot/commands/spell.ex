defmodule Roll35Bot.Commands.Spell do
  @moduledoc """
  A command to roll random spells.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  alias Roll35Core.Data.Spell

  @spell_server {:via, Registry, {Roll35Core.Registry, :spell}}

  Cogs.set_parser(:spell, &List.wrap/1)

  Cogs.def spell(options) do
    Roll35Bot.Command.run_cmd(__MODULE__, options, message, &Cogs.say/1)
  end

  @impl Roll35Bot.Command
  def cmd(args, options) do
    if args == [] do
      Spell.random(@spell_server, options)
    else
      {:error, "`/roll35 spell` command does not take any positional parameters.`"}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random spells, optionally limited by level, class, or tag."

  @impl Roll35Bot.Command
  def extra_help, do: ""

  @impl Roll35Bot.Command
  def options do
    [
      {:level, :integer, fn -> 0..9 end,
       "Optionally specify the level for the spell. Must be a number between 0 and 9 inclusive."},
      {:class, :string, fn -> Spell.get_classes(@spell_server) end,
       """
       Optionally specify a class for the spell. Must be a lower-case class name (such as `wizard`) with any spaces replaced with `_`, or one of the of the following special terms:
           * `minimum`: Evaluate the level based on the minimum level the spell appears on any class list. This is the default behavior if no class is specified. This is the behavior expected for potions and wands found as magic items.
           * `random`: Pick a class at random and roll a spell from that class. This is the behavior expected for scrolls found as magic items.
           * `spellpage_arcane`: Use the rules for an arcane ‘Page of Spell Knowledge’ to evaluate the level (more specifically, if the spell is on the wizard list, use the level it appears ther,e otherwise use the highest level it appears on any arcane spellcaster class’s list).
           * `spellpage_divine`: Same as `spellpage_arcane`, but for a divine ‘Page of Spell Knowledge’ (using divne spellcasting classes and the cleric list).
           * `spellpage`: Pick one of `spellpage_arcane` or `spellpage_divine` at random.
       """},
      {:tag, :string, fn -> Spell.get_tags(@spell_server) end,
       "Optionally specify a tag to limit the possible results by. Matches on any of the school, sub-school, or descriptors for the spell, must be lower-case with any `-` replaced by `_`."}
    ]
  end
end
