defmodule Roll35Core.Data.WandTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Wand

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Wand.load_data/0" do
    setup do
      data = Wand.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.compound_itemlist_tests()
  end
end
