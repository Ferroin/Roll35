defmodule Roll35Core.Data.Head do
  @moduledoc """
  Data handling for head items.
  """

  use Roll35Core.Data.Agent, {:head, "priv/head.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank, subrank), to: Roll35Core.Data.Agent, as: :random_ranked
end
