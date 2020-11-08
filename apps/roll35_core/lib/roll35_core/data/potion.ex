defmodule Roll35Core.Data.Potion do
  @moduledoc """
  Data handling for potions.
  """

  use Roll35Core.Data.Agent, {:potion, "priv/potion.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_compound_itemlist(data)
  end

  Roll35Core.Data.Agent.compound_itemlist_selectors()
end
