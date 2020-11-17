defmodule Roll35Bot.Commands.Weapon do
  @moduledoc """
  A command to roll random mundane weapon.
  """

  @behaviour Roll35Bot.Command

  use Alchemy.Cogs

  alias Roll35Bot.Renderer
  alias Roll35Core.Data.Weapon

  Cogs.set_parser(:weapon, &List.wrap/1)

  Cogs.def weapon(options) do
    Roll35Bot.Command.run_cmd(
      "weapon",
      options,
      [strict: []],
      message,
      __MODULE__,
      &Cogs.say/1
    )
  end

  @impl Roll35Bot.Command
  def cmd(args, _) do
    _ = Weapon.tags({:via, Registry, {Roll35Core.Registry, :weapon}})

    tags = Enum.map(args, &String.to_existing_atom/1)

    if item = Weapon.random_base({:via, Registry, {Roll35Core.Registry, :weapon}}, tags) do
      {:ok, Renderer.format(item)}
    else
      {:error, "No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)})."}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random weapons."

  @impl Roll35Bot.Command
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
