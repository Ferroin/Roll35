defmodule Roll35Core.Data.Body do
  @moduledoc """
  Data handling for body items.
  """

  use Agent

  alias Roll35Core.Data.Macros
  alias Roll35Core.Types
  alias Roll35Core.Util

  require Logger
  require Macros
  require Types

  @datapath "priv/body.yaml"

  @spec start_link(atom) :: Agent.on_start()
  def start_link(name) do
    Agent.start_link(&load_data/0, name: name)
  end

  @doc """
  Load the body item data from disk. Used to prepare the initial state for the agent.
  """
  @spec load_data :: Types.itemlist()
  def load_data do
    path = Path.join(Application.app_dir(:roll35_core), @datapath)
    Logger.info("Loading data for body items from #{path}.")
    data = YamlElixir.read_from_file!(path)

    Logger.info("Processing data for body items.")

    result = Util.process_ranked_itemlist(data)

    Logger.info("Finished processing data for body items.")
    result
  end

  Macros.ranked_itemlist_selectors()
end
