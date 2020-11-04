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
end
