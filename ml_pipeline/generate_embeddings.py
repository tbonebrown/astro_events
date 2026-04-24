from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json

import pandas as pd

from common import ArtifactPaths, load_manifest, require_package


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate galaxy embeddings from a trained encoder.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=96)
    parser.add_argument("--device", default="cuda")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    torch = require_package("torch")
    torchvision = require_package("torchvision")
    require_package("PIL", "pillow")

    frame = load_manifest(args.manifest)
    artifacts = ArtifactPaths(args.model_dir)
    checkpoint = torch.load(artifacts.checkpoint_path, map_location="cpu")
    config = json.loads(artifacts.config_path.read_text())
    image_size = int(config["image_size"])

    transforms = torchvision.transforms.Compose(
        [
            torchvision.transforms.Resize((image_size, image_size)),
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    Image = require_package("PIL.Image", "pillow")
    Dataset = torch.utils.data.Dataset

    class GalaxyDataset(Dataset):
        def __len__(self):
            return len(frame)

        def __getitem__(self, index: int):
            row = frame.iloc[index]
            image = Image.open(row["image_path"]).convert("RGB")
            return transforms(image), row.to_dict()

    def build_encoder():
        backbone = checkpoint["backbone"]
        if backbone == "resnet50":
            model = torchvision.models.resnet50(weights=None)
            model.fc = torch.nn.Identity()
            return model
        model = torchvision.models.vit_b_16(weights=None)
        model.heads.head = torch.nn.Identity()
        return model

    loader = torch.utils.data.DataLoader(
        GalaxyDataset(),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=lambda batch: (
            torch.stack([item[0] for item in batch]),
            [item[1] for item in batch],
        ),
    )
    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    encoder = build_encoder()
    encoder.load_state_dict(checkpoint["encoder_state_dict"])
    encoder.to(device)
    encoder.eval()

    rows: list[dict] = []
    with torch.inference_mode():
        for images, metadata_rows in loader:
            features = encoder(images.to(device)).detach().cpu().numpy()
            for feature_vector, metadata in zip(features, metadata_rows, strict=False):
                row = dict(metadata)
                row["predicted_class"] = str(
                    metadata.get("label")
                    or metadata.get("morphology")
                    or metadata.get("class_label")
                    or "unlabeled galaxy"
                )
                row["morphology"] = str(metadata.get("morphology") or row["predicted_class"])
                for index, value in enumerate(feature_vector):
                    row[f"emb_{index}"] = float(value)
                rows.append(row)

    output = pd.DataFrame(rows)
    output.to_parquet(artifacts.embeddings_path, index=False)
    print(f"wrote embeddings to {artifacts.embeddings_path}")


if __name__ == "__main__":
    main()
