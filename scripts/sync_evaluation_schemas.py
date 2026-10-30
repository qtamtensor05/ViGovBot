"""Synchronize embedded Golden and prediction definitions in standalone v3 schemas."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "schema"


def _read(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _write(name: str, value: dict) -> None:
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _embedded(value: dict) -> dict:
    serialized = json.dumps(value, ensure_ascii=False)
    return json.loads(serialized.replace("#/$defs/", "#/$defs/golden_"))


def main() -> None:
    golden = _read("golden_dataset.schema.json")
    prediction = _read("prediction.schema.json")
    evaluation = _read("evaluation_case.schema.json")

    for key, value in golden["$defs"].items():
        prediction["$defs"]["golden_" + key] = _embedded(value)

    evaluation["properties"].update(deepcopy(prediction["properties"]))
    for key, value in prediction["$defs"].items():
        evaluation["$defs"][key] = deepcopy(value)

    _write("prediction.schema.json", prediction)
    _write("evaluation_case.schema.json", evaluation)


if __name__ == "__main__":
    main()
