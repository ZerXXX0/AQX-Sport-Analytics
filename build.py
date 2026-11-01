import argparse
import json
from pathlib import Path
from core import ROOT, prepare, train

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=ROOT/'data'/'raw')
    p.add_argument('--season', type=int, default=2023)
    args = p.parse_args()
    df, manifest = prepare(args.source,args.season)
    (ROOT/'data').mkdir(exist_ok=True)
    df.to_parquet(ROOT/'data/shots.parquet',index=False)
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))
    print(json.dumps(train(df),indent=2))
