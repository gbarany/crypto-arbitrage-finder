docker build -t "orderbook-analyser" .
docker run -it --mount type=bind,source="$(pwd)"/results,target=/app/results --name "orderbook-analyser-instance" "orderbook-analyser"