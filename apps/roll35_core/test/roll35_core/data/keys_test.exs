defmodule Roll35Core.Data.KeysTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Keys

  @spec check_key_entry(term()) :: none()
  defp check_key_entry(item) do
    assert is_map(item)

    assert Map.has_key?(item, :weight)
    assert is_integer(item.weight)
    assert item.weight >= 1

    assert Map.has_key?(item, :value)
    assert is_binary(item.value)
  end

  describe "Roll35Core.Data.Keys.load_data/0" do
    setup do
      data = Keys.load_data(Path.join("priv", "keys.yaml"))

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data)
    end

    test "Returned map’s entries are maps.", context do
      assert Enum.all?(context.data, fn {_, value} -> is_map(value) end)
    end

    test "Returned map’s entries have the correct format.", context do
      Enum.each(context.data, fn {_, entry} ->
        assert Map.has_key?(entry, :type)

        assert is_atom(entry.type)

        assert entry.type in [:flat, :grouped, :flat_proportional, :grouped_proportional]

        assert Map.has_key?(entry, :data)

        case entry.type do
          :flat ->
            assert is_list(entry.data)

            assert Enum.all?(entry.data, &is_binary/1)

          :grouped ->
            assert is_map(entry.data)

            Enum.each(entry.data, fn {_, value} ->
              assert is_list(value)

              assert Enum.all?(value, &is_binary/1)
            end)

          :flat_proportional ->
            assert is_list(entry.data)

            Enum.each(entry.data, &check_key_entry/1)

          :grouped_proportional ->
            assert is_map(entry.data)

            Enum.each(entry.data, fn {_, value} ->
              assert is_list(value)

              Enum.each(value, &check_key_entry/1)
            end)
        end
      end)
    end
  end
end
