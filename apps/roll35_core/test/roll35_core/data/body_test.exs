defmodule Roll35Core.Data.BodyTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Body

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Body.load_data/0" do
    setup do
      data = Body.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
