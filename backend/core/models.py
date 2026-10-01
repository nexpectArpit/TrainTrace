"""
traintrace/core/models.py
=========================
Model Architecture Definitions for TrainTrace.

Senior Engineering Rationale:
-----------------------------
1. Implements 4 distinct neural network architectures to support our experiment investigations:
   - Approach 1: CustomCNN (Baseline 3-layer Convolutional Network)
   - Approach 2: ResNet18 (Deep Residual Network with Skip Connections)
   - Approach 3: MobileNetV2 (Lightweight Depthwise Separable Architecture)
   - Approach 4: EfficientNet-B0 (Compound Scaled Convolutional Network)
2. Every architecture subclass inherits from `torch.nn.Module` and implements `forward()`.
3. Every block includes line-by-line comments explaining tensor dimensions (Channels, Height, Width).
"""

import torch
import torch.nn as nn
import torchvision.models as torchvision_models


# =============================================================================
# APPROACH 1: CUSTOM 3-LAYER CNN (Baseline Architecture)
# =============================================================================
class CustomCNN(nn.Module):
    """
    A lightweight 3-block Convolutional Neural Network built for 32x32 CIFAR-10 images.
    
    Tensor Dimensional Trajectory:
    - Input Image Batch: [Batch_Size, 3, 32, 32]
    - Block 1 (Conv -> BN -> ReLU -> Pool): [Batch_Size, 32, 16, 16]
    - Block 2 (Conv -> BN -> ReLU -> Pool): [Batch_Size, 64, 8, 8]
    - Block 3 (Conv -> BN -> ReLU -> Pool): [Batch_Size, 128, 4, 4]
    - Flatten: [Batch_Size, 128 * 4 * 4] = [Batch_Size, 2048]
    - Classifier (Linear -> Dropout -> Linear): [Batch_Size, num_classes]
    """
    def __init__(self, num_classes: int = 10):
        # Always call super().__init__() to register PyTorch module parameters correctly
        super().__init__()
        
        # Block 1: Extracts low-level visual features (edges, color gradients)
        # in_channels=3 (RGB), out_channels=32 (number of 3x3 filters)
        # padding=1 ensures spatial dimensions stay 32x32 before pooling
        self.conv_block1 = nn.Sequential(
            nn.Conv2d(in_channels=3, out_channels=32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),  # Normalizes activations across batch to stabilize training
            nn.ReLU(inplace=True),  # Non-linear activation function
            nn.MaxPool2d(kernel_size=2, stride=2)  # Downsamples spatial grid from 32x32 -> 16x16
        )
        
        # Block 2: Extracts mid-level visual features (textures, simple patterns)
        # in_channels=32, out_channels=64
        self.conv_block2 = nn.Sequential(
            nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2)  # Downsamples spatial grid from 16x16 -> 8x8
        )
        
        # Block 3: Extracts high-level semantic features (object parts)
        # in_channels=64, out_channels=128
        self.conv_block3 = nn.Sequential(
            nn.Conv2d(in_channels=64, out_channels=128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2)  # Downsamples spatial grid from 8x8 -> 4x4
        )
        
        # Fully Connected Classification Head
        # Converts 2D spatial feature maps into class logits vector
        self.classifier = nn.Sequential(
            nn.Flatten(),  # Flattens 3D tensor [128, 4, 4] into 1D vector of length 2048
            nn.Linear(128 * 4 * 4, 256),  # First dense projection layer
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),  # Randomly zeroes 30% of units during training to prevent overfitting
            nn.Linear(256, num_classes)  # Final projection to 10 class logits (unnormalized scores)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Executes the forward pass computation graph.
        
        Args:
            x (torch.Tensor): Input batch of shape [B, 3, 32, 32]
            
        Returns:
            torch.Tensor: Raw output class logits of shape [B, num_classes]
        """
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        x = self.conv_block3(x)
        logits = self.classifier(x)
        return logits


# =============================================================================
# APPROACH 2: RESNET-18 (Residual Network Wrapper)
# =============================================================================
class ResNet18Wrapper(nn.Module):
    """
    ResNet-18 residual architecture adapted for CIFAR-10.
    
    Senior Engineering Note:
    Standard ImageNet ResNet-18 has a large 7x7 conv kernel with stride 2 designed for 224x224 images.
    For 32x32 CIFAR-10, we modify initial conv layer to 3x3 with stride 1 so small features are not lost.
    """
    def __init__(self, num_classes: int = 10, pretrained: bool = False):
        super().__init__()
        
        # Instantiate base ResNet-18 from torchvision
        weights = torchvision_models.ResNet18_Weights.DEFAULT if pretrained else None
        self.model = torchvision_models.resnet18(weights=weights)
        
        # Modify initial convolution to preserve 32x32 input resolution without aggressive downsampling
        self.model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.model.maxpool = nn.Identity()  # Remove initial aggressive 3x3 max pooling for small images
        
        # Replace final fully connected classification layer to output num_classes logits
        in_features = self.model.fc.in_features  # 512 for ResNet-18
        self.model.fc = nn.Linear(in_features, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


# =============================================================================
# APPROACH 3: MOBILENET-V2 (Lightweight Architecture)
# =============================================================================
class MobileNetV2Wrapper(nn.Module):
    """
    MobileNetV2 lightweight architecture using Depthwise Separable Convolutions.
    Efficient for low-latency edge deployment.
    """
    def __init__(self, num_classes: int = 10, pretrained: bool = False):
        super().__init__()
        weights = torchvision_models.MobileNet_V2_Weights.DEFAULT if pretrained else None
        self.model = torchvision_models.mobilenet_v2(weights=weights)
        
        # Replace classifier head for target num_classes
        in_features = self.model.classifier[1].in_features  # 1280 for MobileNetV2
        self.model.classifier[1] = nn.Linear(in_features, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


# =============================================================================
# APPROACH 4: EFFICIENTNET-B0 (Compound Scaling Architecture)
# =============================================================================
class EfficientNetB0Wrapper(nn.Module):
    """
    EfficientNet-B0 compound scaling architecture balancing depth, width, and resolution.
    """
    def __init__(self, num_classes: int = 10, pretrained: bool = False):
        super().__init__()
        weights = torchvision_models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        self.model = torchvision_models.efficientnet_b0(weights=weights)
        
        # Replace final classifier layer
        in_features = self.model.classifier[1].in_features  # 1280 for EfficientNet-B0
        self.model.classifier[1] = nn.Linear(in_features, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


# =============================================================================
# FACTORY HELPER FUNCTION
# =============================================================================
def get_model_by_name(model_name: str, num_classes: int = 10, pretrained: bool = False) -> nn.Module:
    """
    Factory function to instantiate model architectures cleanly by name.
    
    Args:
        model_name (str): Identifier name ('custom_cnn', 'resnet18', 'mobilenet_v2', 'efficientnet_b0')
        num_classes (int): Number of output target classes (default: 10 for CIFAR-10)
        pretrained (bool): Whether to load pre-trained ImageNet weights
        
    Returns:
        nn.Module: Instantiated PyTorch neural network model.
    """
    name_clean = model_name.lower().strip()
    
    if name_clean in ["custom_cnn", "customcnn", "baseline"]:
        return CustomCNN(num_classes=num_classes)
    elif name_clean in ["resnet18", "resnet-18"]:
        return ResNet18Wrapper(num_classes=num_classes, pretrained=pretrained)
    elif name_clean in ["mobilenet_v2", "mobilenetv2", "mobilenet"]:
        return MobileNetV2Wrapper(num_classes=num_classes, pretrained=pretrained)
    elif name_clean in ["efficientnet_b0", "efficientnetb0", "efficientnet"]:
        return EfficientNetB0Wrapper(num_classes=num_classes, pretrained=pretrained)
    else:
        raise ValueError(
            f"Unknown model architecture '{model_name}'. "
            f"Supported options: ['custom_cnn', 'resnet18', 'mobilenet_v2', 'efficientnet_b0']"
        )
