defmodule Roll35Core.Data.StaffTest do
  @moduledoc false
  use ExUnit.Case, async: true

  alias Roll35Core.Data.Staff

  require Roll35Core.TestHarness

  describe "Roll35Core.Data.Staff.load_data/0" do
    setup do
      data = Staff.load_data()

      {:ok, [data: data]}
    end

    Roll35Core.TestHarness.ranked_itemlist_tests()
  end
end
