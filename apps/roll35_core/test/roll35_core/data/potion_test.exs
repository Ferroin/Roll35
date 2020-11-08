defmodule Roll35Core.Data.PotionTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Potion

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Potion.load_data/0" do
    setup do
      data = Potion.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.compound_itemlist_tests()
  end
end