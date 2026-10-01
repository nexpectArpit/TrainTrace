"""
traintrace/core/dataset.py
==========================
CIFAR-10 Data Ingestion, Image Transformations & DataLoader Factory Module.

Senior Engineering Rationale:
-----------------------------
1. Encapsulates CIFAR-10 data downloading, dataset caching, and split management.
2. Separates Training Augmentation transforms from Validation/Test Deterministic transforms.
3. Uses CIFAR-10 dataset RGB channel statistics (Mean & Standard Deviation) for standardization:
   - Channel Means: R=0.4914, G=0.4822, B=0.4465
   - Channel Standard Deviations: R=0.2023, G=0.1994, B=0.2010
4. Provides factory function `get_cifar10_dataloaders()` returning ready-to-train PyTorch DataLoaders.
"""

import os
from typing import Tuple
import torch
from torch.utils.data import DataLoader, random_split
import torchvision
import torchvision.transforms as transforms

# Import centralized configuration settings
from config import DATA_DIR, DEFAULT_BATCH_SIZE, DEFAULT_NUM_WORKERS, DEFAULT_RANDOM_SEED


# =============================================================================
# CIFAR-10 STANDARDIZATION CONSTANTS
# =============================================================================
# Computed empirical per-channel mean and std values for CIFAR-10 RGB images
CIFAR10_MEAN = [0.4914, 0.4822, 0.4465]
CIFAR10_STD = [0.2023, 0.1994, 0.2010]


# =============================================================================
# TRANSFORMATION PIPELINES
# =============================================================================
def get_transforms(augment: bool = True) -> transforms.Compose:
    """
    Construct torchvision image transformation pipeline.
    
    Args:
        augment (bool): If True, includes random spatial data augmentation (for Training).
                        If False, applies only deterministic normalization (for Validation/Test).
                        
    Returns:
        transforms.Compose: Composed PyTorch transformation pipeline.
    """
    transform_list = []
    
    if augment:
        # Data Augmentation 1: Random cropping with 4-pixel padding to make network shift-invariant
        transform_list.append(transforms.RandomCrop(32, padding=4))
        # Data Augmentation 2: Random horizontal flip with 50% probability
        transform_list.append(transforms.RandomHorizontalFlip(p=0.5))
        
    # Convert PIL Image [0, 255] (uint8) to PyTorch FloatTensor [0.0, 1.0] of shape [C, H, W]
    transform_list.append(transforms.ToTensor())
    
    # Standardize image tensor channels: norm_pixel = (pixel - mean) / std
    # Moves pixel distributions close to N(0, 1) to stabilize gradient propagation in Conv layers
    transform_list.append(transforms.Normalize(mean=CIFAR10_MEAN, std=CIFAR10_STD))
    
    return transforms.Compose(transform_list)


# =============================================================================
# DATALOADER FACTORY FUNCTION
# =============================================================================
def get_cifar10_dataloaders(
    batch_size: int = DEFAULT_BATCH_SIZE,
    val_split_ratio: float = 0.1,
    seed: int = DEFAULT_RANDOM_SEED,
    num_workers: int = DEFAULT_NUM_WORKERS,
    data_dir: str = str(DATA_DIR)
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Download/load CIFAR-10 dataset and return PyTorch DataLoaders for Train, Val, and Test splits.
    
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
    train_transform = get_transforms(augment=True)
    eval_transform = get_transforms(augment=False)
    
    # Download / load raw 50,000 training images using training transformations
    full_train_dataset = torchvision.datasets.CIFAR10(
        root=data_dir,
        train=True,
        download=True,
        transform=train_transform
    )
    
    # Download / load raw 10,000 holdout test images using evaluation transformations
    test_dataset = torchvision.datasets.CIFAR10(
        root=data_dir,
        train=False,
        download=True,
        transform=eval_transform
    )
    
    # Compute split counts (e.g. 45,000 Train / 5,000 Validation)
    num_full_train = len(full_train_dataset)  # 50,000
    num_val = int(num_full_train * val_split_ratio)  # 5,000
    num_train = num_full_train - num_val  # 45,000
    
    # Use fixed PyTorch Generator seed to ensure deterministic train/val partition across runs
    generator = torch.Generator().manual_seed(seed)
    train_dataset, val_dataset_raw = random_split(
        full_train_dataset,
        [num_train, num_val],
        generator=generator
    )
    
    # Senior Note: Ensure validation subset uses non-augmented evaluation transform
    # random_split inherits train_transform from full_train_dataset. We override validation dataset transform.
    # We construct a non-augmented CIFAR-10 instance for validation split evaluation:
    val_dataset_eval = torchvision.datasets.CIFAR10(
        root=data_dir,
        train=True,
        download=False,
        transform=eval_transform
    )
    # Subset wrapping the validation indices with deterministic transform
    val_dataset = torch.utils.data.Subset(val_dataset_eval, val_dataset_raw.indices)
    
    # Construct PyTorch DataLoader instances
    # Train DataLoader: shuffle=True to prevent network learning sequence bias
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()  # Pin memory for faster GPU transfer if CUDA active
    )
    
    # Validation DataLoader: shuffle=False for deterministic evaluation metric comparisons
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    
    # Test DataLoader: Holdout evaluation dataset
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    
    return train_loader, val_loader, test_loader
