#!/usr/bin/env python3
import argparse
import json
import random
import time
from typing import List, Tuple

import joblib
import pandas as pd
import requests
from requests import Response
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sample a target classifier API, train a surrogate model, and upload it "
            "to the /model endpoint until a target accuracy is reached."
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://154.57.164.68:32213",
        help="Target base URL (default: http://154.57.164.68:32213)",
    )
    parser.add_argument("--min-flipper", type=float, default=150.0)
    parser.add_argument("--max-flipper", type=float, default=250.0)
    parser.add_argument("--min-mass", type=float, default=2500.0)
    parser.add_argument("--max-mass", type=float, default=6500.0)
    parser.add_argument(
        "--start-samples",
        type=int,
        default=120,
        help="Initial number of random samples",
    )
    parser.add_argument(
        "--sample-step",
        type=int,
        default=80,
        help="How many extra samples to add each retry",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=6,
        help="Maximum train/upload attempts",
    )
    parser.add_argument(
        "--target-accuracy",
        type=float,
        default=0.80,
        help="Required uploaded model accuracy",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP timeout in seconds",
    )
    parser.add_argument(
        "--output",
        default="surrogate.joblib",
        help="Output surrogate model path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for reproducibility",
    )
    return parser.parse_args()


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def query_classifier(
    session: requests.Session,
    base_url: str,
    flipper_length: float,
    body_mass: float,
    timeout: int,
) -> str:
    params = {
        "flipper_length": flipper_length,
        "body_mass": body_mass,
    }
    response: Response = session.get(base_url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if "result" not in payload:
        raise ValueError(f"Unexpected response payload: {payload}")
    return payload["result"]


def sample_dataset(
    session: requests.Session,
    base_url: str,
    n_samples: int,
    min_flipper: float,
    max_flipper: float,
    min_mass: float,
    max_mass: float,
    timeout: int,
) -> Tuple[pd.DataFrame, List[str]]:
    rows: List[Tuple[float, float]] = []
    labels: List[str] = []

    for _ in range(n_samples):
        flipper = random.uniform(min_flipper, max_flipper)
        mass = random.uniform(min_mass, max_mass)

        # Small retry loop helps deal with transient network issues.
        last_error = None
        for _retry in range(4):
            try:
                label = query_classifier(session, base_url, flipper, mass, timeout)
                rows.append((flipper, mass))
                labels.append(label)
                last_error = None
                break
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                time.sleep(0.25)

        if last_error is not None:
            raise RuntimeError(f"Failed to query classifier after retries: {last_error}")

    samples_df = pd.DataFrame(rows, columns=["Flipper Length (mm)", "Body Mass (g)"])
    return samples_df, labels


def train_surrogate(samples_df: pd.DataFrame, labels: List[str]):
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=1337),
    )
    model.fit(samples_df, labels)
    return model


def upload_model(
    session: requests.Session,
    base_url: str,
    model_path: str,
    timeout: int,
) -> dict:
    with open(model_path, "rb") as model_file:
        file_bytes = model_file.read()

    response = session.post(
        f"{base_url}/model",
        files={"file": ("surrogate.joblib", file_bytes)},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    args = parse_args()
    base_url = normalize_base_url(args.base_url)
    random.seed(args.seed)

    session = requests.Session()
    session.headers.update({"User-Agent": "htb-model-re-solver/1.0"})

    best_accuracy = -1.0
    best_payload = {}

    for attempt_idx in range(args.max_attempts):
        n_samples = args.start_samples + (attempt_idx * args.sample_step)
        print(f"[+] Attempt {attempt_idx + 1}/{args.max_attempts} with {n_samples} samples")

        samples_df, labels = sample_dataset(
            session=session,
            base_url=base_url,
            n_samples=n_samples,
            min_flipper=args.min_flipper,
            max_flipper=args.max_flipper,
            min_mass=args.min_mass,
            max_mass=args.max_mass,
            timeout=args.timeout,
        )

        surrogate_model = train_surrogate(samples_df, labels)
        joblib.dump(surrogate_model, args.output)
        print(f"[+] Saved surrogate model: {args.output}")

        result_payload = upload_model(
            session=session,
            base_url=base_url,
            model_path=args.output,
            timeout=args.timeout,
        )
        print(f"[+] Upload result: {json.dumps(result_payload)}")

        accuracy = float(result_payload.get("accuracy", -1.0))
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_payload = result_payload

        if accuracy >= args.target_accuracy:
            print(
                f"[+] Success: accuracy {accuracy:.4f} >= target {args.target_accuracy:.4f}"
            )
            return

        print(
            f"[-] Accuracy {accuracy:.4f} below target {args.target_accuracy:.4f}; retrying"
        )

    raise SystemExit(
        "[!] Could not reach target accuracy. "
        f"Best result: {json.dumps(best_payload)}"
    )


if __name__ == "__main__":
    main()
