defmodule Roll35Core.Types do
  @moduledoc """
  Core type definitions for Roll35.
  """

  @typedoc """
  Represents an item.
  """
  @type item :: %{
          :name => String.t(),
          optional(atom()) => term()
        }

  @typedoc """
  Represents the category of an item.
  """
  @type category ::
          :armor | :weapon | :potion | :ring | :rod | :scroll | :staff | :wand | :wondrous
  @categories [:armor, :weapon, :potion, :ring, :rod, :scroll, :staff, :wand, :wondrous]

  @typedoc """
  Represents the rank (minor/medium/major) of an item.
  """
  @type rank :: :minor | :medium | :major
  @ranks [:minor, :medium, :major]

  @typedoc """
  A subset of `rank`, used by rods and staves.
  """
  @type limited_rank :: :medium | :major
  @limited_ranks [:medium, :major]

  @typedoc """
  Represents the sub-rank (lesser/greater) of an item.
  """
  @type subrank :: :lesser | :greater
  @subranks [:lesser, :greater]

  @typedoc """
  An superset of `subrank`, used by minor slotless items.
  """
  @type full_subrank :: :least | subrank
  @full_subranks [:least | @subranks]

  @typedoc """
  Represents the slot of a wondrous item.
  """
  @type slot ::
          :belt
          | :body
          | :chest
          | :eyes
          | :feet
          | :hands
          | :head
          | :headband
          | :neck
          | :shoulders
          | :wrists
          | :slotless
  @slots [
    :belt,
    :body,
    :chest,
    :eyes,
    :feet,
    :hands,
    :head,
    :headband,
    :neck,
    :shoulders,
    :wrists,
    :slotless
  ]

  @typedoc """
  A single item entry.
  """
  @type item_entry :: %{weight: non_neg_integer(), value: %{atom() => any}}

  @typedoc """
  A flat list of items.

  This is an internal structure used by many of the data agents.
  """
  @type flat_itemlist :: [item_entry, ...]

  @typedoc """
  A map of ranks to lists of items.

  This is an internal structure used by many of the data agents.
  """
  @type itemlist :: %{rank => [item_entry, ...]}

  @typedoc """
  A map of subranks to lists of items.

  This is an internal structure used by many of the data agents.
  """
  @type subranked_itemlist :: %{full_subrank => [item_entry, ...]}

  @typedoc """
  A map of ranks and subranks to lists of items.

  This is an internal structure used by many of the data agents.
  """
  @type ranked_itemlist :: %{rank => subranked_itemlist}

  @doc """
  Check that a value is a valid category.
  """
  defguard is_category(value) when value in @categories

  @doc """
  Check that a value is a valid rank.
  """
  defguard is_rank(value) when value in @ranks

  @doc """
  Check that a value is a valid limited_rank.
  """
  defguard is_limited_rank(value) when value in @limited_ranks

  @doc """
  Check that a value is a valid subrank.
  """
  defguard is_subrank(value) when value in @subranks

  @doc """
  Check that a value is a valid full_subrank.
  """
  defguard is_full_subrank(value) when value in @full_subranks

  @doc """
  Check that a value is a valid slot.
  """
  defguard is_slot(value) when value in @slots

  @doc """
  Return a list of valid categories.
  """
  @spec categories :: nonempty_list(category)
  def categories do
    @categories
  end

  @doc """
  Return a list of valid ranks.
  """
  @spec ranks :: nonempty_list(rank)
  def ranks do
    @ranks
  end

  @doc """
  Return a list of valid limited_ranks.
  """
  @spec limited_ranks :: nonempty_list(limited_rank)
  def limited_ranks do
    @limited_ranks
  end

  @doc """
  Return a list of valid subranks.
  """
  @spec subranks :: nonempty_list(subrank)
  def subranks do
    @subranks
  end

  @doc """
  Return a list of valid full_subranks.
  """
  @spec full_subranks :: nonempty_list(full_subrank)
  def full_subranks do
    @full_subranks
  end

  @doc """
  Return a list of valid slots.
  """
  @spec slots :: nonempty_list(slot)
  def slots do
    @slots
  end

  @doc """
  Create a category atom from a string.
  """
  @spec category_from_string(String.t()) :: category
  def category_from_string(str) when is_binary(str) do
    _ = @categories
    String.to_existing_atom(str)
  end

  @doc """
  Create a rank atom from a string.
  """
  @spec rank_from_string(String.t()) :: rank
  def rank_from_string(str) when is_binary(str) do
    _ = @ranks
    String.to_existing_atom(str)
  end

  @doc """
  Create a limited_rank atom from a string.
  """
  @spec limited_rank_from_string(String.t()) :: limited_rank
  def limited_rank_from_string(str) when is_binary(str) do
    _ = @limited_ranks
    String.to_existing_atom(str)
  end

  @doc """
  Create a subrank atom from a string.
  """
  @spec subrank_from_string(String.t()) :: subrank
  def subrank_from_string(str) when is_binary(str) do
    _ = @subranks
    String.to_existing_atom(str)
  end

  @doc """
  Create a full_subrank atom from a string.
  """
  @spec full_subrank_from_string(String.t()) :: full_subrank
  def full_subrank_from_string(str) when is_binary(str) do
    _ = @full_subranks
    String.to_existing_atom(str)
  end

  @doc """
  Create a slot atom from a string.
  """
  @spec slot_from_string(String.t()) :: slot
  def slot_from_string(str) when is_binary(str) do
    _ = @slots
    String.to_existing_atom(str)
  end
end
