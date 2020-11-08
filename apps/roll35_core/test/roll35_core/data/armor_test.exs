defmodule Roll35Core.Data.ArmorTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Armor

  alias Roll35Core.TestHarness

  require TestHarness

  @item_types [:armor, :shield]

  describe "Roll35Core.Data.Armor.load_data/1" do
    setup do
      data = Armor.load_data()

      {:ok, [data: data]}
    end

    TestHarness.armor_weapon_core_tests("Armor")
    TestHarness.armor_weapon_base_tests("Armor", @item_types)
    TestHarness.armor_weapon_enchantment_tests("Weapon", @item_types, 1..5)

    test "Specific map has the correct format.", context do
      assert MapSet.new(Map.keys(context.data.specific)) == MapSet.new(@item_types),
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

          TestHarness.armor_weapon_specific_subtests(prefix, map2)
        end)
      end)
      |> Enum.to_list()
    end
  end
end
