#!/bin/bash

Mode="${MODE:-LIVEWITHNEO4J}"

if [ "$Mode" = "LIVE" ]; then
    python ./src/FrameworkLive.py --noforex --resultsdir=./results/ 2> ./results/errorlog.txt
else
    if [ "$Mode" = "LIVEWITHNEO4J" ]; then
        python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --neo4jmode=aws 2> ./results/errorlog.txt
    fi
fi
