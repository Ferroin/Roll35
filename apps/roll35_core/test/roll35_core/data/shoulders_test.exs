defmodule Roll35Core.Data.ShouldersTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Shoulders

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Shoulders.load_data/0" do
    setup do
      data = Shoulders.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
