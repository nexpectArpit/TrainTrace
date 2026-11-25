"""Prevent plausible-looking predictions from incomplete dataset records."""

import pytest
from PIL import Image

from core.preprocessing import prepare_external_image
from services.inference_provenance import require_inference_dataset


def test_inference_requires_recorded_classes_and_upload_adapter():
    dataset = {
        "dataset_name": "mnist",
        "name": "MNIST",
        "num_classes": 10,
        "classes": [str(index) for index in range(10)],
        "preprocessing": {
            "size": [32, 32],
            "mean": [0.1307] * 3,
            "std": [0.3081] * 3,
            "input_conversion": "grayscale_to_rgb",
            "external_input_adapter": "digit_photo_ink_v2",
        },
    }
    assert require_inference_dataset(dataset)[0] == "mnist"
    with pytest.raises(ValueError, match="class names"):
        require_inference_dataset({**dataset, "classes": None})
    missing_adapter = {**dataset["preprocessing"]}
    missing_adapter.pop("external_input_adapter")
    with pytest.raises(ValueError, match="upload adapter"):
        require_inference_dataset({**dataset, "preprocessing": missing_adapter})
    with pytest.raises(ValueError, match="adapter is missing"):
        prepare_external_image(Image.new("RGB", (32, 32)), missing_adapter)
