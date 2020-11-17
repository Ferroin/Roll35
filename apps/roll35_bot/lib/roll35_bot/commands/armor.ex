defmodule Roll35Bot.Commands.Armor do
  @moduledoc """
  A command to roll random mundane armor.
  """

  @behaviour Roll35Bot.Command

  use Alchemy.Cogs

  alias Roll35Bot.Renderer
  alias Roll35Core.Data.Armor

  Cogs.set_parser(:armor, &List.wrap/1)

  Cogs.def armor(options) do
    Roll35Bot.Command.run_cmd(
      "armor",
      options,
      [strict: []],
      message,
      __MODULE__,
      &Cogs.say/1
    )
  end

  @impl Roll35Bot.Command
  def cmd(args, _) do
    _ = Armor.tags({:via, Registry, {Roll35Core.Registry, :armor}})

    tags = Enum.map(args, &String.to_existing_atom/1)

    if item = Armor.random_base({:via, Registry, {Roll35Core.Registry, :armor}}, tags) do
      {:ok, Renderer.format(item)}
    else
      {:error, "No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)})."}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random armor and shield items."

  @impl Roll35Bot.Command
  def help do
    """
    Usage:

    `/roll35 armor [tags]`

    Roll a random mundane armor or shield item.

    The optional `tags` parameter is a space-separated list of tags used to filter the full list of armor and shields before selecting one randomly. For example, one can select a random item of light armor with:

    `/roll35 armor light armor`

    The exact order of tags is not significant.
    """
  end
end
