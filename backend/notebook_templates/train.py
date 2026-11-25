def build_model():
    return get_model_by_name(
        CONFIG["model_name"],
        num_classes=DATASET["classes"],
        pretrained=CONFIG["pretrained"],
        architecture_config=CONFIG["architecture_config"] or None,
    ).to(DEVICE)


def evaluate(model, loader, criterion):
    model.eval()
    total = correct = 0
    loss_sum = 0.0
    with torch.inference_mode():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            logits = model(x)
            loss = criterion(logits, y)
            total += y.size(0)
            correct += (logits.argmax(1) == y).sum().item()
            loss_sum += loss.item() * y.size(0)
    return loss_sum / total, 100 * correct / total


model = build_model()
criterion = nn.CrossEntropyLoss()
opt_name = CONFIG["optimizer"].lower()
optimizer_class = {"adamw": torch.optim.AdamW, "sgd": torch.optim.SGD}[opt_name]
optimizer = optimizer_class(
    model.parameters(),
    lr=CONFIG["learning_rate"],
    weight_decay=CONFIG["weight_decay"],
    **({"momentum": 0.9} if opt_name == "sgd" else {}),
)
if CONFIG["scheduler_type"] == "cosine":
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=CONFIG["epochs"])
elif CONFIG["scheduler_type"] == "step":
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)
elif CONFIG["scheduler_type"] == "constant":
    scheduler = None
else:
    raise ValueError("Unsupported saved scheduler")
history = []
best_val = -1.0
best_path = OUTPUT_DIR / "best_model.pt"
for epoch in range(1, CONFIG["epochs"] + 1):
    start = time.perf_counter()
    model.train()
    total = correct = 0
    loss_sum = 0.0
    for x, y in train_loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total += y.size(0)
        correct += (logits.argmax(1) == y).sum().item()
        loss_sum += loss.item() * y.size(0)
    train_loss = loss_sum / total
    train_acc = 100 * correct / total
    val_loss, val_acc = evaluate(model, val_loader, criterion)
    learning_rate = optimizer.param_groups[0]["lr"]
    if scheduler:
        scheduler.step()
    row = {
        "epoch": epoch,
        "train_loss": train_loss,
        "train_acc": train_acc,
        "val_loss": val_loss,
        "val_acc": val_acc,
        "epoch_time_sec": time.perf_counter() - start,
        "learning_rate": learning_rate,
    }
    history.append(row)
    pd.DataFrame(history).to_csv(OUTPUT_DIR / "metrics.csv", index=False)
    if val_acc > best_val:
        best_val = val_acc
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "config": CONFIG,
                "epoch": epoch,
                "val_accuracy": val_acc,
            },
            best_path,
        )
    print(
        f"Epoch {epoch:>3}/{CONFIG['epochs']} | train loss {train_loss:.4f} acc {train_acc:.2f}% | val loss {val_loss:.4f} acc {val_acc:.2f}% | {row['epoch_time_sec']:.1f}s"
    )

metrics = pd.DataFrame(history)
display(metrics)
print("Best validation accuracy:", round(best_val, 2), "% | checkpoint:", best_path)
