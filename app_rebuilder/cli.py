"""Command-line interface for local, authorized binary inventory."""
import argparse
import json
from .core import inspect_file

def main():
    parser = argparse.ArgumentParser(description="DEXTER App Rebuilder: inventario estático")
    parser.add_argument("file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect_file(args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else "\n".join(f"{k}: {v}" for k, v in result.items()))

if __name__ == "__main__":
    main()
