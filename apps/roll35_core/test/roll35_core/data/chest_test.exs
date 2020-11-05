defmodule Roll35Core.Data.ChestTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Chest

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Chest.load_data/0" do
    setup do
      data = Chest.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
