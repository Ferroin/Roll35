defmodule Roll35Bot.Renderer do
  @moduledoc """
  Rendering functions for bot responses.
  """

  alias Roll35Core.Data.Keys
  alias Roll35Core.Data.Spell

  require Logger

  @doc """
  Render an item name.

  This takes the item name and runs it through two passes of
  `EEx.eval_string/3` to produce the final item name.
  """
  @spec render(String.t()) :: String.t()
  def render(name) do
    Logger.debug("Rendering \"#{name}\".")

    name
    |> EEx.eval_string(key: &Keys.random/1, compound_key: &Keys.random/2)
    |> EEx.eval_string(key: &Keys.random/1, compound_key: &Keys.random/2)
  end

  @doc """
  Render an item name with an attached spell.

  This works similarly to `render/1`, but handles rolling for a random
  spell and then passing that into the first template evaluation.
  """
  @spec render(String.t(), map()) :: String.t()
  def render(name, spell) do
    Logger.debug("Rendering \"#{name}\" with spell #{inspect(spell)}.")

    case Spell.random(
           {:via, Registry, {Roll35Core.Registry, :spell}},
           level: Map.get(spell, :level, nil),
           class: Map.get(spell, :cls, "minimum"),
           tag: Map.get(spell, :tag, nil)
         ) do
      {:ok, item_spell} ->
        name
        |> EEx.eval_string(spell: item_spell, key: &Keys.random/1, compound_key: &Keys.random/2)
        |> EEx.eval_string(key: &Keys.random/1, compound_key: &Keys.random/2)

      {:error, msg} ->
        Logger.error("Unable to generate spell for #{inspect(spell)}, call returned #{msg}.")

        "An internal error occurred while formatting the item: \"#{msg}\"\nSee the bot logs for more information."
    end
  end

  @doc """
  Format an item for use as a message.
  """
  @spec format(map()) :: String.t()
  def format(item) do
    name = item.name

    rendered =
      if Map.has_key?(item, :spell) do
        render(name, item.spell)
      else
        render(name)
      end

    if Map.has_key?(item, :cost) do
      "#{rendered} (cost: #{item.cost}gp)"
    else
      "#{rendered}"
    end
  end
end
