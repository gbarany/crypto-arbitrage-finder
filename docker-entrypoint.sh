#!/bin/bash

Mode="${MODE:-LIVEWITHNEO4J}"

if [ "$Mode" = "LIVE_NETX_LOCALPOLLER" ]; then
    python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --dealfinder=networkx 2> ./results/errorlog.txt
else
    if [ "$Mode" = "LIVE_NEO4J_LOCALPOLLER" ]; then
        python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --neo4jmode=aws --dealfinder=neo4j 2> ./results/errorlog.txt
    else
        if [ "$Mode" = "LIVE_NETX_KAFKA_AWS" ]; then
            python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --dealfinder=networkx --datasource=kafkaaws 2> ./results/errorlog.txt
        fi
    fi
fi
