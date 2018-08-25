docker rm orderbook-analyser-instance-live
docker run -it --mount type=bind,source="$(pwd)"/results,target=/app/results -e MODE='LIVE' --name "orderbook-analyser-instance-live" "orderbook-analyser"