"""
traintrace/core/dataset.py
==========================
Image dataset ingestion, transformations, and DataLoader factories.

Senior Engineering Rationale:
-----------------------------
1. Encapsulates CIFAR-10/100 downloading, dataset caching, and split management.
2. Separates Training Augmentation transforms from Validation/Test Deterministic transforms.
3. Uses dataset-specific RGB channel statistics (Mean & Standard Deviation):
   - Channel Means: R=0.4914, G=0.4822, B=0.4465
   - Channel Standard Deviations: R=0.2023, G=0.1994, B=0.2010
4. Provides factory function `get_cifar10_dataloaders()` returning ready-to-train PyTorch DataLoaders.
"""

import random
import numpy as np
from typing import Tuple
import torch
from torch.utils.data import DataLoader, random_split
import torchvision
import torchvision.transforms as transforms
from torchvision import datasets as tv_datasets

# Import centralized configuration settings
from config import DATA_DIR, DEFAULT_BATCH_SIZE, DEFAULT_NUM_WORKERS, DEFAULT_RANDOM_SEED


# =============================================================================
# CIFAR DATASET STANDARDIZATION CONSTANTS
# =============================================================================
# Computed empirical per-channel mean and std values for CIFAR-10 RGB images
from core.dataset_contract import dataset_spec, preprocessing_contract


# =============================================================================
# TRANSFORMATION PIPELINES
# =============================================================================
def get_transforms(
    augment: bool = True, dataset_name: str = "cifar10", pretrained: bool = False
) -> transforms.Compose:
    """
    Construct torchvision image transformation pipeline.

    Args:
        augment (bool): If True, includes random spatial data augmentation (for Training).
                        If False, applies only deterministic normalization (for Validation/Test).

    Returns:
        transforms.Compose: Composed PyTorch transformation pipeline.
    """
    contract = preprocessing_contract(dataset_name, pretrained)
    size = contract["size"][0]
    dataset_key, spec = dataset_spec(dataset_name)
    transform_list = []
    if spec.get("grayscale"):
        transform_list.append(transforms.Grayscale(num_output_channels=3))
    transform_list.append(transforms.Resize((size, size)))

    if augment:
        if dataset_key in {"cifar10", "cifar100"}:
            transform_list.extend(
                [transforms.RandomCrop(size, padding=4), transforms.RandomHorizontalFlip(p=0.5)]
            )
        elif dataset_key in {"mnist", "fashion_mnist"}:
            # Horizontal reflection changes digit identity/style. Use small
            # affine variation while keeping the MNIST background black.
            transform_list.append(
                transforms.RandomAffine(
                    degrees=10, translate=(0.08, 0.08), scale=(0.9, 1.1), shear=5, fill=0
                )
            )
        elif dataset_key == "svhn":
            transform_list.append(
                transforms.RandomAffine(
                    degrees=5, translate=(0.05, 0.05), scale=(0.95, 1.05), fill=0
                )
            )

    # Convert PIL Image [0, 255] (uint8) to PyTorch FloatTensor [0.0, 1.0] of shape [C, H, W]
    transform_list.append(transforms.ToTensor())

    # Standardize image tensor channels: norm_pixel = (pixel - mean) / std
    # Moves pixel distributions close to N(0, 1) to stabilize gradient propagation in Conv layers
    transform_list.append(transforms.Normalize(mean=contract["mean"], std=contract["std"]))

    return transforms.Compose(transform_list)


