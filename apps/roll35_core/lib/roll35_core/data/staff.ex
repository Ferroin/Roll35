defmodule Roll35Core.Data.Staff do
  @moduledoc """
  Data handling for staves.
  """

  use Roll35Core.Data.Agent, {:staff, "priv/staff.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  Roll35Core.Data.Agent.ranked_itemlist_selectors()
end