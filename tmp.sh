apt-get update
apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    ca-certificates \
    build-essential \
    lsb-release \
    cmake 

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y --no-install-recommends docker-ce-cli


command:
    - sh
    - '-c'
  args:
    - >-
      cd src && uv run dynamo serve --service-name PrefillWorker graphs.disagg_router:Frontend -f ./configs/disagg_router.yaml

UCX_DC_MLX5_ALLOC=huge,thp,md,mmap,heap
UCX_RC_VERBS_ALLOC=huge,thp,md,mmap,heap
UCX_RC_MLX5_ALLOC=huge,thp,md,mmap,heap
UCX_UD_VERBS_ALLOC=huge,thp,md,mmap,heap
UCX_UD_MLX5_ALLOC=huge,thp,md,mmap,heap
UCX_CMA_ALLOC=huge,thp,mmap,heap

- name: UCX_DC_MLX5_ALLOC
  value: "thp,md,mmap,heap,huge"
- name: UCX_RC_VERBS_ALLOC
  value: "thp,md,mmap,heap,huge"
- name: UCX_RC_MLX5_ALLOC
  value: "thp,md,mmap,heap,huge"
- name: UCX_UD_VERBS_ALLOC
  value: "thp,md,mmap,heap,huge"
- name: UCX_UD_MLX5_ALLOC
  value: "thp,md,mmap,heap,huge"
- name: UCX_CMA_ALLOC
  value: "thp,mmap,heap,huge"


docker run -it --rm --gpus all --user root \
  -e NATS_SERVER=nats://172.30.1.126:4222 \
  -e ETCD_ENDPOINTS=172.30.1.126:2379 \
  -e UCX_LOG_LEVEL=trace \
  -v /root/model_garden:/root/model_garden \
  -v /mnt:/mnt \
  --ipc=host \
  --network host \
  --device /dev/infiniband:/dev/infiniband \
  us-west1-docker.pkg.dev/devv-404803/public/frontend:5zxl5kjfrwsevdtb bash






curl localhost:8010/v1/chat/completions   -H "Content-Type: application/json"   -d '{
    "model": "qwen2.5-0.5b",
    "messages": [
    {
        "role": "user",
        "content": "Hello, how are you?"
    }
    ],
    "stream":false,
    "max_tokens": 300
  }' | jq