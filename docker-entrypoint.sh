#!/bin/bash

Mode="${MODE:-LIVE}"

if [ "$Mode" = "LIVE" ]; then
    python ./src/FrameworkLive.py --noplot --resultsdir=./results/
else
    if [ "$Mode" = "SIMDB" ]; then
        python ./src/FrameworkSimDB.py --resultsdir=./results/ #--limit=5000
    fi
fi
