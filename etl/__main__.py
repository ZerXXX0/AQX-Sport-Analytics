"""Run with python -m etl; no model or network access is needed."""

import argparse
import json

from . import prepare, write_outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, choices=[2023], default=2023)
    args = parser.parse_args()
    shots, report = prepare(season=args.season)
    print(json.dumps(write_outputs(shots, report), indent=2))


if __name__ == '__main__':
    main()
