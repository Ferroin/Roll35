defmodule Roll35Core.Data.WeaponTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Weapon

  alias Roll35Core.TestHarness

  require TestHarness

  @item_types [:melee, :ranged, :ammo]

  describe "Roll35Core.Data.Weapon.load_data/1" do
    setup do
      data = Weapon.load_data()

      {:ok, [data: data]}
    end

    TestHarness.armor_weapon_core_tests("Weapon")
    TestHarness.armor_weapon_base_tests("Weapon", @item_types)
    TestHarness.armor_weapon_enchantment_tests("Weapon", @item_types, 1..4)

    test "Specific map has the correct format.", context do
      assert TestHarness.map_has_rank_keys(context.data.specific)

      "Weapon specific item map does not have correct keys (#{
        inspect(Map.keys(context.data.specific))
      })."

      context.data.specific
      |> Task.async_stream(fn {rank, map} ->
        prefix = "Weapon specifc item #{rank}"

        TestHarness.armor_weapon_specific_subtests(prefix, map)
      end)
      |> Enum.to_list()
    end
  end
end
