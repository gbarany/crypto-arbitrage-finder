docker run --rm -it \
    --mount type=bind,source="$(pwd)"/results,target=/app/results \
    --mount type=bind,source="$(pwd)"/cred,target=/app/cred \
    -e MODE='SANDBOX_NEO4J_LOCALPOLLER' \
    -p 3000:3000 \
    --name "orderbook-analyser-instance-live" "orderbook-analyser"