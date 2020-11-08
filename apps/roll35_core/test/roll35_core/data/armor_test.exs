defmodule Roll35Core.Data.ArmorTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Armor

  alias Roll35Core.TestHarness

  require TestHarness

  describe "Roll35Core.Data.Armor.load_data/1" do
    setup do
      data = Armor.load_data()

      {:ok, [data: data]}
    end

    TestHarness.armor_weapon_core_tests("Armor")
    TestHarness.armor_weapon_base_tests("Armor", [:armor, :shield])

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
  end
end
