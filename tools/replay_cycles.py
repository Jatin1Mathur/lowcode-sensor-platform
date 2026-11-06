"""Replay hydraulic test-rig cycles against the REST service.

Uses the UCI "Condition monitoring of hydraulic systems" dataset
(17 sensors, 2,205 cycles) when --data-dir points to its .txt files
(PS1.txt ... SE.txt; one row per cycle). Each row is reduced to its
mean value, so one cycle becomes one JSON payload.

Without --data-dir it generates realistic synthetic cycles, which is
handy for load and demo tests.

Examples:
    python tools/replay_cycles.py --synthetic --cycles 100
    python tools/replay_cycles.py --data-dir ./uci_hydraulic --batch-size 200
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.sensors import SENSORS  # noqa: E402

TYPICAL = {  # rough mid values for synthetic data
    "PS1": 160, "PS2": 110, "PS3": 2, "PS4": 2.5, "PS5": 9.2, "PS6": 9.1,
    "EPS1": 2500, "FS1": 6.2, "FS2": 9.6, "TS1": 45, "TS2": 50, "TS3": 48,
    "TS4": 41, "VS1": 0.6, "CE": 31, "CP": 1.8, "SE": 56,
}


def load_uci(data_dir: Path) -> list[dict[str, float]]:
    columns = {}
    for code in SENSORS:
        path = data_dir / f"{code}.txt"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        with path.open() as fh:
            columns[code] = [
                sum(map(float, line.split())) / len(line.split())
                for line in fh if line.strip()
            ]
    n = min(len(v) for v in columns.values())
    return [{code: round(columns[code][i], 4) for code in SENSORS} for i in range(n)]


def synthetic(count: int, seed: int = 42) -> list[dict[str, float]]:
    rng = random.Random(seed)
    cycles = []
    for _ in range(count):
        row = {}
        for code, sensor in SENSORS.items():
            value = TYPICAL[code] * rng.uniform(0.9, 1.1)
            row[code] = round(min(max(value, sensor.min_value), sensor.max_value), 4)
        cycles.append(row)
    return cycles


def to_payloads(rows, device_id: str, start: datetime) -> list[dict]:
    return [
        {
            "device_id": device_id,
            "cycle": i + 1,
            "timestamp": (start + timedelta(seconds=60 * i)).isoformat().replace("+00:00", "Z"),
            "readings": row,
        }
        for i, row in enumerate(rows)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:5000")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--device-id", default="hydraulic-rig-01")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--cycles", type=int, default=2205)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()

    if args.data_dir:
        rows = load_uci(args.data_dir)[: args.cycles]
    else:
        rows = synthetic(args.cycles)

    payloads = to_payloads(rows, args.device_id, datetime.now(timezone.utc))
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    stored = rejected = 0

    for start in range(0, len(payloads), args.batch_size):
        batch = payloads[start: start + args.batch_size]
        response = requests.post(f"{args.url}/api/readings/batch",
                                 json=batch, headers=headers, timeout=30)
        body = response.json()
        stored += body.get("stored", 0)
        rejected += body.get("rejected", 0)
        print(f"cycles {start + 1}-{start + len(batch)}: HTTP {response.status_code}")

    print(f"Done: {stored} stored, {rejected} rejected")


if __name__ == "__main__":
    main()
