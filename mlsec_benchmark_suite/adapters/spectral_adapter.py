"""Adapter connecting dataset-poisoning-detector's spectral method to mlsec-benchmark-suite.

Generates synthetic poisoned data (2 Gaussian clusters with 5% label flips),
runs the spectral detection method, and reports how many flipped samples were caught.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

try:
    from poison_detector.spectral import spectral_detect
except ImportError:
    spectral_detect = None  # type: ignore[assignment]

# Configuration for synthetic data generation
DEFAULT_CONFIG = {
    "n_samples": 200,
    "n_features": 10,
    "n_clusters": 2,
    "poison_rate": 0.05,
    "random_seed": 42,
    "cluster_separation": 3.0,
}


def _generate_synthetic_data(
    n_samples: int = 200,
    n_features: int = 10,
    cluster_separation: float = 3.0,
    poison_rate: float = 0.05,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Generate synthetic 2-cluster data with poisoned (flipped) labels.

    Returns dict with features, labels, poisoned_labels, and poison_mask.
    """
    rng = np.random.default_rng(random_seed)

    # Generate 2 Gaussian clusters
    samples_per_cluster = n_samples // 2

    cluster_0 = rng.standard_normal((samples_per_cluster, n_features))
    cluster_1 = rng.standard_normal((n_samples - samples_per_cluster, n_features)) + cluster_separation

    features = np.vstack([cluster_0, cluster_1])
    labels = np.array([0] * samples_per_cluster + [1] * (n_samples - samples_per_cluster))

    # Flip 5% of labels to simulate poisoning
    n_poison = int(n_samples * poison_rate)
    poison_indices = rng.choice(n_samples, size=n_poison, replace=False)
    poisoned_labels = labels.copy()
    poisoned_labels[poison_indices] = 1 - poisoned_labels[poison_indices]

    poison_mask = np.zeros(n_samples, dtype=bool)
    poison_mask[poison_indices] = True

    return {
        "features": features,
        "labels": labels,
        "poisoned_labels": poisoned_labels,
        "poison_mask": poison_mask,
        "poison_indices": poison_indices.tolist(),
        "n_poison": n_poison,
    }


def run_benchmark(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute the spectral poisoning detection benchmark.

    Generates synthetic poisoned data and evaluates how many poisoned samples
    the spectral method identifies.

    Returns a result dict conforming to the suite's JSON schema.
    """
    if spectral_detect is None:
        raise ImportError(
            "dataset-poisoning-detector is not installed. "
            "Install with: pip install dataset-poisoning-detector"
        )
    if np is None:
        raise ImportError(
            "numpy is not installed. Install with: pip install numpy"
        )
    config = config or DEFAULT_CONFIG

    # Generate synthetic data
    data = _generate_synthetic_data(
        n_samples=config["n_samples"],
        n_features=config["n_features"],
        cluster_separation=config["cluster_separation"],
        poison_rate=config["poison_rate"],
        random_seed=config["random_seed"],
    )

    # Run spectral detection
    detection_result = spectral_detect(
        features=data["features"],
        labels=data["poisoned_labels"],
    )

    # Extract detected indices from result
    if isinstance(detection_result, dict):
        detected_indices = set(detection_result.get("flagged_indices", []))
        scores = detection_result.get("scores", [])
    else:
        detected_indices = set(detection_result) if detection_result is not None else set()
        scores = []

    poison_set = set(data["poison_indices"])
    all_indices = set(range(config["n_samples"]))
    clean_indices = all_indices - poison_set

    # Compute metrics
    true_positives = poison_set & detected_indices
    false_positives = clean_indices & detected_indices
    false_negatives = poison_set - detected_indices

    tp_count = len(true_positives)
    fp_count = len(false_positives)
    fn_count = len(false_negatives)

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 1.0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    detection_rate = tp_count / data["n_poison"] if data["n_poison"] > 0 else 0.0

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = hashlib.sha256(
        f"spectral-adapter:{created_at}".encode()
    ).hexdigest()[:16]

    # Hash the config for reproducibility
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()

    # Dataset is synthetic, hash the generation parameters
    dataset_hash = hashlib.sha256(
        json.dumps(
            {"config": config, "generator": "numpy.random.default_rng"},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "suite_version": "0.1.0",
        "created_at": created_at,
        "run_id": run_id,
        "contract_version": "spectral-v1",
        "dataset_manifest": {
            "schema_version": "1.0.0",
            "name": "spectral-synthetic-poisoned",
            "source": "Synthetic 2-Gaussian-cluster data with 5% label flips",
            "license": "Apache-2.0",
            "version": "0.1.0",
            "dataset_hash": f"sha256:{dataset_hash}",
            "acquisition": "Generated at runtime with fixed seed for reproducibility",
            "split_policy": "Single evaluation set; no train/test split (detector is unsupervised).",
        },
        "input_identity": {
            "repository": "poojakira/dataset-poisoning-detector",
            "repository_commit": "evaluated-locally",
            "artifact_digest": f"sha256:{dataset_hash}",
            "model_hash": "n/a-unsupervised",
            "dataset_hash": f"sha256:{dataset_hash}",
            "configuration_hash": f"sha256:{config_hash}",
            "dependency_lock_hash": "evaluated-locally",
            "seeds": [config["random_seed"]],
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "adapter": "spectral_adapter",
            "scanner_package": "dataset-poisoning-detector",
        },
        "results": {
            "spectral": {
                "contract": "spectral-v1",
                "data_config": config,
                "aggregate_metrics": {
                    "total_samples": config["n_samples"],
                    "total_poisoned": data["n_poison"],
                    "total_detected": len(detected_indices),
                    "total_tp": tp_count,
                    "total_fp": fp_count,
                    "total_fn": fn_count,
                    "detection_rate": round(detection_rate, 4),
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                },
                "poison_indices": data["poison_indices"],
                "detected_indices": sorted(detected_indices),
                "true_positive_indices": sorted(true_positives),
                "false_positive_indices": sorted(false_positives),
                "false_negative_indices": sorted(false_negatives),
            }
        },
        "raw_artifacts": {
            "embedded_raw_sample_count": 1,
            "retention_policy": "Synthetic data regenerated from seed; detection scores embedded.",
            "spectral_scores_summary": {
                "count": len(scores) if scores else 0,
                "min": float(min(scores)) if scores else None,
                "max": float(max(scores)) if scores else None,
            },
        },
        "failure_accounting": {
            "spectral": {
                "failed_detections": fn_count,
                "total_poisoned": data["n_poison"],
                "false_positives": fp_count,
            }
        },
        "signature": {"algorithm": "unsigned", "payload_sha256": "", "value": ""},
    }

    # Compute payload hash for signature
    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    payload_hash = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload["signature"] = {
        "algorithm": "unsigned",
        "payload_sha256": payload_hash,
        "value": "",
    }

    return payload
