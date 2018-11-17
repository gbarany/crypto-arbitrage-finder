docker run --rm -it \
    --mount type=bind,source="$(pwd)"/results,target=/app/results \
    --mount type=bind,source="$(pwd)"/cred,target=/app/cred \
    -e MODE='LIVE_NETX_LOCALPOLLER' \
    --name "orderbook-analyser-instance-live" "orderbook-analyser"