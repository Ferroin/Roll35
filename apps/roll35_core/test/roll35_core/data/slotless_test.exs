defmodule Roll35Core.Data.SlotlessTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Slotless

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Slotless.load_data/0" do
    setup do
      data = Slotless.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
