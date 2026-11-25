if RUN_FINAL_TEST:
    test_data = make_dataset(False, make_transform(False))
    test_loader = DataLoader(
        test_data,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    saved = torch.load(best_path, map_location=DEVICE, weights_only=False)
    model.load_state_dict(saved["model_state_dict"])
    test_loss, test_acc = evaluate(model, test_loader, criterion)
    print(f"Holdout test: loss={test_loss:.4f}, accuracy={test_acc:.2f}%")
else:
    print("Holdout test not run. Set RUN_FINAL_TEST=True when ready.")
