defmodule Roll35Bot.Weapon do
  @moduledoc """
  A command to roll random mundane weapon.
  """

  use Alchemy.Cogs

  alias Roll35Core.Data.Weapon
  alias Roll35Core.Renderer

  require Logger

  Cogs.set_parser(:weapon, fn i -> [i] end)

  Cogs.def weapon(options) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info(
      "Recieved weapon command with parameters #{inspect(options)} from #{user}##{tag}."
    )

    try do
      case cmd(options) do
        {:ok, msg} ->
          Cogs.say(msg)

        {:error, msg} ->
          Cogs.say("ERROR: #{msg}")

        result ->
          Cogs.say("An unknown error occurred, check the bot logs for more info.")
          Logger.error("Recieved unknown return value in weapon command: #{inspect(result)}")
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
  @spec cmd(String.t()) :: {:ok | :error, String.t()}
  def cmd(options) do
    _ = Weapon.tags({:via, Registry, {Roll35Core.Registry, :weapon}})

    tags =
      options
      |> String.split(" ", trim: true)
      |> Enum.map(&String.to_existing_atom/1)

    if item = Weapon.random_base({:via, Registry, {Roll35Core.Registry, :weapon}}, tags) do
      {:ok, Renderer.format(item)}
    else
      {:error, "No items matching specified tags (#{Enum.map(tags, &Atom.to_string/1)})."}
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
