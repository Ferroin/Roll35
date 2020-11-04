defmodule Roll35Core.UtilTest do
  @moduledoc false

  use ExUnit.Case, async: true

  describe "Roll35Core.Util.atomize_map/1" do
    test "Converts string keys to atoms in maps." do
      data =
        Roll35Core.Util.atomize_map(%{
          "a" => 1,
          "b" => 2
        })

      assert Enum.all?(Map.keys(data), &is_atom/1)
    end

    test "Does not modify atom keys." do
      data1 = %{
        a: 1,
        b: 2
      }

      data2 = Roll35Core.Util.atomize_map(data1)

      assert data1 |> Map.keys() |> Enum.sort() == data2 |> Map.keys() |> Enum.sort()
    end

    test "Does not modify values." do
      data1 = %{
        "a" => 1,
        b: nil
      }

      data2 = Roll35Core.Util.atomize_map(data1)

      assert data1 |> Map.values() |> Enum.sort() == data2 |> Map.values() |> Enum.sort()
    end

    test "Does not modify non-string non-atom keys." do
      data1 = %{
        1 => 1,
        b: 2
      }

      data2 = Roll35Core.Util.atomize_map(data1)

      assert data1 |> Map.keys() |> Enum.sort() == data2 |> Map.keys() |> Enum.sort()
    end

    test "Properly handles nested maps." do
      data1 =
        Roll35Core.Util.atomize_map(%{
          "a" => %{
            "b" => 1,
            c: 2
          },
          d: 3
        })

      data2 = %{
        a: %{
          b: 1,
          c: 2
        },
        d: 3
      }

      assert data1 == data2
    end
  end

  describe "Roll35Core.Util.process_compound_itemlist/1" do
    test "Correctly transforms it’s input." do
      data1 = [
        %{minor: 1, medium: 2, major: 3, a: 1, b: 2},
        %{minor: 3, medium: 2, major: 0, a: 2, b: 1}
      ]

      data2 = %{
        minor: [
          %{weight: 1, value: %{a: 1, b: 2}},
          %{weight: 3, value: %{a: 2, b: 1}}
        ],
        medium: [
          %{weight: 2, value: %{a: 1, b: 2}},
          %{weight: 2, value: %{a: 2, b: 1}}
        ],
        major: [
          %{weight: 3, value: %{a: 1, b: 2}},
          %{weight: 0, value: %{a: 2, b: 1}}
        ]
      }

      assert Roll35Core.Util.process_compound_itemlist(data1) == data2
    end
  end
end
