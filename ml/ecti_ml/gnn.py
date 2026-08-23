from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd
import torch
from torch import nn

from ecti_ml.metrics import BinaryMetrics, evaluate_binary
from ecti_ml.preprocessing import PreparedDataset


class GraphSAGE(nn.Module):
    """Two-layer mean-aggregation GraphSAGE for event-node classification."""

    def __init__(self, input_size: int, hidden_size: int = 32, dropout: float = 0.1) -> None:
        super().__init__()
        self.self_layer_1 = nn.Linear(input_size, hidden_size)
        self.neighbor_layer_1 = nn.Linear(input_size, hidden_size, bias=False)
        self.self_layer_2 = nn.Linear(hidden_size, 1)
        self.neighbor_layer_2 = nn.Linear(hidden_size, 1, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, features: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        neighbor_features = adjacency @ features
        hidden = torch.relu(self.self_layer_1(features) + self.neighbor_layer_1(neighbor_features))
        hidden = self.dropout(hidden)
        neighbor_hidden = adjacency @ hidden
        return (self.self_layer_2(hidden) + self.neighbor_layer_2(neighbor_hidden)).squeeze(1)


@dataclass(frozen=True)
class GNNResult:
    model: GraphSAGE
    validation: BinaryMetrics
    test: BinaryMetrics
    validation_probabilities: np.ndarray
    test_probabilities: np.ndarray
    epochs_trained: int


def build_causal_adjacency(
    frame: pd.DataFrame,
    *,
    timestamp_column: str,
    entity_columns: tuple[str, ...],
    window_minutes: int = 15,
) -> torch.Tensor:
    missing = sorted({timestamp_column, *entity_columns} - set(frame.columns))
    if missing:
        raise ValueError(f"missing graph columns: {', '.join(missing)}")
    ordered = frame.copy()
    ordered[timestamp_column] = pd.to_datetime(ordered[timestamp_column], utc=True, errors="raise")
    ordered = ordered.sort_values(timestamp_column, kind="stable").reset_index(drop=True)
    row_count = len(ordered)
    adjacency = torch.zeros((row_count, row_count), dtype=torch.float32)
    window = pd.Timedelta(minutes=window_minutes)

    for current in range(row_count):
        current_time = ordered.at[current, timestamp_column]
        current_entities = {
            (
                "ip" if column in {"source_ip", "destination_ip"} else column,
                str(ordered.at[current, column]).strip().lower(),
            )
            for column in entity_columns
            if pd.notna(ordered.at[current, column]) and str(ordered.at[current, column]).strip()
        }
        for prior in range(current - 1, -1, -1):
            if current_time - ordered.at[prior, timestamp_column] > window:
                break
            prior_entities = {
                (
                    "ip" if column in {"source_ip", "destination_ip"} else column,
                    str(ordered.at[prior, column]).strip().lower(),
                )
                for column in entity_columns
                if pd.notna(ordered.at[prior, column]) and str(ordered.at[prior, column]).strip()
            }
            if current_entities & prior_entities:
                adjacency[current, prior] = 1.0

    degrees = adjacency.sum(dim=1, keepdim=True).clamp(min=1.0)
    return adjacency / degrees


def _binary_labels(dataset: PreparedDataset, positive_label: str) -> np.ndarray:
    return (
        np.concatenate(
            [
                dataset.train.labels,
                dataset.validation.labels,
                dataset.test.labels,
            ]
        ).astype(str)
        == positive_label
    )


def train_graphsage(
    dataset: PreparedDataset,
    event_frame: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    entity_columns: tuple[str, ...] = ("source_ip", "destination_ip", "user", "host"),
    positive_label: str = "attack",
    window_minutes: int = 15,
    hidden_size: int = 32,
    learning_rate: float = 0.01,
    weight_decay: float = 1e-4,
    max_epochs: int = 200,
    patience: int = 25,
    random_state: int = 42,
    decision_threshold: float = 0.5,
) -> GNNResult:
    features = np.vstack(
        [dataset.train.features, dataset.validation.features, dataset.test.features]
    ).astype(np.float32)
    if len(event_frame) != len(features):
        raise ValueError("event frame and prepared feature rows must have the same length")
    labels = _binary_labels(dataset, positive_label).astype(np.float32)
    train_end = len(dataset.train.labels)
    validation_end = train_end + len(dataset.validation.labels)
    adjacency = build_causal_adjacency(
        event_frame,
        timestamp_column=timestamp_column,
        entity_columns=entity_columns,
        window_minutes=window_minutes,
    )

    torch.manual_seed(random_state)
    feature_tensor = torch.from_numpy(features)
    label_tensor = torch.from_numpy(labels)
    model = GraphSAGE(features.shape[1], hidden_size=hidden_size)
    positives = label_tensor[:train_end].sum().item()
    negatives = train_end - positives
    positive_weight = torch.tensor(negatives / max(positives, 1.0))
    loss_function = nn.BCEWithLogitsLoss(pos_weight=positive_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

    best_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    epochs_trained = 0
    for epoch in range(max_epochs):
        model.train()
        optimizer.zero_grad()
        logits = model(feature_tensor, adjacency)
        loss = loss_function(logits[:train_end], label_tensor[:train_end])
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            validation_logits = model(feature_tensor, adjacency)[train_end:validation_end]
            validation_loss = loss_function(
                validation_logits,
                label_tensor[train_end:validation_end],
            ).item()
        epochs_trained = epoch + 1
        if validation_loss < best_loss - 1e-6:
            best_loss = validation_loss
            best_state = {
                name: parameter.detach().clone() for name, parameter in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        start = perf_counter()
        probabilities = torch.sigmoid(model(feature_tensor, adjacency)).numpy()
        inference_time = (perf_counter() - start) * 1000

    validation_probabilities = probabilities[train_end:validation_end]
    test_probabilities = probabilities[validation_end:]
    validation_labels = labels[train_end:validation_end].astype(int)
    test_labels = labels[validation_end:].astype(int)
    validation_share = len(validation_probabilities) / len(probabilities)
    test_share = len(test_probabilities) / len(probabilities)
    return GNNResult(
        model=model,
        validation=evaluate_binary(
            validation_labels,
            validation_probabilities,
            inference_time_ms=inference_time * validation_share,
            threshold=decision_threshold,
        ),
        test=evaluate_binary(
            test_labels,
            test_probabilities,
            inference_time_ms=inference_time * test_share,
            threshold=decision_threshold,
        ),
        validation_probabilities=validation_probabilities,
        test_probabilities=test_probabilities,
        epochs_trained=epochs_trained,
    )
