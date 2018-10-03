docker rm orderbook-analyser-instance-live
docker run -it \
    --mount type=bind,source="$(pwd)"/results,target=/app/results \
    --mount type=bind,source="$(pwd)"/cred,target=/app/cred \
    -e MODE='LIVEWITHNEO4J' \
    --name "orderbook-analyser-instance-live" "orderbook-analyser"