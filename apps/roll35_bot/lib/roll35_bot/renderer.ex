defmodule Roll35Bot.Renderer do
  @moduledoc """
  Rendering functions for bot responses.
  """

  alias Roll35Core.Data.Keys
  alias Roll35Core.Data.Spell
  alias Roll35Core.Types

  require Logger

  @doc """
  Render an item name.

  This takes the item name and runs it through two passes of
  `EEx.eval_string/3` to produce the final item name.
  """
  @spec render(String.t()) :: {:ok, String.t()}
  def render(name) do
    Logger.debug("Rendering \"#{name}\".")

    {
      :ok,
      name
      |> EEx.eval_string(key: &Keys.random/1)
      |> EEx.eval_string(key: &Keys.random/1)
    }
  end

  @doc """
  Render an item name with an attached spell.

  This works similarly to `render/1`, but handles rolling for a random
  spell and then passing that into the first template evaluation.
  """
  @spec render(String.t(), map()) :: {:ok | :error, String.t()}
  def render(name, spell) do
    Logger.debug("Rendering \"#{name}\" with spell #{inspect(spell)}.")

    case Spell.random(
           {:via, Registry, {Roll35Core.Registry, :spell}},
           level: Map.get(spell, :level, nil),
           class: Map.get(spell, :cls, "minimum"),
           tag: Map.get(spell, :tag, nil)
         ) do
      {:ok, item_spell} ->
        {
          :ok,
          name
          |> EEx.eval_string(spell: item_spell, key: &Keys.random/1)
          |> EEx.eval_string(key: &Keys.random/1)
        }

      {:error, msg} ->
        Logger.error("Unable to generate spell for #{inspect(spell)}, call returned #{msg}.")

        {:error,
         "An internal error occurred while formatting the item: \"#{msg}\"\nSee the bot logs for more information."}
    end
  end

  @doc """
  Format an item for use as a message.
  """
  @spec format(Types.item() | String.t()) :: String.t()
  def format(item) when is_binary(item) do
    item
  end

  def format(item) do
    name = item.name

    rendered =
      if Map.has_key?(item, :spell) do
        render(name, item.spell)
      else
        render(name)
      end

    case rendered do
      {:ok, msg} ->
        if Map.has_key?(item, :cost) do
          "#{msg} (cost: #{item.cost}gp)"
        else
          msg
        end

      {:error, msg} ->
        msg
    end
  end
end
