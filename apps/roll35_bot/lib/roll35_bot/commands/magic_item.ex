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
          base: :string,
          class: :string,
          rank: :string,
          slot: :string,
          subrank: :string,
          type: :string
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

  defp check_arg(:base, value, acc, _classes) do
    {:cont, Map.put(acc, :base, value)}
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
               map.base,
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
         base,
         category,
         class,
         rank,
         slot,
         subrank
       }} ->
        cond do
          args != [] ->
            {:error, "`/roll35 magicitem` command does not take any positional parameters."}

          base != nil and category not in [:weapon, :armor] ->
            {:error, "Base item may only be specified when rolling for magic weapons or armor."}

          class != nil and not Enum.member?([:scroll, :wand], category) ->
            {:error, "Spellcasting class may only be specified for scrolls and wands."}

          slot != nil and category != nil and category != :wondrous ->
            {:error, "Slots may only be specified for wondrous items."}

          category in [:rod, :staff] and rank == :minor ->
            {:error, "#{category} items have no minor rank options."}

          subrank == :least and slot != :slotless ->
            {:error, "Only slotless items have a least subrank."}

          true ->
            {ret, msg} =
              cond do
                base != nil -> MagicItem.roll(rank, subrank, category, base: base)
                class != nil -> MagicItem.roll(rank, subrank, category, class: class)
                slot != nil -> MagicItem.roll(rank, subrank, category, slot: slot)
                true -> MagicItem.roll(rank, subrank, category)
              end

            {ret, Renderer.format(msg)}
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

    `/roll35 magicitem [--rank minor|medium|major] [--subrank least|lesser|greater] [--type armor|weapon|potion|ring|rod|scroll|staff|wand|wondrous] [--slot belt|body|chest|eyes|feet|hands|head|headband|neck|shoulders|wrists|slotless] [--class <class>] [--base <base>]`

    Roll a random magic item of the specified type. Exact order of parameters is not relevant.

    `--base`: Specifies a base item to use when rolling a magic weapon or magic armor. This is matched case insensitively, but the item name must be quoted if it contains spaces.
    `--class`: Specifies a spellcasting class to use for rolling wands and scrolls. Class names must be in lowercase with any spaces replaced with `_`. If specified, `--type` must also be specified and must be either `wand` or `scroll`.
    `--rank`: Specifies the item’s rank (minor/medium/major)
    `--slot`: Specifies the slot for a wondrous item. Rolled randomly if left unspecified. If passed without specifying a `--type`, the type is assumed to be `wondrous`.
    `--subrank`: Specifies the item’s sub-rank (least/lesser/greater)
    `--type`: Specifies the type of magic item. Rolled randomly if left unspecified.

    At least one of `--rank`, `--type` or `--slot` must be specified.

    If a parameter is specified more than once, the last instance specified gets used.
    """
  end
end
