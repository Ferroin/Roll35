defmodule Roll35Core.Data.ArmorTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Armor
  alias Roll35Core.Types

  alias Roll35Core.TestHarness

  describe "Roll35Core.Data.Armor.load_data/1" do
    setup do
      data = Armor.load_data()

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data), "Armor data is not a map."
    end

    test "Returned map has expected keys with expected value types.", context do
      assert Enum.all?(Map.keys(context.data), &is_atom/1), "Armor data keys are not all atoms."

      assert MapSet.new(Map.keys(context.data)) ==
               MapSet.new([:base, :specific, :enchantments, :tags | Types.ranks()]),
             "Armor data does not contain the correct set of keys (#{
               inspect(Map.keys(context.data))
             })."

      assert is_list(context.data.base), "Armor base item data is not a list."

      assert is_map(context.data.specific), "Armor specific item data is not a map."

      assert is_map(context.data.enchantments), "Armor enchantment data is not a map."

      assert Enum.all?(Types.ranks(), fn rank -> is_map(context.data[rank]) end),
             "Armor rank entries are not all maps."

      assert is_list(context.data.tags), "Armor tag data is not a list."
    end

    test "Rank maps have the correct format.", context do
      Types.ranks()
      |> Task.async_stream(fn rank ->
        data = context.data[rank]

        assert MapSet.new(Map.keys(data)) == MapSet.new(Types.subranks()) or
                 MapSet.new(Map.keys(data)) == MapSet.new(Types.full_subranks()),
               "Armor #{rank} data does not have subrank keys (#{inspect(Map.keys(data))})."

        Enum.each(data, fn {key, value} ->
          assert is_list(value), "Armor #{rank} #{key} data is not a list."

          value
          |> Enum.with_index()
          |> Enum.each(fn {item, index} ->
            prefix = "Armor #{rank} #{key} item #{index}"
            assert is_map(item), "#{prefix} is not a map."

            assert TestHarness.map_has_weighted_random_keys(item),
                   "#{prefix} does not have the correct keys (#{inspect(Map.keys(item))})."

            assert is_integer(item.weight), "#{prefix} weight key is not an integer."
            assert item.weight >= 0, "#{prefix} weight key is less than zero."

            assert is_map(item.value), "#{prefix} value key is not a map."

            assert Map.has_key?(item.value, :bonus) or Map.has_key?(item.value, :reroll),
                   "#{prefix} value map is missing a bonus or reroll key."

            if Map.has_key?(item.value, :bonus) do
              assert is_integer(item.value.bonus),
                     "#{prefix} value map bonus key is not an integer."

              assert item.value.bonus > 0, "#{prefix} value map bonus key is out of range."

              assert Map.has_key?(item.value, :enchants),
                     "#{prefix} value map is missing an enchants key."

              assert is_list(item.value.enchants),
                     "#{prefix} value map enchants key is not a list."

              if length(item.value.enchants) > 0 do
                item.value.enchants
                |> Enum.with_index()
                |> Enum.each(fn {enchant, index} ->
                  assert is_integer(enchant),
                         "#{prefix} value map enchants list item #{index} is not an integer."

                  assert enchant > 0,
                         "#{prefix} value map enchants list item #{index} is out of range."
                end)
              end
            end

            if Map.has_key?(item.value, :reroll) do
              assert is_binary(item.value.reroll),
                     "#{prefix} value map reroll key is not a string."
            end
          end)
        end)
      end)
      |> Enum.to_list()
    end

    test "Base list has the correct format.", context do
      context.data.base
      |> Enum.with_index()
      |> Task.async_stream(fn {entry, index} ->
        prefix = "Armor base items entry #{index}"

        assert is_map(entry), "#{prefix} is not a map."

        assert MapSet.new(Map.keys(entry)) == MapSet.new([:name, :cost, :type, :tags]),
               "#{prefix} does not have the correct keys (#{inspect(Map.keys(entry))})."

        assert is_binary(entry.name), "#{prefix} name key is not a string."

        assert is_integer(entry.cost) or is_float(entry.cost),
               "#{prefix} cost key is not a number."

        assert entry.cost >= 0, "#{prefix} cost key is less than zero."

        assert entry.type in [:armor, :shield], "#{prefix} type is not armor or shield."

        assert is_list(entry.tags), "#{prefix} tags key is not a list."
        assert Enum.all?(entry.tags, &is_atom/1), "#{prefix} tags entries are not all atoms."
      end)
      |> Enum.to_list()
    end

    test "Specific map has the correct format.", context do
      assert MapSet.new(Map.keys(context.data.specific)) == MapSet.new([:armor, :shield]),
             "Armor specific item map does not have correct keys (#{
               inspect(Map.keys(context.data.specific))
             })."

      context.data.specific
      |> Task.async_stream(fn {key, map1} ->
        prefix = "Armor specifc item #{key}"

        assert TestHarness.map_has_rank_keys(map1),
               "#{prefix} does not have rank keys (#{inspect(Map.keys(map1))})."

        Enum.each(map1, fn {rank, map2} ->
          prefix = "#{prefix} #{rank}"

          assert TestHarness.map_has_subrank_keys(map2),
                 "#{prefix} does not have subrank keys (#{inspect(Map.keys(map2))})."

          Enum.each(map2, fn {subrank, entry} ->
            prefix = "#{prefix} #{subrank}"
            assert is_list(entry), "#{prefix} is not a list."

            entry
            |> Enum.with_index()
            |> Enum.each(fn {item, index} ->
              prefix = "#{prefix} item #{index}"

              assert is_map(item), "#{prefix} is not a map."

              assert TestHarness.map_has_weighted_random_keys(item),
                     "#{prefix} does not have correct keys (#{inspect(Map.keys(item))})."

              assert is_integer(item.weight), "#{prefix} weight key is not an integer."
              assert item.weight >= 0, "#{prefix} weight key is less than zero."

              assert is_map(item.value), "#{prefix} value key is not a map."

              assert MapSet.equal?(MapSet.new(Map.keys(item.value)), MapSet.new([:name, :cost])),
                     "#{prefix} value map does not have correct keys (#{
                       inspect(Map.keys(item.value))
                     })."
            end)
          end)
        end)
      end)
      |> Enum.to_list()
    end

    test "Enchantment map has the correct format.", context do
      assert MapSet.new(Map.keys(context.data.enchantments)) == MapSet.new([:armor, :shield]),
             "Armor enchantment map does not have correct keys (#{
               inspect(Map.keys(context.data.enchantments))
             })."

      context.data.enchantments
      |> Task.async_stream(fn {key, map1} ->
        prefix = "Armor enchantment #{key}"

        assert MapSet.equal?(MapSet.new(Map.keys(map1)), MapSet.new(1..5)),
               "#{prefix} does not have the correct keys (#{inspect(Map.keys(map1))})."

        Enum.each(map1, fn {level, level_items} ->
          prefix = "#{prefix} #{level}"

          assert is_list(level_items), "#{prefix} is not a list."

          level_items
          |> Enum.with_index()
          |> Enum.each(fn {item, index} ->
            prefix = "#{prefix} item #{index}"

            assert is_map(item), "#{prefix} is not a map."

            assert TestHarness.map_has_weighted_random_keys(item),
                   "#{prefix} does not have the correct keys (#{inspect(Map.keys(item))})."

            assert MapSet.subset?(
                     MapSet.new(Map.keys(item.value)),
                     MapSet.new([:name, :cost, :limit, :exclude])
                   ),
                   "#{prefix} value map does not have the correct keys (#{inspect(Map.keys(item))})."

            assert Map.has_key?(item.value, :name), "#{prefix} value map is missing name key."
            assert is_binary(item.value.name), "#{prefix} value map name key is not a string."

            if Map.has_key?(item.value, :cost) do
              assert is_integer(item.value.cost) or is_float(item.value.cost),
                     "#{prefix} value map cost key is not a number."

              assert item.value.cost >= 0, "#{prefix} value map cost key is below zero."
            end

            if Map.has_key?(item.value, :limit) do
              assert is_list(item.value.limit), "#{prefix} value map limit key is not a list."

              assert Enum.all?(item.value.limit, &is_atom/1),
                     "#{prefix} value map limit list contains values that are not atoms."
            end

            if Map.has_key?(item.value, :exclude) do
              assert is_list(item.value.exclude), "#{prefix} value map exclude key is not a list."

              assert Enum.all?(item.value.exclude, &is_binary/1),
                     "#{prefix} value map limit list contains values that are not strings."
            end
          end)
        end)
      end)
      |> Enum.to_list()
    end

    test "Tags list has the correct format.", context do
      Enum.each(context.data.tags, fn item ->
        assert is_atom(item)
      end)
    end
  end
end
