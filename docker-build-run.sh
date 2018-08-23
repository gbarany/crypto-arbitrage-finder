docker build -t "orderbook-analyser" .
docker rm orderbook-analyser-instance
#docker run -it --mount type=bind,source="$(pwd)"/results,target=/app/results -e MODE='LIVE' --name "orderbook-analyser-instance" "orderbook-analyser"
docker run -it --mount type=bind,source="$(pwd)"/results,target=/app/results -e MODE='SIMDB' --name "orderbook-analyser-instance" "orderbook-analyser"