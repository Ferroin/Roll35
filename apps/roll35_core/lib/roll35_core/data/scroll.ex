defmodule Roll35Core.Data.Scroll do
  @moduledoc """
  Data handling for scrolls.
  """

  use Roll35Core.Data.Agent, "priv/scroll.yaml"

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_compound_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_compound
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_compound
end
