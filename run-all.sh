#!/bin/bash

if [ "$1" == "fe" ]; then
    # Run the Frontend
    DYN_JAEGER_ENDPOINT=172.30.1.126:4317 DYN_CIRCUS_PUBSUB_PORT=52345 DYN_CIRCUS_ENDPOINT_PORT=41234 \
        cargo run --bin dynamo-serve -- \
        --service-name Frontend graphs.disagg_router:Frontend \
        -f ./configs/disagg_router-1.yaml
fi


if [ "$1" == "pr" ]; then
    # Run the Backend
    DYN_JAEGER_ENDPOINT=172.30.1.126:4317 DYN_CIRCUS_PUBSUB_PORT=52346 DYN_CIRCUS_ENDPOINT_PORT=41235 \
        cargo run --bin dynamo-serve -- \
        --service-name Processor graphs.disagg_router:Frontend \
        -f ./configs/disagg_router-1.yaml
fi

if [ "$1" == "ro" ]; then
    # Run the Router
    DYN_JAEGER_ENDPOINT=172.30.1.126:4317 DYN_CIRCUS_PUBSUB_PORT=52347 DYN_CIRCUS_ENDPOINT_PORT=41236 \
        cargo run --bin dynamo-serve -- \
        --service-name Router graphs.disagg_router:Frontend \
        -f ./configs/disagg_router-1.yaml
fi

if [ "$1" == "pf" ]; then
    # Run the Router
    DYN_JAEGER_ENDPOINT=172.30.1.126:4317 DYN_CIRCUS_PUBSUB_PORT=52348 DYN_CIRCUS_ENDPOINT_PORT=41237 DYN_DISABLE_AUTO_GPU_ALLOCATION=1 CUDA_VISIBLE_DEVICES=6 \
        cargo run --bin dynamo-serve -- \
        --service-name PrefillWorker graphs.disagg_router:Frontend \
        -f ./configs/disagg_router-1.yaml
fi

if [ "$1" == "de" ]; then
    # Run the Router
    DYN_JAEGER_ENDPOINT=172.30.1.126:4317 DYN_CIRCUS_PUBSUB_PORT=52349 DYN_CIRCUS_ENDPOINT_PORT=41238 DYN_DISABLE_AUTO_GPU_ALLOCATION=1 CUDA_VISIBLE_DEVICES=7 \
        cargo run --bin dynamo-serve -- \
        --service-name VllmWorker graphs.disagg_router:Frontend \
        -f ./configs/disagg_router-1.yaml
fi

if [ "$1" == "fpr" ]; then
    # Run all the services
    ./run-all.sh fe &
    ./run-all.sh pr &
    ./run-all.sh pf &
fi

if [ "$1" == "pd" ]; then
    # Run all the services
    ./run-all.sh pf &
    ./run-all.sh de &
fi

if [ "$1" == "all" ]; then
    # Run all the services
    ./run-all.sh fe &
    ./run-all.sh pr &
    ./run-all.sh ro &
    ./run-all.sh pf &
    ./run-all.sh de &
fi
