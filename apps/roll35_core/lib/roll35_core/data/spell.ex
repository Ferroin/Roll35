defmodule Roll35Core.Data.Spell do
  @moduledoc """
  Data handling for spells.
  """

  # Due to complexities and caching requirements, we need to implement
  # this from scratch instead of building on Roll35Core.Data.Agent.
  use GenServer

  alias Roll35Core.DB
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
  @max_spell_level 9

  @spec sql_escape(String.t()) :: String.t()
  defp sql_escape(string) do
    String.replace(string, "'", "''")
  end

  @spec load_data({GenServer.server(), Path.t(), Path.t()}) :: term()
  def load_data({spell_db, spath, cpath}) do
    spellpath = Path.join(Application.app_dir(:roll35_core), spath)
    classpath = Path.join(Application.app_dir(:roll35_core), cpath)

    spelltstamp = File.stat!(spellpath, time: :posix).mtime
    clasststamp = File.stat!(classpath, time: :posix).mtime

    classdata =
      classpath
      |> YamlElixir.read_from_file!()
      |> Util.atomize_map()
      |> Enum.map(fn {key, value} ->
        {
          key,
          value
          |> Map.replace(:copy, value |> Map.get(:copy, "nil") |> String.to_existing_atom())
          |> Map.replace(
            :merge,
            value |> Map.get(:merge, []) |> Enum.map(&String.to_existing_atom/1)
          )
        }
      end)
      |> Map.new()

    try do
      {:ok, [%{data: rev}]} = DB.query(spell_db, "SELECT data FROM info WHERE id='rev';")

      {:ok, [%{data: mtime1}]} =
        DB.query(spell_db, "SELECT data FROM info WHERE id='spell_mtime;'")

      {:ok, [%{data: mtime2}]} =
        DB.query(spell_db, "SELECT data FROM info WHERE id='class_mtime;'")

      if rev != @schema_rev or Integer.parse(mtime1, 10) != spelltstamp or
           Integer.parse(mtime2, 10) != clasststamp do
        Logger.notice("DB out of sync with data, regenerating it from spell data.")
        spelldata = YamlElixir.read_from_file!(spellpath)

        :ok = prepare_spell_db(spell_db, spelldata, spelltstamp, classdata, clasststamp)
      else
        Logger.info("DB timestamps and schema match, using existing database.")
      end
    rescue
      e ->
        Logger.notice("Unable to read spell DB, regenerating it from spell data.")
        Logger.debug(inspect(e))
        spelldata = YamlElixir.read_from_file!(spellpath)

        :ok = prepare_spell_db(spell_db, spelldata, spelltstamp, classdata, clasststamp)
    end

    %{db: spell_db, class: classdata}
  end

  defp eval_minimum(level, cls, minimum, minimum_cls) when level == minimum and minimum_cls == "",
    do: {level, cls}

  defp eval_minimum(level, cls, minimum, _minimum_cls) when level != "NULL" and level < minimum,
    do: {level, cls}

  defp eval_minimum(level, cls, minimum, _minimum_cls) when level != "NULL" and minimum == "NULL",
    do: {level, cls}

  defp eval_minimum(_level, _cls, minimum, minimum_cls), do: {minimum, minimum_cls}

  defp eval_spellpage(_level, _cls, spellpage, spellpage_cls, spellpage_fixed, _cls_match)
       when spellpage_fixed == true,
       do: {spellpage, spellpage_cls, true}

  defp eval_spellpage(level, cls, _spellpage, _spellpage_cls, _spellpage_fixed, cls_match)
       when cls_match == true and level != "NULL",
       do: {level, cls, true}

  defp eval_spellpage(level, cls, spellpage, _spellpage_cls, _spellpage_fixed, _cls_match)
       when level != "NULL" and spellpage < level,
       do: {level, cls, false}

  defp eval_spellpage(level, cls, spellpage, _spellpage_cls, _spellpage_fixed, _cls_match)
       when level != "NULL" and spellpage == "NULL",
       do: {level, cls, false}

  defp eval_spellpage(_level, _cls, spellpage, spellpage_cls, spellpage_fixed, _cls_match),
    do: {spellpage, spellpage_cls, spellpage_fixed}

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
        fn cls, acc ->
          ilevel =
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
                    entry.classes[Enum.at(classdata[cls].merge, 0)]

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
              ilevel != "NULL" and ilevel >= length(classdata[cls].levels) and
                  (:copy in Map.keys(classdata[cls]) or :merge in Map.keys(classdata[cls])) ->
                "NULL"

              ilevel != "NULL" and ilevel >= length(classdata[cls].levels) ->
                Logger.warning(
                  "#{entry.name} has invalid spell level for class #{cls}, ignoring."
                )

                "NULL"

              true ->
                ilevel
            end

          {minimum, minimum_cls} = eval_minimum(level, cls, acc.minimum, acc.minimum_cls)

          {spellpage_arcane, spellpage_arcane_cls, spellpage_arcane_fixed} =
            if classdata[cls].type == "arcane" do
              eval_spellpage(
                level,
                cls,
                acc.spellpage_arcane,
                acc.spellpage_arcane_cls,
                acc.spellpage_arcane_fixed,
                cls == :wizard
              )
            else
              {acc.spellpage_arcane, acc.spellpage_arcane_cls, acc.spellpage_arcane_fixed}
            end

          {spellpage_divine, spellpage_divine_cls, spellpage_divine_fixed} =
            if classdata[cls].type == "divine" do
              eval_spellpage(
                level,
                cls,
                acc.spellpage_divine,
                acc.spellpage_divine_cls,
                acc.spellpage_divine_fixed,
                cls == :cleric
              )
            else
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

    {
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
      """,
      [
        entry.school,
        entry.subschool
        | String.split(entry.descriptor, ", ")
      ]
    }
  end

  @spec prepare_spell_db(GenServer.server(), list(), integer(), map(), integer()) ::
          :ok | {:error, term()}
  def prepare_spell_db(spell_db, spelldata, spelltstamp, classdata, clasststamp) do
    classes = Map.keys(classdata)
    columns = classes ++ [:minimum, :spellpage_arcane, :spellpage_divine]

    Logger.debug("Initializing spell database.")

    :ok =
      DB.exec(spell_db, """
      DROP TABLE IF EXISTS spells;
      DROP TABLE IF EXISTS tagmap;
      DROP TABLE IF EXISTS info;
      #{EEx.eval_string(@spells_schema, classes: classes)}
      #{@tagmap_schema}
      #{@info_schema}
      PRAGMA journal_mode='WAL';
      PRAGMA synchronous='NORMAL';
      INSERT INTO info (id, data) VALUES ('columns', '#{Enum.join(columns, " ")}');
      INSERT INTO info (id, data) VALUES ('classes', '#{Enum.join(classes, " ")}');
      VACUUM;
      """)

    tags =
      spelldata
      |> Stream.chunk_every(50)
      |> Enum.map(fn item ->
        {classdata, classes, item}
      end)
      |> Enum.with_index()
      |> Task.async_stream(
        fn {{classdata, columns, item}, index} ->
          rev_columns = Enum.reverse(columns)

          {tags, sql} =
            Enum.reduce(item, {MapSet.new(), ""}, fn entry, {tags, cmd} ->
              {new_cmd, item_tags} = process_spell(entry, rev_columns, classdata, classes)

              new_tags = MapSet.union(tags, MapSet.new(item_tags))

              {new_tags, "#{cmd}\n#{new_cmd}"}
            end)

          Logger.debug("Writing chunk #{index} to spell database.")

          DB.exec(spell_db, sql)

          tags
        end,
        max_concurrency: min(System.schedulers_online(), 8),
        ordered: false,
        timeout: 60_000
      )
      |> Stream.map(fn {:ok, i} -> i end)
      |> Enum.reduce(MapSet.new(), &MapSet.union/2)
      |> MapSet.to_list()

    Logger.debug("Finalizing spell database.")

    :ok =
      DB.exec(spell_db, """
        INSERT INTO info (id, data) VALUES ('tags', '#{Enum.join(tags, ", ")}');
        INSERT INTO info (id, data) VALUES ('rev', '#{@schema_rev}');
        INSERT INTO info (id, data) VALUES ('spell_mtime', '#{spelltstamp}');
        INSERT INTO info (id, data) VALUES ('class_mtime', '#{clasststamp}');
        PRAGMA optimize;
      """)

    Logger.notice("Finished regenerating spell database.")

    :ok
  end

  @spec start_link(
          name: GenServer.server(),
          spellpath: Path.t(),
          classpath: Path.t(),
          dbpath: Path.t()
        ) :: GenServer.on_start()
  def start_link(params) do
    [{:name, name} | initargs] = params

    Logger.info("Starting #{__MODULE__}.")

    GenServer.start_link(__MODULE__, initargs, name: name)
  end

  @impl GenServer
  def init(spellpath: spellpath, classpath: classpath, dbpath: dbpath) do
    {:ok, pid} = DB.start_link(Path.join(dbpath, "spells.sqlite3"))

    {:ok, %{db: pid, spellpath: spellpath, classpath: classpath}, {:continue, :init}}
  end

  @impl GenServer
  def handle_continue(:init, state) do
    {:noreply, load_data({state.db, state.spellpath, state.classpath})}
  end

  @impl GenServer
  def handle_call(:ready, _from, state) do
    {:reply, :ready, state}
  end

  @impl GenServer
  def handle_call({:query, sql, bind}, _from, state) do
    {:reply, DB.query(state.db, sql, bind), state}
  end

  @impl GenServer
  def handle_call(:get_classes, _from, state) do
    {:reply, {:ok, Map.keys(state.class)}, state}
  end

  @impl GenServer
  def handle_call({:get_class, cls}, _from, state) do
    if Map.has_key?(state.class, cls) do
      {:reply, {:ok, state.class[cls]}, state}
    else
      {:reply, {:error, "Not a known class."}, state}
    end
  end

  @impl GenServer
  def handle_call(:get_tags, _from, state) do
    {:ok, [%{data: tags}]} = DB.query(state.db, "SELECT data FROM info WHERE id='tags';")

    {:reply, {:ok, String.split(tags, ", ", trim: true)}, state}
  end

  @impl GenServer
  def handle_call({:get_spell, name}, _from, state) do
    escaped = sql_escape(name)

    case DB.query(state.db, "SELECT * FROM spells WHERE name='#{escaped}';") do
      {:ok, [spell]} ->
        {:ok, [%{tags: dbtags}]} =
          DB.query(state.db, "SELECT tags FROM tagmap WHERE name='#{escaped}';")

        tags =
          dbtags
          |> String.split()
          |> Enum.map(fn i ->
            String.replace(i, ",", "")
          end)

        {
          :reply,
          {
            :ok,
            spell
            |> Enum.reduce(%{}, fn
              {_, ""}, acc ->
                acc

              {key, _}, acc
              when key in [:minimum_cls, :spellpage_arcane_cls, :spellpage_divine_cls] ->
                acc

              {key, value}, acc ->
                Map.put(acc, key, value)
            end)
            |> Map.new()
            |> Map.put(:tags, tags)
          },
          state
        }

      {:ok, []} ->
        {:reply, {:error, "No such spell."}, state}

      result ->
        {:reply, {:error, result}, state}
    end
  end

  @doc """
  Wait until the server is ready.

  This waits for up to `timeout` miliseconds and returns either `:ready`
  if the server is ready or causes the caller to exit if it is not ready.
  """
  @spec ready?(GenServer.server(), timeout()) :: :ready
  def ready?(server, timeout \\ 30_000) do
    GenServer.call(server, :ready, timeout)
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
  Get a list of known tags.
  """
  @spec get_tags(GenServer.server()) :: [String.t(), ...]
  def get_tags(server) do
    {:ok, ret} = GenServer.call(server, :get_tags, 15_000)

    ret
  end

  @doc """
  Get info about a specific class.
  """
  @spec get_class(GenServer.server(), atom()) :: map()
  def get_class(server, class) do
    GenServer.call(server, {:get_class, class}, 15_000)
  end

  @doc """
  Get info about a spell by spell name.
  """
  @spec get_spell(GenServer.server(), String.t()) :: map()
  def get_spell(server, name) do
    GenServer.call(server, {:get_spell, name}, 15_000)
  end

  defp select_spell(server, nil, cls, nil) do
    {:ok, results} =
      GenServer.call(
        server,
        {
          :query,
          """
          SELECT *
          FROM spells
          WHERE #{cls} IS NOT NULL
          ORDER BY random()
          LIMIT 1;
          """,
          []
        },
        15_000
      )

    results
  end

  defp select_spell(server, level, cls, nil) do
    {:ok, results} =
      GenServer.call(
        server,
        {
          :query,
          """
          SELECT *
          FROM spells
          WHERE #{cls} = #{level}
          ORDER BY random()
          LIMIT 1;
          """,
          []
        },
        15_000
      )

    results
  end

  defp select_spell(server, nil, cls, tag) do
    {:ok, results} =
      GenServer.call(
        server,
        {
          :query,
          """
          SELECT *
          FROM spells
          WHERE #{cls} IS NOT NULL
          AND name IN (
            SELECT name
            FROM tagmap
            WHERE tags MATCH '#{tag}'
          )
          ORDER BY random()
          LIMIT 1;
          """,
          []
        },
        15_000
      )

    results
  end

  defp select_spell(server, level, cls, tag) do
    {:ok, results} =
      GenServer.call(
        server,
        {
          :query,
          """
          SELECT *
          FROM spells
          WHERE #{cls} = #{level}
          AND name IN (
            SELECT name
            FROM tagmap
            WHERE tags MATCH '#{tag}'
          )
          ORDER BY random()
          LIMIT 1;
          """,
          []
        },
        15_000
      )

    results
  end

  @doc """
  Select a random spell.

  This takes a keyword list with three optional keys to limit the list
  of spells to select from:

  `level`: Specifies a spell level to limit the search to. This should be
  an integer ranging from 0 to 9. It can be either omitted or specified as
  `nil` to not limit the search by level.

  `class`: Specifies the class spell list to search within. This should be
  an atom with the class name in lower-case with any spaces replaced by
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
  def random(server, options \\ [class: :minimum]) do
    level = Keyword.get(options, :level)

    opt_class =
      options
      |> Keyword.get(:class, :minimum)
      |> (fn
            item when is_atom(item) ->
              item

            item ->
              try do
                String.to_existing_atom(item)
              rescue
                _ -> false
              end
          end).()

    tag = Keyword.get(options, :tag)

    Logger.debug("Rolling random spell with parameters #{inspect({level, opt_class, tag})}.")

    {:ok, valid_classes} = GenServer.call(server, :get_classes, 5_000)

    valid_columns = [:spellpage_arcane, :spellpage_divine, :minimum | valid_classes]

    class =
      cond do
        opt_class == :spellpage ->
          Util.random([:spellpage_arcane, :spellpage_divine])

        opt_class == :random and level == nil ->
          Util.random(valid_classes)

        opt_class == :random and level != nil ->
          valid_classes
          |> Enum.filter(fn item ->
            {:ok, clsinfo} = GenServer.call(server, {:get_class, String.to_existing_atom(item)})
            length(clsinfo.levels) > level
          end)
          |> Util.random()

        opt_class == nil ->
          :minimum

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
        case select_spell(server, level, class, tag) do
          [spell] ->
            cls =
              case class do
                :minimum -> String.to_existing_atom(spell.minimum_cls)
                :spellpage_arcane -> String.to_existing_atom(spell.spellpage_arcane_cls)
                :spellpage_divine -> String.to_existing_atom(spell.spellpage_divine_cls)
                _ -> class
              end

            {:ok, clsinfo} = GenServer.call(server, {:get_class, cls}, 5_000)
            caster_level = Enum.at(clsinfo.levels, spell[cls])

            {:ok, "#{spell.name} (#{Atom.to_string(cls)} CL #{caster_level})"}

          [] ->
            {:error, "No spells found for the requested parameters."}
        end
    end
  end
end
