defmodule Roll35Core.Data.NeckTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Neck

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Neck.load_data/0" do
    setup do
      data = Neck.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
