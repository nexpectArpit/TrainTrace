"""Dataset identities and preprocessing contract shared by local and Kaggle runs."""

CIFAR10_MEAN = [0.4914, 0.4822, 0.4465]
CIFAR10_STD = [0.2023, 0.1994, 0.2010]
CIFAR100_MEAN = [0.5071, 0.4867, 0.4408]
CIFAR100_STD = [0.2675, 0.2565, 0.2761]
DATASET_SPECS = {
    "cifar10": {
        "name": "CIFAR-10",
        "torchvision_name": "CIFAR10",
        "mean": CIFAR10_MEAN,
        "std": CIFAR10_STD,
        "num_classes": 10,
        "source_dir": "cifar-10-batches-py",
    },
    "cifar100": {
        "name": "CIFAR-100",
        "torchvision_name": "CIFAR100",
        "mean": CIFAR100_MEAN,
        "std": CIFAR100_STD,
        "num_classes": 100,
        "source_dir": "cifar-100-python",
    },
    "mnist": {
        "name": "MNIST",
        "torchvision_name": "MNIST",
        "mean": [0.1307] * 3,
        "std": [0.3081] * 3,
        "num_classes": 10,
        "source_dir": "MNIST/raw",
        "classes": [str(i) for i in range(10)],
        "grayscale": True,
    },
    "fashion_mnist": {
        "name": "Fashion-MNIST",
        "torchvision_name": "FashionMNIST",
        "mean": [0.2860] * 3,
        "std": [0.3530] * 3,
        "num_classes": 10,
        "source_dir": "FashionMNIST/raw",
        "classes": [
            "T-shirt/top",
            "Trouser",
            "Pullover",
            "Dress",
            "Coat",
            "Sandal",
            "Shirt",
            "Sneaker",
            "Bag",
            "Ankle boot",
        ],
        "grayscale": True,
    },
    "svhn": {
        "name": "SVHN",
        "torchvision_name": "SVHN",
        "mean": [0.4377, 0.4438, 0.4728],
        "std": [0.1980, 0.2010, 0.1970],
        "num_classes": 10,
        "source_dir": "SVHN",
        "classes": [str(i) for i in range(10)],
        "grayscale": False,
    },
}


def preprocessing_contract(dataset_name="cifar10", pretrained=False, model_name=None):
    """Single source of truth for native training and external image inputs."""
    key, spec = dataset_spec(dataset_name)
    size = 224 if pretrained else 32
    return {
        "schema_version": 3,
        "dataset_name": key,
        "size": [size, size],
        "mean": [0.485, 0.456, 0.406] if pretrained else list(spec["mean"]),
        "std": [0.229, 0.224, 0.225] if pretrained else list(spec["std"]),
        "input_conversion": "grayscale_to_rgb" if spec.get("grayscale") else "rgb",
        "external_input_adapter": "digit_photo_ink_v2"
        if key in {"mnist", "fashion_mnist"}
        else "aspect_fit_mean_pad",
        "pretrained_imagenet_normalization": bool(pretrained),
        "initialization": (
            f"torchvision {model_name} ImageNet DEFAULT weights; native pretrained stem preserved"
            if pretrained and model_name
            else "random initialization"
        ),
    }


def dataset_spec(dataset_name="cifar10"):
    key = dataset_name.lower().replace("-", "_")
    key = {"cifar_10": "cifar10", "cifar_100": "cifar100"}.get(key, key)
    if key == "fashionmnist":
        key = "fashion_mnist"
    if key not in DATASET_SPECS:
        raise ValueError(f"Unsupported dataset: {dataset_name}")
    return key, DATASET_SPECS[key]
