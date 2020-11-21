defmodule Roll35Core.Data.KeysTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Keys

  alias Roll35Core.TestHarness

  @testfile Path.join("priv", "keys.yaml")

  @spec check_key_entry(term()) :: none()
  defp check_key_entry(item) do
    assert is_map(item)

    assert Map.has_key?(item, :weight)
    assert is_integer(item.weight)
    assert item.weight >= 1

    assert Map.has_key?(item, :value)
    assert String.valid?(item.value)
  end

  describe "Roll35Core.Data.Keys.load_data/0" do
    setup do
      data = Keys.load_data(@testfile)

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

            assert Enum.all?(entry.data, &String.valid?/1)

          :grouped ->
            assert is_map(entry.data)

            Enum.each(entry.data, fn {_, value} ->
              assert is_list(value)

              assert Enum.all?(value, &String.valid?/1)
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

  describe "Roll35Core.Data.Keys.get_keys/2" do
    setup do
      {:ok, server} = start_supervised({Keys, {nil, @testfile}})

      %{server: server}
    end

    test "Returns proper lists of keys.", context do
      agent = context.server

      flat = Keys.get_keys(agent, :flat)

      assert is_list(flat)
      refute Enum.empty?(flat)
      assert Enum.all?(flat, &is_atom/1)

      flat_proportional = Keys.get_keys(agent, :flat_proportional)

      assert is_list(flat_proportional)
      refute Enum.empty?(flat_proportional)
      assert Enum.all?(flat_proportional, &is_atom/1)

      grouped = Keys.get_keys(agent, :grouped)

      assert is_list(grouped)
      refute Enum.empty?(grouped)
      assert Enum.all?(grouped, &is_atom/1)

      grouped_proportional = Keys.get_keys(agent, :grouped_proportional)

      assert is_list(grouped_proportional)
      refute Enum.empty?(grouped_proportional)
      assert Enum.all?(grouped_proportional, &is_atom/1)
    end
  end

  describe "Roll35Core.Data.Keys.get_subkeys/2" do
    setup do
      {:ok, server} = start_supervised({Keys, {nil, @testfile}})

      %{server: server}
    end

    test "Returns proper lists of subkeys.", context do
      agent = context.server

      grouped_keys = Keys.get_keys(agent, :grouped) ++ Keys.get_keys(agent, :grouped_proportional)

      Enum.each(TestHarness.iter(), fn _ ->
        key = Enum.random(grouped_keys)

        {:ok, subkeys} = Keys.get_subkeys(agent, key)

        assert is_list(subkeys)
        refute Enum.empty?(subkeys)
      end)
    end
  end

  describe "Roll35Core.Data.Keys.random/2" do
    setup do
      {:ok, server} = start_supervised({Keys, {nil, @testfile}})

      %{server: server}
    end

    test "Returns random strings for flat keys.", context do
      agent = context.server

      keys = Keys.get_keys(agent, :flat) ++ Keys.get_keys(agent, :flat_proportional)

      Enum.each(TestHarness.iter(), fn _ ->
        result = Keys.random(agent, key: Enum.random(keys))

        assert String.valid?(result)
      end)
    end

    test "Returns random strings for grouped keys.", context do
      agent = context.server

      keys = Keys.get_keys(agent, :grouped) ++ Keys.get_keys(agent, :grouped_proportional)

      Enum.each(TestHarness.iter(), fn _ ->
        key = Enum.random(keys)
        {:ok, subkeys} = Keys.get_subkeys(agent, key)

        result = Keys.random(agent, key: key, subkey: Enum.random(subkeys))

        assert String.valid?(result)
      end)
    end
  end
end
