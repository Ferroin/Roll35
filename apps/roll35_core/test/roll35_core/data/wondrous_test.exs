defmodule Roll35Core.Data.WondrousTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Wondrous
  alias Roll35Core.Types

  describe "Roll35Core.Data.Wondrous.load_data/0" do
    setup do
      data = Wondrous.load_data(Path.join("priv", "wondrous.yaml"))

      {:ok, [data: data]}
    end

    test "Returned data structure is a non-empty list.", context do
      assert is_list(context.data)
      assert length(context.data) > 0
    end

    test "Entries of the returned list have the correct format.", context do
      Enum.each(context.data, fn entry ->
        assert is_map(entry)

        assert Map.has_key?(entry, :weight)
        assert is_integer(entry.weight)
        assert entry.weight > 0

        assert Map.has_key?(entry, :value)
        assert entry.value in Types.slots()
      end)
    end
  end
end
