defmodule Roll35Core.Data.RingTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Ring

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Ring.load_data/0" do
    setup do
      data = Ring.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
