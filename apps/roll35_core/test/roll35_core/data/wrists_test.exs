defmodule Roll35Core.Data.WristsTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Wrists

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Wrists.load_data/0" do
    setup do
      data = Wrists.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
