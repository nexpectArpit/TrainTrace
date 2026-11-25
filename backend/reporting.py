"""Run artifact renderers: readable evaluation PDF and confusion-matrix PNG."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from storage import record_artifact, run_artifact_path


def render_dataset_preview(run_id, dataset, class_names):
    """Record a deterministic preview from training images only."""
    raw_images = getattr(dataset, "data", None)
    if raw_images is None or len(raw_images) == 0:
        return None
    labels = getattr(dataset, "targets", None)
    if labels is None:
        labels = getattr(dataset, "labels", None)
    count = min(12, len(raw_images))
    canvas = Image.new("RGB", (4 * 124, 3 * 144), "#ffffff")
    draw = ImageDraw.Draw(canvas)
    for index in range(count):
        pixels = np.asarray(raw_images[index])
        if pixels.ndim == 3 and pixels.shape[0] in (1, 3):
            pixels = np.transpose(pixels, (1, 2, 0))
        if pixels.ndim == 3 and pixels.shape[-1] == 1:
            pixels = pixels[..., 0]
        image = Image.fromarray(pixels.astype("uint8")).convert("RGB")
        image = image.resize((112, 112))
        x, y = (index % 4) * 124 + 6, (index // 4) * 144 + 6
        canvas.paste(image, (x, y))
        label_index = int(labels[index]) if labels is not None else -1
        label = (
            str(class_names[label_index]) if 0 <= label_index < len(class_names) else "unlabeled"
        )
        draw.text((x, y + 115), label[:18], fill="#172033")
    path = run_artifact_path(run_id, f"{run_id}_dataset_preview.png", "images")
    canvas.save(path, "PNG", optimize=True)
    record_artifact(run_id, "dataset_preview_png", path)
    return path


def _pdf_escape(value):
    text = str(value).encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_text_pdf(path: Path, lines):
    commands = ["BT", "/F1 10 Tf", "54 790 Td", "14 TL"]
    for line in lines:
        commands.append(f"({_pdf_escape(line)[:110]}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    path.write_bytes(output)


def _render_confusion_matrix(path, matrix, class_names):
    count = len(matrix)
    cell = max(2, min(18, 720 // max(1, count)))
    margin = 90 if count <= 20 else 48
    side = count * cell
    image = Image.new("RGB", (margin + side + 18, margin + side + 60), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text(
        (margin, 12),
        "Confusion matrix: rows = actual, columns = predicted",
        fill="#172033",
        font=font,
    )
    peak = max((max(row) for row in matrix), default=1) or 1
    for row_index, row in enumerate(matrix):
        row_peak = max(row, default=1) or 1
        for col_index, value in enumerate(row):
            intensity = int(220 * value / max(peak, row_peak, 1))
            color = (240 - intensity // 3, 247 - intensity // 4, 255 - intensity // 5)
            x0, y0 = margin + col_index * cell, margin + row_index * cell
            draw.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=color)
    if count <= 20:
        for i, label in enumerate(class_names):
            draw.text((margin + i * cell, margin - 13), str(label)[:7], fill="#344054", font=font)
            draw.text((4, margin + i * cell), str(label)[:10], fill="#344054", font=font)
    else:
        stride = max(1, count // 10)
        for i in range(0, count, stride):
            draw.text((margin + i * cell, margin - 13), str(i), fill="#344054", font=font)
            draw.text((4, margin + i * cell), str(i), fill="#344054", font=font)
    image.save(path, format="PNG", optimize=True)


def render_final_evaluation(run_id, validation, evaluation, class_names):
    image_path = run_artifact_path(run_id, f"{run_id}_confusion_matrix.png", "images")
    _render_confusion_matrix(image_path, evaluation["confusion_matrix"], class_names)
    record_artifact(run_id, "confusion_matrix_png", image_path)
    pdf_path = run_artifact_path(run_id, f"{run_id}_evaluation_report.pdf", "reports")
    lines = [
        "TrainTrace final evaluation report",
        f"Run: {run_id}",
        f"Dataset: {evaluation.get('dataset_name', 'unknown')}",
        f"Validation accuracy: {validation.get('validation_accuracy', float('nan')):.4f}%",
        f"Validation loss: {validation.get('validation_loss', float('nan')):.6f}",
        f"Final test accuracy: {evaluation.get('test_accuracy', float('nan')):.4f}%",
        f"Final test loss: {evaluation.get('test_loss', float('nan')):.6f}",
        f"Macro precision: {evaluation.get('precision_macro', float('nan')):.6f}",
        f"Macro recall: {evaluation.get('recall_macro', float('nan')):.6f}",
        f"Macro F1: {evaluation.get('f1_macro', float('nan')):.6f}",
        f"Samples: {evaluation.get('samples', 0)}",
        f"Checkpoint SHA-256: {evaluation.get('checkpoint_sha256', 'unknown')}",
        f"Model-only p50 latency (ms): {evaluation.get('model_only_latency_ms_p50', float('nan')):.4f}",
        f"Model-only p95 latency (ms): {evaluation.get('model_only_latency_ms_p95', float('nan')):.4f}",
        f"Latency method: {evaluation.get('latency_method', 'not measured')}",
        "See the associated PNG artifact for the rendered confusion matrix.",
    ]
    _write_text_pdf(pdf_path, lines)
    record_artifact(run_id, "evaluation_report_pdf", pdf_path)
    return {"confusion_matrix_image_key": image_path.name, "report_pdf_key": pdf_path.name}
