#!/bin/bash
# portable static CPU llama-server for the local analyst (AVX2 baseline, no GPU, no web UI, only libc/libm): ends up in omnipool/rt/llama-server, build.sh packs it into the binary
# LLAMA_SRC = a llama.cpp checkout that knows Qwen3.5 (tested: commit de69995); heavy -> mem-guard + lowprio
set -e
cd "$(dirname "$0")/.."
SRC="${LLAMA_SRC:?set LLAMA_SRC to a llama.cpp checkout (commit de69995 or newer)}"
B="$HOME/omnipool-build/llama-static"; mkdir -p "$B" omnipool/rt
mem-guard || { echo "machine busy (mem-guard), try again later"; exit 75; }
lowprio -m 3G -c 200 -- cmake -S "$SRC" -B "$B" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_BMI2=ON -DGGML_AVX512=OFF \
  -DGGML_OPENMP=OFF -DGGML_VULKAN=OFF -DGGML_CUDA=OFF -DGGML_HIP=OFF -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF \
  -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc"
lowprio -m 4G -c 400 -- ninja -C "$B" -j6 llama-server
cp "$B/bin/llama-server" omnipool/rt/llama-server && strip omnipool/rt/llama-server
sha256sum omnipool/rt/llama-server
