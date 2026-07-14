Status: done
Created: 2026-07-14
Updated: 2026-07-14

# Open Embedding Backend Bake-off Roster

## Question

Which current open-source local inference backends should be compared for Buoy's exact `BAAI/bge-small-en-v1.5` embedding contract on the Apple M2 Pro host?

## Sources and methods

Web research on 2026-07-14 covered Sentence Transformers' supported inference backends, OpenVINO Apple Silicon support, MLX embedding implementations and converted BGE artifacts, FastEmbed's supported model list, Hugging Face TEI/Candle, Infinity, and direct CoreML/community conversions.

Primary references:

- https://sbert.net/docs/sentence_transformer/usage/efficiency.html
- https://docs.openvino.ai/2025/get-started/install-openvino/install-openvino-macos.html
- https://github.com/Blaizzy/mlx-embeddings
- https://huggingface.co/mlx-community/bge-small-en-v1.5-bf16
- https://github.com/qdrant/fastembed
- https://qdrant.github.io/fastembed/examples/Supported_Models/
- https://github.com/huggingface/text-embeddings-inference
- https://github.com/michaelfeil/infinity
- https://huggingface.co/michaeljelly/bge-small-en-coreml-v1.5
- https://github.com/GarthDB/metal-candle

## Findings

Sentence Transformers officially supports Torch, ONNX, and OpenVINO backends, making ONNX and OpenVINO the lowest-integration-risk alternatives. OpenVINO documents macOS ARM64 CPU support. FastEmbed supports the exact BGE model through ONNX but may use separately converted or quantized artifacts, so parity must decide its viability. `mlx-embeddings` and MLX-community provide an Apple-native BGE path, but model conversion and pooling/tokenization equivalence need direct validation.

TEI and Infinity are server-oriented deployment layers rather than distinct in-process kernels for Buoy's local CLI. Candle/Metal requires a Rust process or extension boundary. Direct CoreML depends on community model conversion and lacks the same stable Python Sentence Transformers contract. They are credible later deployment/integration experiments, but including them now would conflate runtime performance with IPC, service lifecycle, or conversion engineering.

## Conclusion

Benchmark five lanes:

1. Current Sentence Transformers Torch/MPS float32 baseline.
2. Sentence Transformers ONNX Runtime, CPU provider; also test CoreML EP only if the installed supported runtime exposes it without a custom build.
3. Sentence Transformers OpenVINO CPU.
4. FastEmbed ONNX for the exact model.
5. MLX Embeddings using a non-quantized/bfloat16 exact-model artifact.

Use the retained 1,024 Iceberg chunks, batch 32, three warm measurements, one cold load time, process memory, normalized document-vector cosine, and exact ordered top-10 equality. The existing threshold is minimum cosine >= 0.999 and the same top-10 IDs in the same order. Record unsupported or failed lanes rather than silently dropping them. No remote service or write is involved.
