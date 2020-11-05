defmodule Roll35Core.Data.HandTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Hand

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Hand.load_data/0" do
    setup do
      data = Hand.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
