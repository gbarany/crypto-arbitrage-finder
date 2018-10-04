#!/bin/bash

Mode="${MODE:-LIVEWITHNEO4J}"

if [ "$Mode" = "LIVE" ]; then
    python ./src/FrameworkLive.py --noplot --noforex --resultsdir=./results/
else
    if [ "$Mode" = "SIMDB" ]; then
        python ./src/FrameworkSimDB.py --resultsdir=./results/ #--limit=5000
    else
        if [ "$Mode" = "LIVEWITHNEO4J" ]; then
            python ./src/FrameworkLive.py --noplot --noforex --resultsdir=./results/ --neo4jmode=aws
        fi
    fi
fi
