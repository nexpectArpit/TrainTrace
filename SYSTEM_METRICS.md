# TrainTrace dataset and model dimensions

CIFAR-10 and CIFAR-100 each contain 60,000 RGB images of 32×32 pixels, in 10 and 100 classes respectively. The application uses 45,000 training images, 5,000 validation images and 10,000 holdout test images. Split identity is controlled by a separate split seed and stored as an artifact/hash. Training augmentation is random cropping with 4-pixel padding and horizontal flipping; evaluation resizes to 32×32 and applies the selected dataset's recorded normalization.

At batch size 64, these partitions require 704, 79 and 157 batches respectively. At 128 they require 352, 40 and 79; at 256 they require 176, 20 and 40. The final batch may be smaller. A full `[64,3,32,32]` FP32 input tensor contains 196,608 values, occupying 786,432 bytes before activation/gradient/optimizer memory.

## Actual parameter counts

Counts below are computed with `sum(p.numel() for p in model.parameters())` for the default 10-class heads and default CustomCNN profile. CIFAR-100 and user-configured CustomCNN profiles have different parameter counts; the dashboard reports the count measured from each actual model. FP32 parameter bytes alone do not include buffers, optimizer states, serialization overhead, or runtime activations. The dashboard reports the actual checkpoint file size separately.

| Architecture | Parameters | FP32 parameter MB (decimal) |
|---|---:|---:|
| CustomCNN | 620,810 | 2.483 |
| ResNet-18 (CIFAR stem) | 11,173,962 | 44.696 |
| MobileNetV2 | 2,236,682 | 8.947 |
| EfficientNet-B0 | 4,020,358 | 16.081 |

Accuracy is reported as **0–100 percent**. Precision, recall and F1 use **0–1**. Accuracy spread and overfitting gap use percentage points. The overfitting gap compares training and validation from the same final epoch; training augmentation/dropout can make this negative.

Holdout latency is the batched wall time including loading/transfers divided by sample count. It is not single-image serving latency. Prediction responses measure model forward execution plus probability transfer separately and identify the model version. Compare latency only under matching hardware, batch and evaluation conditions.

Worker device selection uses CUDA, then MPS, then CPU unless overridden. Actual dataset/configuration/environment/source hashes are captured per new run. Legacy observations without these snapshots remain unverified. Model quality depends on the training configuration; a one-epoch acceptance run is not an accuracy benchmark.

## Kaggle live telemetry

Kaggle runs retain sampled batch loss, running accuracy, throughput, PyTorch-allocated device memory, worker CPU and resident memory. When `nvidia-smi` exposes the fields, TrainTrace also records GPU compute utilization, total GPU memory use and utilization, temperature, and power draw. The worker samples these alongside training batches and the UI refreshes from the persisted run samples. GPU-wide memory includes allocations from the full Kaggle process, while PyTorch device memory is the current process's allocator measurement; these values are related but not interchangeable. Unsupported system fields remain empty rather than being reported as zero. Epoch metrics remain in the same run history, and downloadable CSVs plus checkpoint, dataset split, preview, and training-curve artifacts are retained after completion.
