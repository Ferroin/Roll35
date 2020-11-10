defmodule Roll35Bot.Armor do
  @moduledoc """
  A command to roll random mundane armor.
  """

  use Alchemy.Cogs

  alias Roll35Core.Data.Armor
  alias Roll35Core.Renderer

  Cogs.set_parser(:armor, fn i -> [i] end)

  Cogs.def armor(options) do
    _ = Armor.tags({:via, Registry, {Roll35Core.Registry, :armor}})

    tags =
      options
      |> String.split(" ", trim: true)
      |> Enum.map(&String.to_existing_atom/1)

    if item = Armor.random_base({:via, Registry, {Roll35Core.Registry, :armor}}, tags) do
      Cogs.say(Renderer.format(item))
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

    `/roll35 armor [tags]`

    Roll a random mundane armor or shield item.

    The optional `tags` parameter is a space-separated list of tags used to filter the full list of armor and shields before selecting one randomly. For example, one can select a random item of light armor with:

    `/roll35 armor light armor`

    The exact order of tags is not significant.
    """
  end
end
