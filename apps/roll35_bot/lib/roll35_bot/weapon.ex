defmodule Roll35Bot.Weapon do
  @moduledoc """
  A command to roll random mundane weapon.
  """

  use Alchemy.Cogs

  alias Roll35Core.Data.Weapon

  Cogs.set_parser(:weapon, fn i -> [i] end)

  Cogs.def weapon(options) do
    _ = Weapon.tags({:via, Registry, {Roll35Core.Registry, :weapon}})

    tags =
      options
      |> String.split(" ", trim: true)
      |> Enum.map(&String.to_existing_atom/1)

    if item = Weapon.random_base({:via, Registry, {Roll35Core.Registry, :weapon}}, tags) do
      Cogs.say("#{item.name} (cost: #{item.cost}gp)")
    else
      Cogs.say("No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)}).")
    end
  end

  @doc """
  Return help text for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 weapon [tags]`

    Roll a random mundane weapon item.

    The optional `tags` parameter is a space-separated list of tags used to filter the full list of weapons before selecting one randomly. For example, one can select a random light melee weapon with:

    `/roll35 weapon light melee`

    The exact order of tags is not significant.
    """
  end
end
