defmodule Roll35Core.Data.EyesTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Eyes

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Eyes.load_data/0" do
    setup do
      data = Eyes.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
