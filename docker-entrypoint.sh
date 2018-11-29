#!/bin/bash

Mode="${MODE:-SANDBOX_NETX_KAFKA_AWS}"

if [ "$Mode" = "SANDBOX_NETX_LOCALPOLLER" ]; then
    python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --dealfinder=networkx 2> ./results/errorlog.txt
else
    if [ "$Mode" = "SANDBOX_NEO4J_LOCALPOLLER" ]; then
        python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --neo4jmode=aws --dealfinder=neo4j 2> ./results/errorlog.txt
    else
        if [ "$Mode" = "SANDBOX_NETX_KAFKA_AWS" ]; then
            python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --dealfinder=networkx --datasource=kafkaaws 2> ./results/errorlog.txt
        else
            if [ "$Mode" = "LIVE_NETX_KAFKA_AWS" ]; then
                python ./src/FrameworkLive.py --noforex --resultsdir=./results/ --dealfinder=networkx --datasource=kafkaaws --output=kafkaaws --live 2> ./results/errorlog.txt
            fi
        fi
    fi
fi
