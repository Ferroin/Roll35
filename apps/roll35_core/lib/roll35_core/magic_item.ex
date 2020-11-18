defmodule Roll35Core.MagicItem do
  @moduledoc """
  Code to actually roll for (and dispatch rendering of) a magic item.
  """

  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger

  @compound_itemlists [:potion, :scroll, :wand]
  @ranked_itemlists [:ring, :rod, :staff]
  @max_tries 3

  defp modname(:armor), do: Roll35Core.Data.Armor
  defp modname(:belt), do: Roll35Core.Data.Belt
  defp modname(:body), do: Roll35Core.Data.Body
  defp modname(:category), do: Roll35Core.Data.Category
  defp modname(:chest), do: Roll35Core.Data.Chest
  defp modname(:eyes), do: Roll35Core.Data.Eyes
  defp modname(:feet), do: Roll35Core.Data.Feet
  defp modname(:hand), do: Roll35Core.Data.Hand
  defp modname(:headband), do: Roll35Core.Data.Headband
  defp modname(:head), do: Roll35Core.Data.Head
  defp modname(:neck), do: Roll35Core.Data.Neck
  defp modname(:potion), do: Roll35Core.Data.Potion
  defp modname(:ring), do: Roll35Core.Data.Ring
  defp modname(:rod), do: Roll35Core.Data.Rod
  defp modname(:scroll), do: Roll35Core.Data.Scroll
  defp modname(:shoulders), do: Roll35Core.Data.Shoulders
  defp modname(:slotless), do: Roll35Core.Data.Slotless
  defp modname(:spell), do: Roll35Core.Data.Spell
  defp modname(:staff), do: Roll35Core.Data.Staff
  defp modname(:wand), do: Roll35Core.Data.Wand
  defp modname(:weapon), do: Roll35Core.Data.Weapon
  defp modname(:wondrous), do: Roll35Core.Data.Wondrous
  defp modname(:wrists), do: Roll35Core.Data.Wrists

  defp server(:armor), do: {:via, Registry, {Roll35Core.Registry, :armor}}
  defp server(:belt), do: {:via, Registry, {Roll35Core.Registry, :belt}}
  defp server(:body), do: {:via, Registry, {Roll35Core.Registry, :body}}
  defp server(:category), do: {:via, Registry, {Roll35Core.Registry, :category}}
  defp server(:chest), do: {:via, Registry, {Roll35Core.Registry, :chest}}
  defp server(:eyes), do: {:via, Registry, {Roll35Core.Registry, :eyes}}
  defp server(:feet), do: {:via, Registry, {Roll35Core.Registry, :feet}}
  defp server(:hand), do: {:via, Registry, {Roll35Core.Registry, :hand}}
  defp server(:headband), do: {:via, Registry, {Roll35Core.Registry, :headband}}
  defp server(:head), do: {:via, Registry, {Roll35Core.Registry, :head}}
  defp server(:neck), do: {:via, Registry, {Roll35Core.Registry, :neck}}
  defp server(:potion), do: {:via, Registry, {Roll35Core.Registry, :potion}}
  defp server(:ring), do: {:via, Registry, {Roll35Core.Registry, :ring}}
  defp server(:rod), do: {:via, Registry, {Roll35Core.Registry, :rod}}
  defp server(:scroll), do: {:via, Registry, {Roll35Core.Registry, :scroll}}
  defp server(:shoulders), do: {:via, Registry, {Roll35Core.Registry, :shoulders}}
  defp server(:slotless), do: {:via, Registry, {Roll35Core.Registry, :slotless}}
  defp server(:spell), do: {:via, Registry, {Roll35Core.Registry, :spell}}
  defp server(:staff), do: {:via, Registry, {Roll35Core.Registry, :staff}}
  defp server(:wand), do: {:via, Registry, {Roll35Core.Registry, :wand}}
  defp server(:weapon), do: {:via, Registry, {Roll35Core.Registry, :weapon}}
  defp server(:wondrous), do: {:via, Registry, {Roll35Core.Registry, :wondrous}}
  defp server(:wrists), do: {:via, Registry, {Roll35Core.Registry, :wrists}}

  @spec call(atom(), atom(), [term()]) :: term()
  defp call(target, function, opts \\ []) do
    apply(modname(target), function, [server(target) | opts])
  end

  @spec finalize_roll(map()) :: {:ok, Types.item()} | {:error, term()}
  defp finalize_roll(item) do
    case item do
      {:error, msg} ->
        {:error, msg}

      {:ok, msg} ->
        {:ok, msg}

      item ->
        if Map.has_key?(item, :reroll) do
          reroll(item.reroll)
        else
          {:ok, item}
        end
    end
  end

  @spec bonus_costs(:armor | :weapon, map()) :: {non_neg_integer(), non_neg_integer()}
  defp bonus_costs(type, item) do
    cond do
      type == :armor -> {150, 1000}
      type == :weapon and :double in item.tags -> {600, 4000}
      type == :weapon -> {300, 2000}
    end
  end

  @doc """
  Assemble a magic weapon or armor item.
  """
  @spec assemble_magic_item(atom, map, map, non_neg_integer, non_neg_integer, non_neg_integer) ::
          {:ok, String.t()} | {:error, String.t()}
  def assemble_magic_item(type, item, base, cost_mult, masterwork, iter \\ 0) do
    Logger.debug(
      "Assembling magic item of type #{inspect(type)} with parameters #{inspect(item)}."
    )

    base_cost = base.cost + masterwork
    item_cost = base_cost + Util.squared(item.bonus) * cost_mult

    {cost, enchants, _, _, _} =
      Enum.reduce_while(
        item.enchants,
        {item_cost, [], item.bonus, base_cost, MapSet.new(base.tags)},
        fn ench, {_item_cost, enchants, enchant_bonus, extra_cost, tags} ->
          enchantment =
            call(type, :random_enchantment, [base.type, ench, enchants, MapSet.to_list(tags)])

          if enchantment == nil do
            {:halt, {nil, nil, nil, nil, nil}}
          else
            {bonus, extra} =
              if Map.has_key?(enchantment, :cost) do
                {enchant_bonus, extra_cost + enchantment.cost}
              else
                {enchant_bonus + ench, extra_cost}
              end

            new_tags =
              tags
              |> (fn item ->
                    if Map.has_key?(enchantment, :add) do
                      MapSet.union(tags, MapSet.new(enchantment.add))
                    else
                      item
                    end
                  end).()
              |> (fn item ->
                    if Map.has_key?(enchantment, :remove) do
                      MapSet.difference(tags, MapSet.new(enchantment.remove))
                    else
                      item
                    end
                  end).()

            cost = Util.squared(bonus + item.bonus) * cost_mult + extra

            {:cont, {cost, [enchantment | enchants], bonus, extra, new_tags}}
          end
        end
      )

    cond do
      enchants == nil and iter >= @max_tries ->
        {:error, "Too many failed attempts to select enchantments."}

      enchants == nil and iter < @max_tries ->
        assemble_magic_item(type, item, base, cost_mult, masterwork, iter + 1)

      true ->
        {:ok,
         %{
           name:
             "+#{item.bonus} #{enchants |> Enum.map(& &1.name) |> Enum.join(" ")} #{base.name}",
           cost: cost
         }}
    end
  end

  @doc """
  Dispatch a reroll based on a reroll path.

  This is mostly a helper function to keep the `roll/1` function tidy.
  """
  @spec reroll(list()) :: {:ok, Types.item()} | {:error, term()}
  def reroll(path) do
    Logger.debug("Rerolling item with parameters #{inspect(path)}.")

    case path do
      [category, extra, rank, subrank] ->
        roll(rank, subrank, category, extra)

      [category, rank, subrank] ->
        roll(rank, subrank, category)

      _ ->
        {:error, "Invalid reroll directive found while rolling for magic item."}
    end
  end

  @doc """
  Roll a magic item.

  This takes a keyword list specifying how to get to the item in question.
  """
  @spec roll(Types.rank(), Types.full_subrank(), Types.category(), term()) ::
          {:ok, Types.item()} | {:error, term()}
  def roll(rank, subrank, category, extra \\ nil) do
    Logger.debug(
      "Rolling magic item with parameters #{inspect({rank, subrank, category, extra})}."
    )

    item =
      cond do
        category != :wondrous and extra != :slotless and subrank == :least ->
          {:error, "Only slotless wondrous items have a least subrank."}

        category in [:rod, :staff] and rank == :minor ->
          {:error,
           "#{category |> Atom.to_string() |> String.capitalize()} items do not have a minor rank."}

        category == :wondrous and extra == nil ->
          slot = call(:wondrous, :random)

          call(slot, :random, [rank, subrank])

        category == nil and extra != nil ->
          call(extra, :random, [rank, subrank])

        category == :wondrous ->
          call(extra, :random, [rank, subrank])

        category in [:armor, :weapon] ->
          pattern = call(category, :random, [rank, subrank])

          if Map.has_key?(pattern, :specific) do
            call(
              category,
              :random_specific,
              Enum.map(pattern.specific, fn i -> String.to_existing_atom(i) end)
            )
          else
            base = call(category, :random_base, [])

            {masterwork, bonus_cost} = bonus_costs(category, base)

            assemble_magic_item(
              category,
              pattern,
              base,
              bonus_cost,
              masterwork
            )
          end

        category in [:wand, :scroll] and extra in call(:spell, :get_classes, []) ->
          item = call(category, :random, [rank])

          Map.update(item, :spell, %{}, fn spell ->
            Map.put(spell, :cls, extra)
          end)

        category in @compound_itemlists ->
          call(category, :random, [rank])

        category in @ranked_itemlists ->
          call(category, :random, [rank, subrank])

        category == nil ->
          category = call(:category, :random, [rank])

          roll(rank, subrank, category)

        true ->
          {:error, "Invalid item category."}
      end

    finalize_roll(item)
  end
end
