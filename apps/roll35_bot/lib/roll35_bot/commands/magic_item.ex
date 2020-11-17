defmodule Roll35Bot.Commands.MagicItem do
  @moduledoc """
  Command to roll rando magic items.
  """

  @behaviour Roll35Bot.Command

  use Alchemy.Cogs

  alias Roll35Bot.Renderer
  alias Roll35Core.Data.Spell
  alias Roll35Core.MagicItem
  alias Roll35Core.Types

  Cogs.set_parser(:magicitem, &List.wrap/1)

  Cogs.def magicitem(options) do
    Roll35Bot.Command.run_cmd(
      "magicitem",
      options,
      [
        strict: [
          rank: :string,
          subrank: :string,
          type: :string,
          slot: :string,
          class: :string
        ]
      ],
      message,
      __MODULE__,
      &Cogs.say/1
    )
  end

  defp arg_to_atom(arg) do
    arg
    |> String.downcase()
    |> String.to_existing_atom()
  end

  defp check_arg(:type, value, acc, _classes) do
    vatom = arg_to_atom(value)

    if vatom in Types.categories() do
      {:cont, Map.put(acc, :category, vatom)}
    else
      {:halt,
       "Invalid value for type. Valid types are: #{
         Types.categories()
         |> Enum.map(&Atom.to_string/1)
         |> Enum.join(", ")
       }"}
    end
  end

  defp check_arg(:rank, value, acc, _classes) do
    vatom = arg_to_atom(value)

    if vatom in Types.ranks() do
      {:cont, Map.put(acc, :rank, vatom)}
    else
      {:halt,
       "Invalid value for item rank. Valid ranks are: #{
         Types.ranks()
         |> Enum.map(&Atom.to_string/1)
         |> Enum.join(", ")
       }"}
    end
  end

  defp check_arg(:subrank, value, acc, _classes) do
    vatom = arg_to_atom(value)

    if vatom in Types.full_subranks() do
      {:cont, Map.put(acc, :subrank, vatom)}
    else
      {:halt,
       "Invalid value for item subrank. Valid subranks are: #{
         Types.full_subranks()
         |> Enum.map(&Atom.to_string/1)
         |> Enum.join(", ")
       }"}
    end
  end

  defp check_arg(:slot, value, acc, _classes) do
    vatom = arg_to_atom(value)

    if vatom in Types.slots() do
      {:cont, Map.put(acc, :slot, vatom)}
    else
      {:halt,
       "Invalid value for item slot. Valid slots are: #{
         Types.slots()
         |> Enum.map(&Atom.to_string/1)
         |> Enum.join(", ")
       }"}
    end
  end

  defp check_arg(:class, value, acc, classes) do
    vatom = arg_to_atom(value)

    if vatom in classes do
      {:cont, Map.put(acc, :class, vatom)}
    else
      {:halt,
       "Invalid value for caster class. Valid classes are: #{
         classes
         |> Enum.map(&Atom.to_string/1)
         |> Enum.join(", ")
       }"}
    end
  end

  defp get_params(opts) do
    spell_classes = Spell.get_classes({:via, Registry, {Roll35Core.Registry, :spell}})

    params =
      Enum.reduce_while(
        opts,
        %{category: nil, rank: nil, subrank: nil, slot: nil, class: nil},
        fn {key, value}, acc ->
          check_arg(key, value, acc, spell_classes)
        end
      )

    if is_binary(params) do
      {:error, params}
    else
      {:ok,
       params
       |> (fn map ->
             if map.slot != nil and map.category == nil do
               Map.put(map, :category, :wondrous)
             else
               map
             end
           end).()
       |> (fn map ->
             cond do
               map.rank == nil and map.category in [:rod, :staff] ->
                 Map.put(map, :rank, Enum.random(Types.limited_ranks()))

               map.rank == nil ->
                 Map.put(map, :rank, Enum.random(Types.ranks()))

               true ->
                 map
             end
           end).()
       |> (fn map ->
             case map.subrank do
               nil -> Map.put(map, :subrank, Enum.random(Types.subranks()))
               _ -> map
             end
           end).()
       |> (fn map ->
             {
               map.category,
               map.class,
               map.rank,
               map.slot,
               map.subrank
             }
           end).()}
    end
  end

  @impl Roll35Bot.Command
  def cmd(args, opts) do
    case get_params(opts) do
      {:ok,
       {
         category,
         class,
         rank,
         slot,
         subrank
       }} ->
        cond do
          args != [] ->
            {:error, "`/roll35 magicitem` command does not take any positional parameters."}

          class != nil and not Enum.member?([:scroll, :wand], category) ->
            {:error, "Spellcasting class may only be specified for scrolls and wands."}

          slot != nil and category != nil and category != :wondrous ->
            {:error, "Slots may only be specified for wondrous items."}

          category in [:rod, :staff] and rank == :minor ->
            {:error, "#{category} items have no minor rank options."}

          subrank == :least and slot != :slotless ->
            {:error, "Only slotless items have a least subrank."}

          class != nil ->
            case MagicItem.roll(rank, subrank, category, class) do
              {:ok, item} -> {:ok, Renderer.format(item)}
              {:error, msg} -> {:error, msg}
            end

          true ->
            case MagicItem.roll(rank, subrank, category, slot) do
              {:ok, item} -> {:ok, Renderer.format(item)}
              {:error, msg} -> {:error, msg}
            end
        end

      {:error, msg} ->
        {:error, msg}
    end
  end

  @impl Roll35Bot.Command
  def short_desc, do: "Roll random magic items."

  @impl Roll35Bot.Command
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
