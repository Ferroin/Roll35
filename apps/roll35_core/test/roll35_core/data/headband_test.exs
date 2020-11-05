defmodule Roll35Core.Data.HeadbandTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Headband

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Headband.load_data/0" do
    setup do
      data = Headband.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
