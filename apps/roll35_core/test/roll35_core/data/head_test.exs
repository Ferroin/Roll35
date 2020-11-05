defmodule Roll35Core.Data.HeadTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Head

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Head.load_data/0" do
    setup do
      data = Head.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
