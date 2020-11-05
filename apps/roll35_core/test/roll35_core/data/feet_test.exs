defmodule Roll35Core.Data.FeetTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Feet

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Feet.load_data/0" do
    setup do
      data = Feet.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
