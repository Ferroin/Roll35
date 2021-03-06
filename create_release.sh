#!/bin/bash

if [ "$(git status --porcelain | wc -l)" -ne 0 ] ; then
    echo "You have uncommitted changes in the working directory. Please discard or commit them before attempting to prepare a release."
    exit 1
fi

if mix git_hooks.run pre-push ; then
    base="$(git describe --tags --abbrev=0)"
    bot_vsn="$(grep 'version: ".*",' apps/roll35_bot/mix.exs | cut -d ':' -f 2 | tr -d ' ,')"
    core_vsn="$(grep 'version: ".*",' apps/roll35_core/mix.exs | cut -d ':' -f 2 | tr -d ' ,')"
    project_vsn="$(grep 'version: ".*",' mix.exs | cut -d ':' -f 2 | tr -d ' ,')"

    if git diff --quiet --exit-code ${base} HEAD apps/roll35_bot/ ; then
        echo "Bot unchanged, keeping existing version number (${bot_vsn})."
    else
        echo "Bot changed, please enter a new version number (previous version ${bot_vsn}):"
        read

        ex -s -c "%s/version: ${bot_vsn},/version: \"${REPLY}\",/" -c "wq" apps/roll35_bot/mix.exs
    fi

    if git diff --quiet --exit-code ${base} HEAD apps/roll35_core/ ; then
        echo "Core unchanged, keeping existing version number (${core_vsn})."
    else
        echo "Core changed, please enter a new version number (previous version ${core_vsn}):"
        read

        ex -s -c "%s/version: ${core_vsn},/version: \"${REPLY}\",/" -c "wq" apps/roll35_core/mix.exs
    fi

    echo "Enter new version number for project (current version: ${project_vsn}):"
    read

    ex -s -c "%s/version: ${project_vsn},/version: \"${REPLY}\",/" -c "wq" mix.exs

    git commit --no-verify -a -m "Version ${REPLY} release."

    git tag v${REPLY}

    git push --no-verify origin v${REPLY}
    git push --no-verify origin main
else
    echo "Git pre-push hook failures must be corrected before producing a release."
    exit 1
fi
