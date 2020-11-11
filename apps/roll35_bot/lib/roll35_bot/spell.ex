defmodule Roll35Bot.Spell do
  @moduledoc """
  A command to roll random spells.
  """

  use Alchemy.Cogs

  alias Roll35Core.Data.Spell

  require Logger

  Cogs.set_parser(:spell, fn rest -> [String.split(rest)] end)

  Cogs.def spell(params) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info("Recieved spell command with parameters #{inspect(params)} from #{user}##{tag}.")

    try do
      case cmd(params) do
        {:ok, msg} ->
          Cogs.say(msg)

        {:error, msg} ->
          Cogs.say("ERROR: #{msg}")

        result ->
          Cogs.say("An unknown error occurred, check the bot logs for more info.")
          Logger.error("Recieved unknown return value in spell command: #{inspect(result)}")
      end
    rescue
      e ->
        Cogs.say("ERROR: An internal error occurred, please check the bot logs for more info.")
        reraise e, __STACKTRACE__
    catch
      :exit, info ->
        Cogs.say("ERROR: An internal error occurred, please check the bot logs for more info.")
        exit(info)
    end
  end

  @doc """
  Actual command logic.
  """
  @spec cmd(term) :: {:ok | :error, String.t()}
  def cmd(params) do
    opts =
      Enum.reduce_while(params, %{level: nil, class: nil, tag: nil}, fn item, acc ->
        cond do
          String.starts_with?(item, "level:") ->
            ["level", value] = String.split(item, ":")

            {:cont, Map.put(acc, :level, String.to_integer(value))}

          String.starts_with?(item, "class:") ->
            ["class", value] = String.split(item, ":")

            {:cont, Map.put(acc, :class, value)}

          String.starts_with?(item, "tag:") ->
            ["tag", value] = String.split(item, ":")

            {:cont, Map.put(acc, :tag, value)}

          true ->
            {:halt, item}
        end
      end)

    if is_map(opts) do
      Spell.random({:via, Registry, {Roll35Core.Registry, :spell}},
        level: opts.level,
        class: opts.class,
        tag: opts.tag
      )
    else
      {:error, "Unrecognized parameter #{opts}."}
    end
  end

  @doc """
  Return help text for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 spell [level:<level>] [class:<class>] [tag:<tag>]`

    Roll a random spell, optionally limited by level, class, or tag.

    Examples:

    Roll a random first level wizard spell:
    `/roll35 spell level:1 class:wizard`

    Roll a random necromancy spell from the cleric spell list:
    `/roll35 spell tag:necromancy class:cleric`

    Roll a spell from a random class
    `/roll35 spell class:random`

    The level specifier must be an integer between 0 and 9 inclusive.

    The class specifier must be a lower-case class name with any spaces replaced with `_`, or one of the following special terms:

    * `minimum`: Evaluate the level based on the minimum level the spell appears on any class list. This is the default behavior if no class is specified. This is the bheaviour expected for potions and wands found as magic items.
    * `random`: Pick a class at random and roll a spell from that class.
    * `spellpage_arcane`: Use the rules for an arcane ‘Page of Spell Knowledge’ to evaluate the level (more specifically, if the spell is on the wizard list, use the level it appears ther,e otherwise use the highest level it appears on any arcane spellcaster class’s list).
    * `spellpage_divine`: Same as `spellpage_arcane`, but for a divine ‘Page of Spell Knowledge’ (using divne spellcasting classes and the cleric list).
    * `spellpage`: Pick one of `spellpage_arcane` or `spellpage_divine` at random.

    The tag specifier must be all lower-case with any spaces or `-` replaced with `_`. It matches on any of the school, sub-school, or descriptors for the spell.

    If a specifier is listed more than once, only the last one is honored.
    """
  end
end
