from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json

from common import ArtifactPaths, load_manifest, require_package


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Train a galaxy encoder for the Galaxy Embedding Map.")
    parser.add_argument("--manifest", type=Path, required=True, help="CSV/JSON/Parquet with image_id,image_path[,label]")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory where model artifacts will be stored")
    parser.add_argument("--objective", choices=["simclr", "supervised"], default="simclr")
    parser.add_argument("--backbone", choices=["resnet50", "vit_b_16"], default="resnet50")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--embedding-dim", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--device", default="cuda")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    torch = require_package("torch")
    torch.nn  # pragma: no cover - import side effect for lint clarity
    torchvision = require_package("torchvision")
    require_package("PIL", "pillow")

    frame = load_manifest(args.manifest)
    artifacts = ArtifactPaths(args.output_dir)
    artifacts.ensure()

    label_to_index: dict[str, int] = {}
    if args.objective == "supervised":
        if "label" not in frame.columns:
            raise SystemExit("Supervised training requires a 'label' column in the manifest.")
        label_to_index = {label: index for index, label in enumerate(sorted(frame["label"].astype(str).unique()))}
        frame = frame.assign(label_index=frame["label"].astype(str).map(label_to_index))

    transforms = torchvision.transforms
    base_transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    aug_transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomResizedCrop(args.image_size, scale=(0.65, 1.0)),
            transforms.ColorJitter(0.18, 0.18, 0.18, 0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    Image = require_package("PIL.Image", "pillow")
    Dataset = torch.utils.data.Dataset

    class GalaxyDataset(Dataset):
        def __init__(self, objective: str):
            self.objective = objective

        def __len__(self):
            return len(frame)

        def __getitem__(self, index: int):
            row = frame.iloc[index]
            image = Image.open(row["image_path"]).convert("RGB")
            if self.objective == "simclr":
                return aug_transform(image), aug_transform(image)
            return base_transform(image), int(row["label_index"])

    def build_backbone():
        if args.backbone == "resnet50":
            model = torchvision.models.resnet50(weights=None)
            in_features = model.fc.in_features
            model.fc = torch.nn.Identity()
            return model, in_features
        model = torchvision.models.vit_b_16(weights=None)
        in_features = model.heads.head.in_features
        model.heads.head = torch.nn.Identity()
        return model, in_features

    class ContrastiveModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder, hidden_dim = build_backbone()
            self.projector = torch.nn.Sequential(
                torch.nn.Linear(hidden_dim, hidden_dim),
                torch.nn.GELU(),
                torch.nn.Linear(hidden_dim, args.embedding_dim),
            )

        def forward(self, inputs):
            features = self.encoder(inputs)
            return torch.nn.functional.normalize(self.projector(features), dim=1)

    class SupervisedModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder, hidden_dim = build_backbone()
            self.embedding_head = torch.nn.Linear(hidden_dim, args.embedding_dim)
            self.classifier = torch.nn.Linear(args.embedding_dim, len(label_to_index))

        def forward(self, inputs):
            features = self.encoder(inputs)
            embedding = torch.nn.functional.normalize(self.embedding_head(features), dim=1)
            logits = self.classifier(embedding)
            return embedding, logits

    def nt_xent_loss(z_a, z_b, temperature: float = 0.2):
        batch_size = z_a.shape[0]
        logits = (z_a @ z_b.T) / temperature
        labels = torch.arange(batch_size, device=logits.device)
        loss_ab = torch.nn.functional.cross_entropy(logits, labels)
        loss_ba = torch.nn.functional.cross_entropy(logits.T, labels)
        return (loss_ab + loss_ba) / 2

    dataset = GalaxyDataset(args.objective)
    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
    )

    device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
    model = ContrastiveModel() if args.objective == "simclr" else SupervisedModel()
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)

    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        for batch in loader:
            optimizer.zero_grad(set_to_none=True)
            if args.objective == "simclr":
                view_a, view_b = (tensor.to(device) for tensor in batch)
                z_a = model(view_a)
                z_b = model(view_b)
                loss = nt_xent_loss(z_a, z_b)
            else:
                images, labels = batch
                images = images.to(device)
                labels = labels.to(device)
                _, logits = model(images)
                loss = torch.nn.functional.cross_entropy(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())
        print(f"epoch={epoch + 1} loss={running_loss / max(1, len(loader)):.4f}")

    encoder_module = model.encoder
    torch.save(
        {
            "encoder_state_dict": encoder_module.state_dict(),
            "objective": args.objective,
            "backbone": args.backbone,
            "embedding_dim": args.embedding_dim,
            "image_size": args.image_size,
            "labels": label_to_index,
        },
        artifacts.checkpoint_path,
    )
    artifacts.config_path.write_text(
        json.dumps(
            {
                "objective": args.objective,
                "backbone": args.backbone,
                "embedding_dim": args.embedding_dim,
                "image_size": args.image_size,
                "manifest": str(args.manifest),
                "labels": label_to_index,
            },
            indent=2,
        )
    )
    print(f"saved encoder checkpoint to {artifacts.checkpoint_path}")


if __name__ == "__main__":
    main()
