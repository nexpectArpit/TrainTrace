"""Portable notebook cell: dataset loading and split preparation."""

dataset_key, DATASET_SPEC = dataset_spec(CONFIG["dataset_name"])
PREPROCESSING = preprocessing_contract(dataset_key, CONFIG["pretrained"], CONFIG["model_name"])


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    random.seed(worker_seed)
    np.random.seed(worker_seed)


def make_transform(train):
    size = PREPROCESSING["size"][0]
    operations = []
    if DATASET_SPEC.get("grayscale"):
        operations.append(transforms.Grayscale(num_output_channels=3))
    operations.append(transforms.Resize((size, size)))
    if train:
        if dataset_key in {"cifar10", "cifar100"}:
            operations.extend(
                [
                    transforms.RandomCrop(size, padding=4),
                    transforms.RandomHorizontalFlip(p=0.5),
                ]
            )
        elif dataset_key in {"mnist", "fashion_mnist"}:
            operations.append(
                transforms.RandomAffine(
                    degrees=10,
                    translate=(0.08, 0.08),
                    scale=(0.9, 1.1),
                    shear=5,
                    fill=0,
                )
            )
        elif dataset_key == "svhn":
            operations.append(
                transforms.RandomAffine(
                    degrees=5,
                    translate=(0.05, 0.05),
                    scale=(0.95, 1.05),
                    fill=0,
                )
            )
    operations.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(PREPROCESSING["mean"], PREPROCESSING["std"]),
        ]
    )
    return transforms.Compose(operations)


def make_dataset(train, transform):
    dataset_class = getattr(datasets, DATASET_SPEC["torchvision_name"])
    if dataset_key == "svhn":
        return dataset_class(
            root=str(DATA_DIR),
            split="train" if train else "test",
            download=True,
            transform=transform,
        )
    return dataset_class(root=str(DATA_DIR), train=train, download=True, transform=transform)


seed_everything(CONFIG["seed"])
raw_train = make_dataset(True, make_transform(True))
val_raw = make_dataset(True, make_transform(False))
val_count = int(len(raw_train) * 0.1)
train_subset, val_subset = random_split(
    raw_train,
    [len(raw_train) - val_count, val_count],
    generator=torch.Generator().manual_seed(CONFIG["split_seed"]),
)
train_loader = DataLoader(
    train_subset,
    batch_size=CONFIG["batch_size"],
    shuffle=True,
    generator=torch.Generator().manual_seed(CONFIG["seed"]),
    worker_init_fn=seed_worker,
    num_workers=0,
    pin_memory=torch.cuda.is_available(),
)
val_loader = DataLoader(
    Subset(val_raw, val_subset.indices),
    batch_size=CONFIG["batch_size"],
    shuffle=False,
    num_workers=0,
    pin_memory=torch.cuda.is_available(),
)
print(f"Train: {len(train_subset):,} | validation: {val_count:,} | classes: {DATASET['classes']}")
print("Preprocessing:", json.dumps(PREPROCESSING, indent=2))
