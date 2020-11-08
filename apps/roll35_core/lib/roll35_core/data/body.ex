defmodule Roll35Core.Data.Body do
  @moduledoc """
  Data handling for body items.
  """

  use Roll35Core.Data.Agent, {:body, "priv/body.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  Roll35Core.Data.Agent.ranked_itemlist_selectors()
end
