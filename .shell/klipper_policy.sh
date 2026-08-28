#!/bin/sh
# (C) 2026 ghzserg https://github.com/ghzserg/zmod
exit 0

. /usr/data/zmod/zmod/.shell/0.sh

MAX_RETRIES=30
RETRY_COUNT=0

set_klipper_policy() {
    while [ "$RETRY_COUNT" -le "$MAX_RETRIES" ]; do
        PID=$(ps w | grep klippy.py | grep -v grep | awk '{print $1}' | head -n 1)

        if [ -n "$PID" ]; then
            echo "Process found, PID: $PID"

            echo "Checking current policy for PID $PID:"
            chrt -p "$PID"

            chrt -f -p 50 "$PID" && echo "Successfully updated scheduling policy:"

            if [ -d "/proc/$PID/task" ]; then
                echo "Updating scheduling policy for all child threads..."
                for tid_dir in /proc/$PID/task/*; do
                    TID=$(basename "$tid_dir")

                    if [ "$TID" != "$PID" ]; then
                        chrt -f -p 50 "$TID" 2>/dev/null && echo " -> Updated policy for Thread ID: $TID"
                    fi
                done
            fi

            chrt -p "$PID"
            exit 0
        else
            if [ "$RETRY_COUNT" -eq 0 ]; then
                echo "Process not found, waiting 2 seconds before retrying..."
            else
                echo "Retry #$RETRY_COUNT: Process has not started yet, still waiting..."
            fi

            sleep 2
            RETRY_COUNT=$((RETRY_COUNT + 1))
        fi
    done

    echo "Exceeded maximum number of retries ($MAX_RETRIES). Process failed to start."
}

mv ${MOD_CONF}/mod_data/log/klipper_policy.4.log ${MOD_CONF}/mod_data/log/klipper_policy.5.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/klipper_policy.3.log ${MOD_CONF}/mod_data/log/klipper_policy.4.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/klipper_policy.2.log ${MOD_CONF}/mod_data/log/klipper_policy.3.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/klipper_policy.1.log ${MOD_CONF}/mod_data/log/klipper_policy.2.log 2>/dev/null
mv ${MOD_CONF}/mod_data/log/klipper_policy.log ${MOD_CONF}/mod_data/log/klipper_policy.1.log 2>/dev/null

set_klipper_policy >"${MOD_CONF}/mod_data/log/klipper_policy.log" 2>&1
