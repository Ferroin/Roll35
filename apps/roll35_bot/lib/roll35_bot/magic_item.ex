defmodule Roll35Bot.MagicItem do
  @moduledoc """
  Command to roll rando magic items.
  """

  use Alchemy.Cogs

  alias Roll35Core.MagicItem
  alias Roll35Core.Types

  require Logger

  Cogs.set_parser(:magicitem, fn rest -> [String.split(rest, " ", trim: true)] end)

  Cogs.def magicitem(params) do
    %Alchemy.Message{
      author: %Alchemy.User{
        username: user,
        discriminator: tag
      }
    } = message

    Logger.info("Recieved armor command with parameters #{inspect(params)} from #{user}##{tag}.")

    try do
      case cmd(params) do
        {:ok, msg} ->
          Cogs.say(msg)

        {:error, msg} ->
          Cogs.say("ERROR: #{msg}")

        result ->
          Cogs.say("An unknown error occurred, check the bot logs for more info.")
          Logger.error("Recieved unknown return value in magicitem command: #{inspect(result)}")
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
  def cmd(params) do
    invalid_params =
      MapSet.difference(
        MapSet.new(params),
        MapSet.new(
          [Types.ranks(), Types.full_subranks(), Types.categories(), Types.slots()]
          |> Enum.concat()
          |> Enum.map(&Atom.to_string/1)
        )
      )

    if MapSet.size(invalid_params) == 0 do
      slot =
        params
        |> Enum.filter(fn item ->
          item in Enum.map(Types.slots(), &Atom.to_string/1)
        end)
        |> Enum.at(-1)
        |> (fn
              nil -> nil
              item -> String.to_existing_atom(item)
            end).()

      category =
        if slot == nil do
          params
          |> Enum.filter(fn item ->
            item in Enum.map(Types.categories(), &Atom.to_string/1)
          end)
          |> Enum.at(-1)
          |> (fn
                nil -> nil
                item -> String.to_existing_atom(item)
              end).()
        else
          :wondrous
        end

      rank =
        if category in [:rod, :staff] do
          params
          |> Enum.filter(fn item ->
            item in Enum.map(Types.ranks(), &Atom.to_string/1)
          end)
          |> Enum.at(-1)
          |> (fn
                nil -> Enum.random(Types.limited_ranks())
                item -> String.to_existing_atom(item)
              end).()
        else
          params
          |> Enum.filter(fn item ->
            item in Enum.map(Types.ranks(), &Atom.to_string/1)
          end)
          |> Enum.at(-1)
          |> (fn
                nil -> Enum.random(Types.ranks())
                item -> String.to_existing_atom(item)
              end).()
        end

      subrank =
        params
        |> Enum.filter(fn item ->
          item in Enum.map(Types.full_subranks(), &Atom.to_string/1)
        end)
        |> Enum.at(-1)
        |> (fn
              nil -> Enum.random(Types.subranks())
              item -> String.to_existing_atom(item)
            end).()

      cond do
        slot != nil and category != nil and category != :wondrous ->
          {:error, "Slots may only be specified for wondrous items."}

        category in [:rod, :staff] and rank == :minor ->
          {:error, "#{category} items have no minor rank options."}

        subrank == :least and slot != :slotless ->
          {:error, "Only slotless items have a least subrank."}

        true ->
          MagicItem.roll(rank, subrank, category, slot)
      end
    else
      {:error, "Unrecognized parameters #{Enum.join(MapSet.to_list(invalid_params), ", ")}."}
    end
  end

  @doc """
  Return help text for this command.
  """
  @spec help :: String.t()
  def help do
    """
    Usage:

    `/roll35 magicitem [[least|lesser|greater] minor|medium|major] [armor|weapon|potion|ring|rod|scroll|staff|wand|wondrous] [<extra>]`

    Roll a random magic item of the specified type. Exact order of parameters is not relevant.

    If the type is `wondrous` or unspecified, you can specify a slot by lowercase name as the `<extra>` parameter. Any parameters not specified are determined randomly.

    Examples:

    Roll a random lesser major item: `/roll35 magicitem lesser major`

    Roll a random scroll: `/roll35 magicitem scroll`

    Roll a random major magic weapon: `/roll35 magicitem major weapon`

    Roll a random belt slot item: `/roll35 magicitem wondrous belt` or `/roll35 magicitem belt`

    Roll a completely random magic item: `roll35 magicitem`
    """
  end
end
