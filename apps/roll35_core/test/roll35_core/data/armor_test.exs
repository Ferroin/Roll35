defmodule Roll35Core.Data.ArmorTest do
  @moduledoc false
  use Roll35Core.TestHarness.BattleGear, async: true

  alias Roll35Core.Data.Armor

  alias Roll35Core.TestHarness
  alias Roll35Core.TestHarness.BattleGear

  require TestHarness

  @item_types [:armor, :shield]

  describe "Roll35Core.Data.Armor.load_data/1" do
    setup do
      data = Armor.load_data(Path.join("priv", "armor.yaml"))

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      BattleGear.check_core_data_type("Armor", context)
    end

    test "Returned map has expected keys with expected value types.", context do
      BattleGear.check_core_data_keys("Armor", context)
    end

    test "Tags list has the correct format.", context do
      BattleGear.check_tag_types("Armor", context)
    end

    test "Rank maps have the correct format.", context do
      BattleGear.check_rank_maps("Armor", context)
    end

    test "Base item list has the correct format.", context do
      BattleGear.check_base("Armor", context, @item_types)
    end

    test "Enchantment map has the correct format.", context do
      BattleGear.check_enchantments("Armor", context, @item_types, 1..5)
    end

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

          BattleGear.specific_item_subchecks(prefix, map2)
        end)
      end)
      |> Enum.to_list()
    end
  end
end
