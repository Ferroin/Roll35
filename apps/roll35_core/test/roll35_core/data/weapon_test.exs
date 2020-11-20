defmodule Roll35Core.Data.WeaponTest do
  @moduledoc false
  use Roll35Core.TestHarness.BattleGear, async: true

  alias Roll35Core.Data.Weapon

  alias Roll35Core.TestHarness
  alias Roll35Core.TestHarness.BattleGear

  require TestHarness

  @item_types [:melee, :ranged, :ammo]

  describe "Roll35Core.Data.Weapon.load_data/1" do
    setup do
      data = Weapon.load_data(Path.join("priv", "weapon.yaml"))

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      BattleGear.check_core_data_type("Weapon", context)
    end

    test "Returned map has expected keys with expected value types.", context do
      BattleGear.check_core_data_keys("Weapon", context)
    end

    test "Tags list has the correct format.", context do
      BattleGear.check_tag_types("Weapon", context)
    end

    test "Rank maps have the correct format.", context do
      BattleGear.check_rank_maps("Weapon", context)
    end

    test "Base item list has the correct format.", context do
      BattleGear.check_base("Weapon", context, @item_types)
    end

    test "Enchantment map has the correct format.", context do
      BattleGear.check_enchantments("Weapon", context, @item_types, 1..4)
    end

    test "Specific map has the correct format.", context do
      assert TestHarness.map_has_rank_keys(context.data.specific)

      "Weapon specific item map does not have correct keys (#{
        inspect(Map.keys(context.data.specific))
      })."

      context.data.specific
      |> Task.async_stream(fn {rank, map} ->
        prefix = "Weapon specifc item #{rank}"

        BattleGear.specific_item_subchecks(prefix, map)
      end)
      |> Enum.to_list()
    end
  end
end
