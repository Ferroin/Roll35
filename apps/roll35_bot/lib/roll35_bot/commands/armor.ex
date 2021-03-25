defmodule Roll35Bot.Commands.Armor do
  @moduledoc """
  A command to roll random mundane armor.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  alias Roll35Bot.Renderer
  alias Roll35Core.Data.Armor

  @armor_server {:via, Registry, {Roll35Core.Registry, :armor}}

  Cogs.set_parser(:armor, &List.wrap/1)

  Cogs.def armor(options) do
    Roll35Bot.Command.run_cmd(
      __MODULE__,
      options,
      message,
      &Cogs.say/1
    )
  end

  Cogs.def ar(options) do
    Roll35Bot.Command.run_cmd(
      __MODULE__,
      options,
      message,
      &Cogs.say/1
    )
  end

  @impl Roll35Bot.Command
  def cmd(args, _) do
    _ = Armor.tags(@armor_server)

    tags = Enum.map(args, &String.to_existing_atom/1)

    if item = Armor.random_base(@armor_server, tags) do
      {:ok, Renderer.format(item)}
    else
      {:error, "No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)})."}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random armor and shield items."

  @impl Roll35Bot.Command
  def extra_help do
    """
    Aliases: `/roll35 ar`

    The optional `tags` parameter is a space-separated list of tags used to filter the full list of armor and shields before selecting one randomly.

    The exact order of tags is not significant.
    """
  end

  @impl Roll35Bot.Command
  def param_names, do: "[<tags>]"

  @impl Roll35Bot.Command
  def sample_params do
    @armor_server
    |> Armor.tags()
    |> Enum.random()
    |> Atom.to_string()
  end
end
