# TrainTrace — System Metrics, Dataset Specs & Runtime Numbers

> **Reference Guide:** Technical dimensions, dataset partition numbers, batch math, and model parameter sizes powering the TrainTrace pipeline.

---

## 1. 📊 Dataset Specifications (CIFAR-10)

The core computer vision benchmark configured in `traintrace/backend/core/dataset.py`:

| Property | Value | Description |
| :--- | :--- | :--- |
| **Dataset Name** | CIFAR-10 | Canonical 10-class vision classification benchmark |
| **Total Images** | **60,000 images** | 6,000 images per category (perfectly balanced) |
| **Image Resolution** | **32 x 32 pixels** | Standardized input dimensions |
| **Color Channels** | **3 (RGB)** | Red, Green, Blue channels |
| **Numbers per Image** | **3,072 floats** | 3 channels * 32 height * 32 width |
| **Storage Footprint** | **~163 MB – 180 MB** | Cached locally in `backend/storage/data/` |
| **10 Target Classes** | `airplane`, `automobile`, `bird`, `cat`, `deer`, `dog`, `frog`, `horse`, `ship`, `truck` | Indexed with class IDs `0` through `9` |

### Partition Splits in Pipeline

* **🏋️ Training Set (`train_loader`)**: **45,000 images** (90% of training split)
  * Data Augmentations: Random 4px padded cropping (`RandomCrop(32, padding=4)`) and random horizontal flipping (`RandomHorizontalFlip(p=0.5)`).
* **🧪 Validation Set (`val_loader`)**: **5,000 images** (10% of training split)
  * Deterministic normalization only. Evaluated after every training epoch for loss and accuracy curves.
* **🎯 Test Set (`test_loader`)**: **10,000 images**
  * Fully independent holdout dataset. Used for final candidate evaluation, Protocol A (deterministic bitwise check), and Protocol B (multi-seed sensitivity analysis).

---

## 2. 🔢 Runtime Execution Numbers & Batch Mathematics

Calculations based on default batch size of **64**:

| Runtime Dimension | Exact Number | Calculation / Explanation |
| :--- | :--- | :--- |
| **Mini-Batch Tensor Shape** | `[64, 3, 32, 32]` | 64 images grouped into a single multidimensional tensor |
| **Values per Mini-Batch** | **196,608 floats** | 64 images * 3 channels * 32 height * 32 width |
| **Batch Memory Size (FP32)** | **~786 KB** | 196,608 floats * 4 bytes per float |
| **Training Steps per Epoch** | **704 batches** | 45,000 training images / 64 batch size = 704 iterations |
| **Validation Steps per Epoch** | **79 batches** | 5,000 validation images / 64 batch size = 79 iterations |
| **Holdout Test Steps** | **157 batches** | 10,000 test images / 64 batch size = 157 iterations |
| **Output Logits Tensor** | `[64, 10]` | 10 unnormalized class confidence scores per image |

---

## 3. 🧠 Model Architectures & Parameter Footprint

The neural network backbones implemented in `traintrace/backend/core/models.py`:

| Model Architecture | Parameter Count | File / Memory Size | Primary Characteristics |
| :--- | :--- | :--- | :--- |
| **`CustomCNN`** | **~1.2 Million** | **~4.8 MB** | 3 Conv-BatchNorm-ReLU blocks with max pooling; lightweight baseline |
| **`MobileNetV2`** | **~2.2 Million** | **~8.8 MB** | Inverted residual bottlenecks & depthwise separable convolutions |
| **`EfficientNet-B0`** | **~4.0 Million** | **~16.0 MB** | Compound coefficient scaling balancing depth, width, and resolution |
| **`ResNet-18`** | **~11.2 Million** | **~44.8 MB** | 18-layer residual network with identity skip connections |

---

## 4. ⚙️ Optimization & Hardware Acceleration

* **Loss Function**: `nn.CrossEntropyLoss()` (combines `LogSoftmax` and Negative Log-Likelihood Loss over 10 classes).
* **Default Learning Rate**: `0.001` (1e-3).
* **Weight Decay ($L_2$ Regularization)**: `0.0001` (1e-4) to penalize large weights and prevent overfitting.
* **Momentum**: `0.9` (when using SGD optimizer).
* **Hardware Device**: Automatically selected via `backend/config.py`:
  * **`mps`**: Apple Silicon Metal Performance Shaders GPU (Mac M1/M2/M3/M4)
  * **`cuda`**: NVIDIA GPU
  * **`cpu`**: Multi-threaded CPU fallback
