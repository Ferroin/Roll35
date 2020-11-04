defmodule Roll35Core.Data.ScrollTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Scroll

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Scroll.load_data/0" do
    setup do
      data = Scroll.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.compound_itemlist_tests()
  end
end
