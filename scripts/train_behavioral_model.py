"""Train the project model from an explicitly labelled benchmark CSV.

python scripts/train_behavioral_model.py --csv auditData/audit_anomalies_joined_dataset.csv --trust-labels
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import torch
from backend.app import config
from backend.app.ml.pipeline import train_claims


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--trust-labels', action='store_true')
    parser.add_argument('--output', default=str(config.TRAINED_MODELS_DIR))
    args = parser.parse_args()
    if not args.trust_labels:
        parser.error('--trust-labels is required; do not assume unreviewed rows are normal')
    df = pd.read_csv(args.csv)
    target = 'is_anomaly' if 'is_anomaly' in df else 'is_fraud'
    if target not in df:
        parser.error('CSV must contain is_anomaly or is_fraud labels')
    def label(v):
        if str(v).lower() in ['0', 'false', '0.0']:
            return 0
        if str(v).lower() in ['1', 'true', '1.0']:
            return 1
        raise ValueError(f'Invalid label: {v!r}')
    records = df.astype(object).where(pd.notna(df), None).to_dict('records')
    config.TRAINED_MODELS_DIR = Path(args.output)
    torch.set_num_threads(2)
    a = train_claims(records, [label(v) for v in df[target]], config)
    report = {**a['metadata'], 'source': str(Path(args.csv).resolve()),
              'label_scope': 'user-declared trusted labels; synthetic metrics are not real fraud accuracy',
              'features': a['feature_names'], 'raw_threshold': a['threshold']}
    path = Path(args.output) / 'training_report.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['history','features']}, indent=2))
    print(f'Saved v2 bundle and training report to {Path(args.output).resolve()}')


if __name__ == '__main__':
    main()
