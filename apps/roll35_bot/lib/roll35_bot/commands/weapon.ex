defmodule Roll35Bot.Commands.Weapon do
  @moduledoc """
  A command to roll random mundane weapon.
  """

  use Roll35Bot.Command
  use Alchemy.Cogs

  alias Roll35Bot.Renderer
  alias Roll35Core.Data.Weapon

  @weapon_server {:via, Registry, {Roll35Core.Registry, :weapon}}

  Cogs.set_parser(:weapon, &List.wrap/1)

  Cogs.def weapon(options) do
    Roll35Bot.Command.run_cmd(
      __MODULE__,
      options,
      message,
      &Cogs.say/1
    )
  end

  @impl Roll35Bot.Command
  def cmd(args, _) do
    _ = Weapon.tags(@weapon_server)

    tags = Enum.map(args, &String.to_existing_atom/1)

    if item = Weapon.random_base(@weapon_server, tags) do
      {:ok, Renderer.format(item)}
    else
      {:error, "No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)})."}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random weapons."

  @impl Roll35Bot.Command
  def extra_help do
    """
    The optional `tags` parameter is a space-separated list of tags used to filter the full list of weapons before selecting one randomly.

    The exact order of tags is not significant.
    """
  end

  @impl Roll35Bot.Command
  def param_names, do: "[<tags>]"

  @impl Roll35Bot.Command
  def sample_params do
    Enum.random(Weapon.tags(@weapon_server))
  end
end