# =============================================================================
# DATALOADER FACTORY FUNCTION
# =============================================================================
def get_dataloaders(
    dataset_name: str = "cifar10",
    batch_size: int = DEFAULT_BATCH_SIZE,
    val_split_ratio: float = 0.1,
    seed: int = DEFAULT_RANDOM_SEED,
    num_workers: int = DEFAULT_NUM_WORKERS,
    data_dir: str = str(DATA_DIR),
    split_seed: int = 42,
    pretrained: bool = False,
    include_test: bool = True,
) -> Tuple[DataLoader, DataLoader, DataLoader | None]:
    """
    Download/load CIFAR-10 or CIFAR-100 and return train/validation/test loaders.

    Args:
        batch_size (int): Number of image samples per mini-batch.
        val_split_ratio (float): Fraction of training set reserved for validation (default: 0.1 = 5,000 samples).
        seed (int): Random seed for reproducible random_split indexing.
        num_workers (int): Number of parallel CPU subprocesses for data loading.
        data_dir (str): Root directory path for dataset storage and caching.

    Returns:
        Tuple[DataLoader, DataLoader, DataLoader]: (train_loader, val_loader, test_loader)
    """
    # Create transformation pipelines
    dataset_key, spec = dataset_spec(dataset_name)
    dataset_class = getattr(torchvision.datasets, spec["torchvision_name"])
    train_transform = get_transforms(augment=True, dataset_name=dataset_key, pretrained=pretrained)
    eval_transform = get_transforms(augment=False, dataset_name=dataset_key, pretrained=pretrained)

    # Download / load raw 50,000 training images using training transformations
    if dataset_key == "svhn":
        full_train_dataset = dataset_class(
            root=data_dir, split="train", download=True, transform=train_transform
        )
    else:
        full_train_dataset = dataset_class(
            root=data_dir, train=True, download=True, transform=train_transform
        )

    # Download / load raw 10,000 holdout test images using evaluation transformations
    if include_test:
        test_dataset = (
            dataset_class(root=data_dir, split="test", download=True, transform=eval_transform)
            if dataset_key == "svhn"
            else dataset_class(root=data_dir, train=False, download=True, transform=eval_transform)
        )
    else:
        test_dataset = None

    # Compute split counts (e.g. 45,000 Train / 5,000 Validation)
    num_full_train = len(full_train_dataset)  # 50,000
    num_val = int(num_full_train * val_split_ratio)  # 5,000
    num_train = num_full_train - num_val  # 45,000

    # Use fixed PyTorch Generator seed to ensure deterministic train/val partition across runs
    generator = torch.Generator().manual_seed(split_seed)
    train_dataset, val_dataset_raw = random_split(
        full_train_dataset, [num_train, num_val], generator=generator
    )

    # Senior Note: Ensure validation subset uses non-augmented evaluation transform
    # random_split inherits train_transform from full_train_dataset. We override validation dataset transform.
    # Re-open the selected dataset with deterministic transforms for validation:
    val_dataset_eval = (
        dataset_class(root=data_dir, split="train", download=False, transform=eval_transform)
        if dataset_key == "svhn"
        else dataset_class(root=data_dir, train=True, download=False, transform=eval_transform)
    )
    # Subset wrapping the validation indices with deterministic transform
    val_dataset = torch.utils.data.Subset(val_dataset_eval, val_dataset_raw.indices)

    # Construct PyTorch DataLoader instances
    # Train DataLoader: shuffle=True to prevent network learning sequence bias
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
        worker_init_fn=seed_worker,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),  # Pin memory for faster GPU transfer if CUDA active
    )

    # Validation DataLoader: shuffle=False for deterministic evaluation metric comparisons
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    # Test DataLoader: Holdout evaluation dataset
    test_loader = (
        DataLoader(
            test_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=torch.cuda.is_available(),
        )
        if test_dataset is not None
        else None
    )

    return train_loader, val_loader, test_loader


def get_test_dataloader(
    dataset_name: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    data_dir: str = str(DATA_DIR),
    pretrained: bool = False,
) -> DataLoader:
    """Load only the final-test partition; training/selection code never receives it."""
    dataset_key, spec = dataset_spec(dataset_name)
    cls = getattr(tv_datasets, spec["torchvision_name"])
    transform = get_transforms(augment=False, dataset_name=dataset_key, pretrained=pretrained)
    dataset = (
        cls(root=data_dir, split="test", download=True, transform=transform)
        if dataset_key == "svhn"
        else cls(root=data_dir, train=False, download=True, transform=transform)
    )
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )


def get_cifar10_dataloaders(
    batch_size=DEFAULT_BATCH_SIZE,
    val_split_ratio=0.1,
    seed=DEFAULT_RANDOM_SEED,
    num_workers=DEFAULT_NUM_WORKERS,
    data_dir=str(DATA_DIR),
    split_seed=42,
    pretrained=False,
    include_test=True,
):
    """Backward-compatible CIFAR-10 loader entry point."""
    return get_dataloaders(
        "cifar10",
        batch_size,
        val_split_ratio,
        seed,
        num_workers,
        data_dir,
        split_seed,
        pretrained,
        include_test,
    )


def seed_worker(worker_id):
    seed = torch.initial_seed() % 2**32
    random.seed(seed)
    np.random.seed(seed)
