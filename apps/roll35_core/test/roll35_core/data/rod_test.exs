defmodule Roll35Core.Data.RodTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Rod

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Rod.load_data/0" do
    setup do
      data = Rod.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
