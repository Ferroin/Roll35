defmodule Roll35Core.Data.Scroll do
  @moduledoc """
  Data handling for scrolls.
  """

  use Roll35Core.Data.Agent, {:scroll, "priv/scroll.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_compound_itemlist(data)
  end

  Roll35Core.Data.Agent.compound_itemlist_selectors()
end
