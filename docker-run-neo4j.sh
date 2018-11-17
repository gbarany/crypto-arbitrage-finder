docker run --rm -it \
    --mount type=bind,source="$(pwd)"/results,target=/app/results \
    --mount type=bind,source="$(pwd)"/cred,target=/app/cred \
    -e MODE='LIVE_NEO4J' \
    -p 3000:3000 \
    --name "orderbook-analyser-instance-live" "orderbook-analyser"