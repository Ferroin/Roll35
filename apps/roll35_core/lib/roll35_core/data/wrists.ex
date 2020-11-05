defmodule Roll35Core.Data.Wrists do
  @moduledoc """
  Data handling for wrists items.
  """

  use Roll35Core.Data.Agent, "priv/wrists.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  Roll35Core.Data.Agent.ranked_itemlist_selectors()
end
