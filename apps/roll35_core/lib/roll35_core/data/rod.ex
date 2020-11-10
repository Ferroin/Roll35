defmodule Roll35Core.Data.Rod do
  @moduledoc """
  Data handling for rods.
  """

  use Roll35Core.Data.Agent, {:rod, "priv/rod.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  Roll35Core.Data.Agent.ranked_itemlist_selectors()
end
