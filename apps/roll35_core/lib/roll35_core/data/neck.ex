defmodule Roll35Core.Data.Neck do
  @moduledoc """
  Data handling for neck items.
  """

  use Roll35Core.Data.Agent, {:neck, "priv/neck.yaml"}

  alias Roll35Core.Util

  @impl Roll35Core.Data.Agent
  def process_data(data) do
    Util.process_ranked_itemlist(data)
  end

  defdelegate random(agent), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank), to: Roll35Core.Data.Agent, as: :random_ranked
  defdelegate random(agent, rank, subrank), to: Roll35Core.Data.Agent, as: :random_ranked
end
