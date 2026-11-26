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
    """Configurable CIFAR CNN with 2-6 convolutional feature blocks."""

    def __init__(
        self,
        num_classes: int = 10,
        depth: int = 3,
        width: int = 32,
        classifier_width: int = 256,
        dropout: float = 0.3,
    ):
        super().__init__()
        if (
            not 2 <= depth <= 6
            or not 8 <= width <= 128
            or not 16 <= classifier_width <= 2048
            or not 0 <= dropout < 1
        ):
            raise ValueError("Invalid CustomCNN architecture configuration")
        self.legacy_layout = (depth, width, classifier_width, dropout) == (3, 32, 256, 0.3)
        if self.legacy_layout:
            # Keep the original state-dict names and tensor shapes for saved v1 checkpoints.
            self.conv_block1 = nn.Sequential(
                nn.Conv2d(3, 32, 3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
            )
            self.conv_block2 = nn.Sequential(
                nn.Conv2d(32, 64, 3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
            )
            self.conv_block3 = nn.Sequential(
                nn.Conv2d(64, 128, 3, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2, 2),
            )
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(128 * 4 * 4, 256),
                nn.ReLU(inplace=True),
                nn.Dropout(p=0.3),
                nn.Linear(256, num_classes),
            )
            return
        blocks = []
        in_channels = 3
        for index in range(depth):
            out_channels = min(width * (2**index), 256)
            layers = [
                nn.Conv2d(in_channels, out_channels, 3, padding=1),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            ]
            if index < 3:
                layers.append(nn.MaxPool2d(2, stride=2))
            blocks.append(nn.Sequential(*layers))
            in_channels = out_channels
        self.feature_blocks = nn.ModuleList(blocks)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(in_channels, classifier_width),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(classifier_width, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.legacy_layout:
            return self.classifier(self.conv_block3(self.conv_block2(self.conv_block1(x))))
        for block in self.feature_blocks:
            x = block(x)
        return self.classifier(self.pool(x))


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

    def __init__(
        self, num_classes: int = 10, pretrained: bool = False, native_stem: bool | None = None
    ):
        super().__init__()

        # Instantiate base ResNet-18 from torchvision
        weights = torchvision_models.ResNet18_Weights.DEFAULT if pretrained else None
        self.model = torchvision_models.resnet18(weights=weights)

        # Use the native ImageNet stem for pretrained weights. For scratch-trained
        # CIFAR models, retain the small-image stem used by the project baseline.
        if not (pretrained if native_stem is None else native_stem):
            self.model.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
            self.model.maxpool = nn.Identity()

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
def get_model_by_name(
    model_name: str,
    num_classes: int = 10,
    pretrained: bool = False,
    architecture_config: dict | None = None,
    native_stem: bool | None = None,
) -> nn.Module:
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
        return CustomCNN(num_classes=num_classes, **(architecture_config or {}))
    elif name_clean in ["resnet18", "resnet-18"]:
        return ResNet18Wrapper(
            num_classes=num_classes, pretrained=pretrained, native_stem=native_stem
        )
    elif name_clean in ["mobilenet_v2", "mobilenetv2", "mobilenet"]:
        return MobileNetV2Wrapper(num_classes=num_classes, pretrained=pretrained)
    elif name_clean in ["efficientnet_b0", "efficientnetb0", "efficientnet"]:
        return EfficientNetB0Wrapper(num_classes=num_classes, pretrained=pretrained)
    else:
        raise ValueError(
            f"Unknown model architecture '{model_name}'. "
            f"Supported options: ['custom_cnn', 'resnet18', 'mobilenet_v2', 'efficientnet_b0']"
        )
