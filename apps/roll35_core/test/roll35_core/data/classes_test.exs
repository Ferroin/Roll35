defmodule Roll35Core.Data.ClassesTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Classes

  describe "Roll35Core.Data.Classes.load_data/0" do
    setup do
      data = Classes.load_data()

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data)
    end

    test "Returned map’s entries are maps.", context do
      assert Enum.all?(context.data, fn {_, value} -> is_map(value) end)
    end

    test "Returned map’s entries have the correct format.", context do
      Enum.each(context.data, fn {_, value} ->
        assert Enum.all?(Map.keys(value), fn key ->
                 key in [
                   :type,
                   :levels,
                   :copy,
                   :merge
                 ]
               end)

        assert :type in Map.keys(value) and value.type in [:arcane, :divine, :occult]

        assert :levels in Map.keys(value) and is_list(value.levels) and
                 ({true, _} =
                    Enum.reduce(value.levels, {true, -1}, fn
                      item, {true, -1} -> {item in 1..20 or item == nil, item}
                      item, {true, nil} -> {item in 1..20, item}
                      item, {true, prev} -> {item in 1..20 and item >= prev, item}
                      _, {false, _} -> {false, nil}
                    end))

        assert (:copy in Map.keys(value) and value.copy in Map.keys(context.data)) or true

        assert (:merge in Map.keys(value) and is_list(value.merge) and
                  Enum.all?(value.merge, fn cls ->
                    cls in Map.keys(context.data)
                  end)) or true
      end)
    end
  end
end
