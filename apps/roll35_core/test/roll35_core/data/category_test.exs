defmodule Roll35Core.Data.CategoryTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Category
  alias Roll35Core.Types

  @not_minor [:rod, :staff]
  @testfile Path.join("priv", "category.yaml")
  @testiter 20

  describe "Roll35Core.Data.Category.load_data/0" do
    setup do
      data = Category.load_data(@testfile)

      {:ok, [data: data]}
    end

    test "Returned data structure is a map.", context do
      assert is_map(context.data)
    end

    test "Returned map has an entry for each rank.", context do
      assert MapSet.equal?(
               MapSet.new(Map.keys(context.data)),
               MapSet.new(Types.ranks())
             )
    end

    test "Returned map’s entries are lists.", context do
      assert Enum.all?(Map.values(context.data), &is_list/1)
    end

    test "Entries of the returned map have the correct format.", context do
      Enum.each(context.data, fn {_, entry} ->
        Enum.each(entry, fn item ->
          assert Map.has_key?(item, :weight)
          assert item.weight > 0
          assert Map.has_key?(item, :value)
          assert is_atom(item.value)
          assert item.value in Types.categories()
        end)
      end)
    end
  end

  describe "Roll35Core.Data.Category.random/1" do
    setup do
      {:ok, server} = start_supervised({Category, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid items of a random rank.", context do
      agent = context.server

      Enum.each(1..@testiter, fn _ ->
        item = Category.random(agent)

        assert is_atom(item)
        assert item in Types.categories()
      end)
    end
  end

  describe "Roll35Core.Data.Category.random/2" do
    setup do
      {:ok, server} = start_supervised({Category, {nil, @testfile}})

      %{server: server}
    end

    test "Returns valid minor items.", context do
      agent = context.server

      Enum.each(1..@testiter, fn _ ->
        item = Category.random(agent, :minor)

        assert is_atom(item)
        assert item in Enum.filter(Types.categories(), fn i -> i not in @not_minor end)
      end)
    end

    test "Returns valid medium items.", context do
      agent = context.server

      Enum.each(1..@testiter, fn _ ->
        item = Category.random(agent, :medium)

        assert is_atom(item)
        assert item in Types.categories()
      end)
    end

    test "Returns valid major items.", context do
      agent = context.server

      Enum.each(1..@testiter, fn _ ->
        item = Category.random(agent, :major)

        assert is_atom(item)
        assert item in Types.categories()
      end)
    end
  end
end
