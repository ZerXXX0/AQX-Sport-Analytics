import argparse
import json
from core import train
from etl import prepare, write_outputs

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--season', type=int, choices=[2023], default=2023)
    args = p.parse_args()
    df, manifest = prepare(season=args.season)
    manifest = write_outputs(df, manifest)
    print(json.dumps(manifest,indent=2))
    print(json.dumps(train(df),indent=2))
