defmodule Roll35Core.Data.Belt do
  @moduledoc """
  Data handling for belts.
  """

  use Roll35Core.Data.Agent, {:belt, "priv/belt.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  Roll35Core.Data.Agent.ranked_itemlist_selectors()
end