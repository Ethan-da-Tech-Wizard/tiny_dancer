# Reconstruct the current local backend

This repository contains source and installation records. Model weights, compiled
binaries and the machine's private data are separate. The current tested host is
Arch Linux, Python 3.12, Intel i7-12650H, RTX 3070 Laptop (8 GiB VRAM), and 16 GB RAM.
The commands below describe reconstructing that layout; a clean-machine install
has not yet been independently tested. Do not run a model build or download over
an active installation without checking its state.

The current serving backend is **llama.cpp with the original GPT-OSS-20B MXFP4
weights**. Colibri and Picchio remain archived alternatives. The older conversion
instructions in the main README describe the Picchio path.

1. Clone Tiny Dancer to `/mnt/GameDrive/tiny_dancer`, the location currently used
   by launchers. If that folder already contains the working installation, use
   its existing source and the publishing procedure in [GITHUB.md](GITHUB.md).
2. Create `vendor`, `models`, `build`, `run`, `logs`, `workspace` and `cache`.
   Clone each desired upstream URL and check out its exact commit from
   [upstreams.json](upstreams.json). Do not pull newer code into a qualified setup.
   If using Picchio, apply [picchio-local.patch](picchio-local.patch) in that checkout.
3. Create the Python 3.12 virtual environment and install `requirements.lock.txt`
   using the README's `uv pip sync` command. Download Playwright Chromium for
   browser tools using `.venv/bin/python -m playwright install chromium` with
   `scripts/env.sh` sourced. Host tools and their recorded versions are in
   [the license inventory](../licenses/README.md).
4. Build the pinned llama.cpp checkout with the existing CUDA toolkit:

   ```bash
   cmake -S vendor/llama.cpp -B build/llama-reference \
     -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release
   cmake --build build/llama-reference --target llama-server -j2
   ```

5. Download `gpt-oss-20b-MXFP4.gguf` from Hugging Face repository
   `ggml-org/gpt-oss-20b-GGUF`, revision
   `ef9b12f2ff56c69cf32153a02784e7a3c88bf524`, into
   `models/gpt-oss-20b-native-mxfp4`. Preserve the accompanying LICENSE and
   USAGE_POLICY. The recorded file size is 12,109,566,624 bytes; its SHA-256 must be
   `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`.
   [Source record](llama-reference-model-source.json) and
   [original model notices](../licenses/models/gpt-oss-20b-original/) are included.
   Existing fidelity reports describe the original installation; independently
   verify new downloads instead of treating those reports as a check of new bytes.
6. Start with `scripts/start.sh` from the established layout and visit
   `http://127.0.0.1:3210`. The runtime creates its own private authentication token
   and local history. Desktop integration depends on the host's editor and Wayland
   tools; it is not supplied by the model.
7. The optional [model cache](MODEL_CACHE.md) can retain an identical model copy
   on a faster drive. Missing or invalid caches fall back to the original model.
   Avoid launching two inference processes on this hardware.

No Ollama or hosted model API is used. Downloading source and weights requires
network access; inference remains local. Keep current and failed validation
reports: the small coding pass does not yet establish general long-task completion.
