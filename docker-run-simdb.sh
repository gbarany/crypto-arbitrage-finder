docker rm orderbook-analyser-instance-simdb
docker run -it --mount type=bind,source="$(pwd)"/results,target=/app/results -e MODE='SIMDB' --name "orderbook-analyser-instance-simdb" "orderbook-analyser"