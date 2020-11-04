defmodule Roll35Core.Data.WondrousTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Wondrous
  alias Roll35Core.Types

  describe "Roll35Core.Data.Wondrous.load_data/0" do
    setup do
      data = Wondrous.load_data()

      {:ok, [data: data]}
    end

    test "Returned data structure is a non-empty list.", context do
      assert is_list(context.data) and length(context.data) > 0
    end

    test "Entries of the returned list have the correct format.", context do
      assert Enum.all?(context.data, fn entry ->
               is_integer(entry.weight) and entry.weight > 0 and entry.value in Types.slots()
             end)
    end
  end
end
