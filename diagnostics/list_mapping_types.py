import json
import re
from pathlib import Path

CONTRACT_PATHS = [
    Path("config/mapping_contract.json"),
    Path("config/mapping_contract_rl.json"),
]


def normalize_mt(mapping_type: str) -> str:
    mapping_type = str(mapping_type).strip()
    if not mapping_type:
        return mapping_type
    match = re.match(r"^([a-zA-Z_]+)\((.*)\)$", mapping_type)
    if match:
        return f"{match.group(1)}(<param>)"
    return mapping_type


def main() -> None:
    normalized: set[str] = set()
    raw: set[str] = set()
    by_contract: dict[str, set[str]] = {}

    for path in CONTRACT_PATHS:
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract_mts: set[str] = set()

        for mapping in contract.get("mappings", []):
            mt = mapping.get("mapping_type")
            if mt is None:
                continue
            if isinstance(mt, str):
                mt = [mt]

            for item in mt:
                item = str(item).strip()
                if not item:
                    continue
                raw.add(item)
                normalized.add(normalize_mt(item))
                contract_mts.add(item)

        by_contract[path.name] = contract_mts

    print("=== Mapping types by contract (raw) ===")
    for name, mts in sorted(by_contract.items()):
        print(f"{name}: {len(mts)}")
        for item in sorted(mts):
            print(f"  - {item}")

    print("\n=== All mapping types (normalized) ===")
    print(f"count: {len(normalized)}")
    for item in sorted(normalized):
        print(f"  - {item}")


if __name__ == "__main__":
    main()
