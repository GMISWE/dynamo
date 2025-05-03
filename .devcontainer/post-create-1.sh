#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

trap 'echo "❌ ERROR: Command failed at line $LINENO: $BASH_COMMAND"; echo "⚠️ This was unexpected and setup was not completed. Can try to resolve yourself and then manually run the rest of the commands in this file or file a bug."' ERR

retry() {
    # retries for connectivity issues in installs
    local retries=3
    local count=0
    until "$@"; do
        exit_code=$?
        wait_time=$((2 ** count))
        echo "Command failed with exit code $exit_code. Retrying in $wait_time seconds..."
        sleep $wait_time
        count=$((count + 1))
        if [ $count -ge $retries ]; then
            echo "Command failed after $retries attempts."
            return $exit_code
        fi
    done
    return 0
}

pre_check() {
    cd ~/software
    if ! command -v kubectl &> /dev/null; then
        cp kubectl-cf kubectl /usr/local/bin
    fi
    if ! command -v helm &> /dev/null; then
        ./get_helm.sh
    fi
    if ! command -v karmadactl &> /dev/null; then
        ./install-karmadactl.sh
    fi
    
    # 检查并安装 docker-cli
    if ! command -v docker &> /dev/null; then
        echo "正在安装 docker-cli..."
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update
        apt-get install -y docker-ce-cli
    else
        echo "docker-cli 已安装，跳过安装步骤"
    fi
    
    # 检查并安装 gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        echo "正在安装 gcloud CLI..."
        apt-get update
        apt-get install -y apt-transport-https ca-certificates gnupg curl
        echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
        curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
        apt-get update
        apt-get install -y google-cloud-cli
    else
        echo "gcloud CLI 已安装，跳过安装步骤"
    fi
    cd -
}

set -xe

pre_check
# Changing permission to match local user since volume mounts default to root ownership
# sudo chown -R ubuntu:ubuntu ~/.cache/pre-commit

HOME=/workspace
# Pre-commit hooks
# cd $HOME/dynamo && pre-commit install && retry pre-commit install-hooks
# pre-commit run --all-files || true # don't fail the build if pre-commit hooks fail

# Set build directory
mkdir -p $HOME/target
export CARGO_TARGET_DIR=/workspace/target

# build project, it will be saved at $HOME/target
cargo build --locked --profile dev --features mistralrs,sglang,vllm,python
cargo doc --no-deps

# create symlinks for the binaries in the deploy directory
mkdir -p $HOME/dynamo/deploy/dynamo/sdk/src/dynamo/sdk/cli/bin
ln -sf /workspace/target/debug/dynamo-run /workspace/deploy/dynamo/sdk/src/dynamo/sdk/cli/bin/dynamo-run && \
ln -sf /workspace/target/debug/http /workspace/deploy/dynamo/sdk/src/dynamo/sdk/cli/bin/http && \
ln -sf /workspace/target/debug/llmctl /workspace/deploy/dynamo/sdk/src/dynamo/sdk/cli/bin/llmctl && \
ln -sf /workspace/target/debug/metrics /workspace/deploy/dynamo/sdk/src/dynamo/sdk/cli/bin/metrics

# install the python bindings in editable mode
cd $HOME/lib/bindings/python && retry uv pip install -e .
cd $HOME && retry env DYNAMO_BIN_PATH=$HOME/target/debug uv pip install -e .

# source the venv and set the VLLM_KV_CAPI_PATH in bashrc
echo "source /opt/dynamo/venv/bin/activate" >> /root/.zshrc
echo "export VLLM_KV_CAPI_PATH=$HOME/target/debug/libdynamo_llm_capi.so" >> /root/.zshrc
# echo "export GPG_TTY=$(tty)" >> ~/.zshrc
