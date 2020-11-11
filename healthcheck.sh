#!/bin/sh

# This uses the Mix release RPC functionality to fetch a list of running
# applications from the BEAM environment and then checks that both the
# core and bot applications are running.

[ "$(/app/bin/roll35_docker rpc "Application.started_applications() |> Enum.each(fn {i, _, _} -> IO.inspect(i) end)" | grep -E ":roll35_core|:roll35_bot" | wc -l)" -eq 2 ]
