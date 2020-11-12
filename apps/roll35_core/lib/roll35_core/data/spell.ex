defmodule Roll35Core.Data.Spell do
  @moduledoc """
  Data handling for spells.
  """

  # Due to complexities and caching requirements, we need to implement
  # this from scratch instead of building on Roll35Core.Data.Agent.
  use GenServer

  alias Roll35Core.Data.SpellDB
  alias Roll35Core.Types
  alias Roll35Core.Util

  require Types
  require Logger

  @spells_schema """
  CREATE TABLE spells(name TEXT,
                      <%= Enum.join(classes, " INTEGER, ") %> INTEGER,
                      minimum INTEGER,
                      spellpage_arcane INTEGER,
                      spellpage_divine INTEGER,
                      minimum_cls TEXT,
                      spellpage_arcane_cls TEXT,
                      spellpage_divine_cls TEXT);
  """
  @tagmap_schema """
  CREATE VIRTUAL TABLE tagmap USING fts4(name, tags);
  """
  @info_schema """
  CREATE TABLE info(id TEXT, data TEXT);
  """
  @schema_rev Base.encode16(
                :crypto.hash(:sha256, "#{@spells_schema}\n#{@tagmap_schema}\n#{@info_schema}")
              )
  @spell_db {:via, Registry, {Roll35Core.Registry, :spell_db}}
  @max_spell_level 9

  @spec sql_escape(String.t()) :: String.t()
  defp sql_escape(string) do
    String.replace(string, "'", "''")
  end

  @spec load_data :: term()
  def load_data do
    spellpath = Path.join(Application.app_dir(:roll35_core, "priv"), "spells.yaml")
    classpath = Path.join(Application.app_dir(:roll35_core, "priv"), "classes.yaml")

    spelltstamp = File.stat!(spellpath, time: :posix).mtime
    clasststamp = File.stat!(classpath, time: :posix).mtime
    classdata = classpath |> YamlElixir.read_from_file!() |> Util.atomize_map()

    try do
      {:ok, [%{data: rev}]} = SpellDB.query(@spell_db, "SELECT data FROM info WHERE id='rev';")

      {:ok, [%{data: mtime1}]} =
        SpellDB.query(@spell_db, "SELECT data FROM info WHERE id='spell_mtime''")

      {:ok, [%{data: mtime2}]} =
        SpellDB.query(@spell_db, "SELECT data FROM info WHERE id='class_mtime''")

      if rev != @schema_rev or Integer.parse(mtime1, 10) != spelltstamp or
           Integer.parse(mtime2, 10) != clasststamp do
        Logger.notice("SpellDB out of sync with data, regenerating it from spell data.")
        spelldata = YamlElixir.read_from_file!(spellpath)

        :ok = prepare_spell_db(spelldata, spelltstamp, classdata, clasststamp)
      else
        Logger.info("SpellDB timestamps and schema match, using existing database.")
      end
    rescue
      _ ->
        Logger.notice("Unable to read spell DB, regenerating it from spell data.")
        spelldata = YamlElixir.read_from_file!(spellpath)

        :ok = prepare_spell_db(spelldata, spelltstamp, classdata, clasststamp)
    end

    %{class: classdata}
  end

  defp process_spell(spell, rev_columns, classdata, classes) do
    entry = Util.atomize_map(spell)

    result =
      Enum.reduce(
        rev_columns,
        %{
          levels: [],
          minimum: @max_spell_level,
          minimum_cls: "",
          spellpage_arcane: "NULL",
          spellpage_arcane_cls: "NULL",
          spellpage_arcane_fixed: false,
          spellpage_divine: "NULL",
          spellpage_divine_cls: "NULL",
          spellpage_divine_fixed: false
        },
        fn class, acc ->
          cls = String.to_existing_atom(class)

          level =
            cond do
              cls in Map.keys(entry.classes) ->
                entry.classes[cls]

              Map.has_key?(classdata[cls], :copy) and
                  classdata[cls].copy in Map.keys(entry.classes) ->
                entry.classes[classdata[cls].copy]

              :merge in Map.keys(classdata[cls]) ->
                valid =
                  MapSet.intersection(
                    MapSet.new(classdata[cls].merge),
                    MapSet.new(Map.keys(entry.classes))
                  )

                case MapSet.size(valid) do
                  0 ->
                    "NULL"

                  1 ->
                    entry.classes[classdata[cls].merge[0]]

                  _ ->
                    valid
                    |> MapSet.to_list()
                    |> Enum.map(fn item -> entry.classes[item] end)
                    |> Enum.min()
                end

              true ->
                "NULL"
            end

          level =
            cond do
              level != "NULL" and Map.get(entry, :max_level, @max_spell_level) < level ->
                "NULL"

              level != "NULL" and level >= length(classdata[cls].levels) ->
                Logger.warning(
                  "#{entry.name} has invalid spell level for class #{cls}, ignoring."
                )

                "NULL"

              true ->
                level
            end

          {minimum, minimum_cls} =
            cond do
              level != "NULL" and level < acc.minimum -> {level, cls}
              level != "NULL" and acc.minimum == "NULL" -> {level, cls}
              true -> {acc.minimum, acc.minimum_cls}
            end

          {spellpage_arcane, spellpage_arcane_cls, spellpage_arcane_fixed} =
            cond do
              acc.spellpage_arcane_fixed ->
                {acc.spellpage_arcane, acc.spellpage_arcane_cls, true}

              cls == "wizard" and level != "NULL" ->
                {level, "wizard", true}

              classdata[cls].type == "arcane" and level != "NULL" and
                  acc.spellpage_arcane < level ->
                {level, cls, false}

              classdata[cls].type == "arcane" and level != "NULL" and
                  acc.spellpage_arcane == "NULL" ->
                {level, cls, false}

              true ->
                {acc.spellpage_arcane, acc.spellpage_arcane_cls, acc.spellpage_arcane_fixed}
            end

          {spellpage_divine, spellpage_divine_cls, spellpage_divine_fixed} =
            cond do
              acc.spellpage_divine_fixed ->
                {acc.spellpage_divine, acc.spellpage_divine_cls, true}

              cls == "cleric" and level != "NULL" ->
                {level, "cleric", true}

              classdata[cls].type == "divine" and level != "NULL" and
                  acc.spellpage_divine < level ->
                {level, cls, false}

              classdata[cls].type == "divine" and level != "NULL" and
                  acc.spellpage_divine == "NULL" ->
                {level, cls, false}

              true ->
                {acc.spellpage_divine, acc.spellpage_divine_cls, acc.spellpage_divine_fixed}
            end

          %{
            levels: [level | acc.levels],
            minimum: minimum,
            minimum_cls: minimum_cls,
            spellpage_arcane: spellpage_arcane,
            spellpage_arcane_cls: spellpage_arcane_cls,
            spellpage_arcane_fixed: spellpage_arcane_fixed,
            spellpage_divine: spellpage_divine,
            spellpage_divine_cls: spellpage_divine_cls,
            spellpage_divine_fixed: spellpage_divine_fixed
          }
        end
      )

    """
    INSERT INTO spells (
                         name,
                         #{Enum.join(classes, ", ")},
                         minimum,
                         spellpage_arcane,
                         spellpage_divine,
                         minimum_cls,
                         spellpage_arcane_cls,
                         spellpage_divine_cls
                       ) VALUES (
                         '#{sql_escape(entry.name)}',
                         #{Enum.join(result.levels, ", ")},
                         #{result.minimum},
                         #{result.spellpage_arcane},
                         #{result.spellpage_divine},
                         '#{result.minimum_cls}',
                         '#{result.spellpage_arcane_cls}',
                         '#{result.spellpage_divine_cls}'
                       );
    INSERT INTO tagmap (name, tags) VALUES ('#{sql_escape(entry.name)}', '#{entry.school} #{
      entry.subschool
    } #{entry.descriptor}');
    """
  end

  @spec prepare_spell_db(list(), integer(), map(), integer()) :: :ok | {:error, term()}
  def prepare_spell_db(spelldata, spelltstamp, classdata, clasststamp) do
    classes = Map.keys(classdata)
    columns = [:minimum, :spellpage_arcane, :spellpage_divine | classes]

    Logger.debug("Initializing spell database.")

    :ok =
      SpellDB.exec(@spell_db, """
      DROP TABLE IF EXISTS spells;
      DROP TABLE IF EXISTS tagmap;
      DROP TABLE IF EXISTS info;
      #{EEx.eval_string(@spells_schema, classes: classes)}
      #{@tagmap_schema}
      #{@info_schema}
      PRAGMA journal_mode='MEMORY';
      PRAGMA synchronous='NORMAL';
      INSERT INTO info (id, data) VALUES ('columns', '#{Enum.join(columns, " ")}');
      INSERT INTO info (id, data) VALUES ('classes', '#{Enum.join(classes, " ")}');
      VACUUM;
      """)

    _ =
      spelldata
      |> Stream.chunk_every(50)
      |> Enum.map(fn item ->
        {classdata, item}
      end)
      |> Enum.with_index()
      |> Task.async_stream(
        fn {{classdata, item}, index} ->
          {:ok, [%{data: columns}]} =
            SpellDB.query(@spell_db, "SELECT data FROM info WHERE id='classes';")

          rev_columns = columns |> String.split(" ", trim: true) |> Enum.reverse()

          sql =
            Enum.reduce(item, "", fn entry, acc ->
              cmd = process_spell(entry, rev_columns, classdata, classes)
              "#{acc}\n#{cmd}"
            end)

          Logger.debug("Writing chunk #{index} to spell database.")

          SpellDB.exec(@spell_db, sql)

          []
        end,
        max_concurrency: min(System.schedulers_online(), 8),
        ordered: false,
        timeout: 60_000
      )
      |> Enum.to_list()

    Logger.debug("Finalizing spell database.")

    :ok =
      SpellDB.exec(@spell_db, """
        INSERT INTO info (id, data) VALUES ('rev', '#{@schema_rev}');
        INSERT INTO info (id, data) VALUES ('spell_mtime', '#{spelltstamp}');
        INSERT INTO info (id, data) VALUES ('class_mtime', '#{clasststamp}');
        PRAGMA optimize;
      """)

    Logger.notice("Finished regenerating spell database.")

    :ok
  end

  @spec start_link(term()) :: GenServer.on_start()
  def start_link(_) do
    Logger.info("Starting #{__MODULE__}.")

    GenServer.start_link(__MODULE__, [], name: {:via, Registry, {Roll35Core.Registry, :spell}})
  end

  @impl GenServer
  def init(_) do
    {:ok, %{}, {:continue, :init}}
  end

  @impl GenServer
  def handle_continue(:init, _) do
    {:noreply, load_data()}
  end

  @impl GenServer
  def handle_call({:query, sql, bind}, _from, state) do
    {:reply, SpellDB.query(@spell_db, sql, bind), state}
  end

  @impl GenServer
  def handle_call(:get_classes, _from, state) do
    {:reply, {:ok, Map.keys(state.class)}}
  end

  @impl GenServer
  def handle_call({:get_class, cls}, _from, state) do
    if Map.has_key?(state.class, cls) do
      {:reply, {:ok, state.class[cls]}, state}
    else
      {:reply, {:error, "Not a known class."}, state}
    end
  end

  @doc """
  Get a list of known class identifiers.
  """
  @spec get_classes(GenServer.server()) :: [atom(), ...]
  def get_classes(server) do
    {:ok, ret} = GenServer.call(server, :get_classes, 15_000)

    ret
  end

  @doc """
  Select a random spell.

  This takes a keyword list with three optional keys to limit the list
  of spells to select from:

  `level`: Specifies a spell level to limit the search to. This should be
  an integer ranging from 0 to 9. It can be either omitted or specified as
  `nil` to not limit the search by level.

  `class`: Specifies the class spell list to search within. This should be
  a string with the class name in lower-case with any spaces replaced by
  `_`. In addition to the standard class names, there are three special
  values this can take. `minimum` searches for the spell based on the
  lowest level it appears at on any class list. `spellpage_arcane`
  uses the rules for finding an arcane spell for a ‘Page of Spell
  Knowledge’ (highest level it appears in any arcane caster class
  list, unless it appears on the wizard list in which case it uses that
  level). `spellpage_divine` uses the rules for finding a divine spell for
  a ‘Page of Spell Knowledge’ (same as arcane, just for divine spells
  and using the cleric list instead of the wizard list). `spellpage` picks
  one of `spellpage_arcane` or `spellpage_divine` at random. `random`
  picks a class completely at random. If unspecified, defaults to
  `"minimum"`.

  `tag`: Specifies an optional school, subschool, or descriptor to use to
  further limit the search. The tag must be a lower-case string with any
  special characters replaced with `_`. If left unspecified or specified
  as `nil`, tag-based filtering is not done.

  Note that level and class-based searches are relatively fast because
  they can be run as a single query against the database, but filtering
  by tag is noticeably slower as it requires a second query (involving
  the SQLite FTS5 extension) and some post-processing of the data outside
  of the database. Searches that only look for a tag are especially slow.
  """
  @spec random(GenServer.server(), keyword()) :: {:ok, term()} | {:error, term()}
  def random(server, options) do
    level = Keyword.get(options, :level)
    opt_class = Keyword.get(options, :class, "minimum")
    tag = Keyword.get(options, :tag)

    Logger.debug("Rolling random spell with parameters #{inspect({level, opt_class, tag})}.")

    {:ok, valid_cls_result} = GenServer.call(server, :get_classes, 5_000)

    valid_classes = Enum.each(valid_cls_result, &Atom.to_string/1)

    {:ok, [%{data: valid_col_result}]} =
      GenServer.call(server, {:query, "SELECT data FROM info WHERE id='columns';", []}, 5_000)

    valid_columns = String.split(valid_col_result, " ")

    class =
      cond do
        opt_class == "spellpage" ->
          Enum.random(["spellpage_arcane", "spellpage_divine"])

        opt_class == "random" and level == nil ->
          Enum.random(valid_classes)

        opt_class == "random" and level != nil ->
          valid_classes
          |> Enum.filter(fn item ->
            {:ok, clsinfo} = GenServer.call(server, {:get_class, String.to_existing_atom(item)})
            length(clsinfo.levels) > level
          end)
          |> Enum.random()

        opt_class == nil ->
          "minimum"

        opt_class in valid_columns ->
          opt_class

        true ->
          nil
      end

    cond do
      class == nil ->
        {:error, "Invalid class identifier specified."}

      level != nil and not (level in 0..@max_spell_level) ->
        {:error, "Invalid spell level specified."}

      true ->
        base_list =
          if level != nil do
            {:ok, results} =
              GenServer.call(
                server,
                {:query, "SELECT * FROM spells WHERE #{class} = #{level};", []},
                15_000
              )

            results
          else
            {:ok, results} =
              GenServer.call(
                server,
                {:query, "SELECT * FROM spells WHERE #{class} IS NOT NULL;", []},
                15_000
              )

            results
          end

        tag_filter =
          if tag != nil do
            {:ok, results} =
              GenServer.call(
                server,
                {:query, "SELECT name FROM tagmap WHERE tags MATCH '#{tag}';", []},
                15_000
              )

            Enum.map(results, fn item -> item.name end)
          else
            nil
          end

        possible =
          if tag_filter != nil do
            Enum.filter(base_list, fn item -> item.name in tag_filter end)
          else
            base_list
          end

        if Enum.empty?(possible) do
          {:error, "No spells found for the requested parameters."}
        else
          spell = Enum.random(possible)

          cls =
            case class do
              "minimum" -> String.to_existing_atom(spell.minimum_cls)
              "spellpage_arcane" -> String.to_existing_atom(spell.spellpage_arcane_cls)
              "spellpage_divine" -> String.to_existing_atom(spell.spellpage_divine_cls)
              _ -> String.to_existing_atom(class)
            end

          {:ok, clsinfo} = GenServer.call(server, {:get_class, cls}, 5_000)
          caster_level = Enum.at(clsinfo.levels, spell[cls])

          {:ok, "#{spell.name} (#{Atom.to_string(cls)} CL #{caster_level})"}
        end
    end
  end
end
