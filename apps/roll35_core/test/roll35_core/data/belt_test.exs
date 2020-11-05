defmodule Roll35Core.Data.BeltTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Belt

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Belt.load_data/0" do
    setup do
      data = Belt.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
