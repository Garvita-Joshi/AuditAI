"""Focused local ablation using reviewed definitions from Untitled10; no OCR inputs."""
import ast
import json
import os
from pathlib import Path

os.environ['MPLBACKEND'] = 'Agg'
root = Path(__file__).resolve().parent
source = (root / 'Untitled10.txt').read_text(encoding='utf-8-sig')
tree = ast.parse(source)
prefix = source.split('# %% 1. Locate and load the dataset')[0]
ns = {}
exec(compile(prefix, 'reviewed_config', 'exec'), ns)
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'reviewed_definitions', 'exec'), ns)
ns['torch'].set_num_threads(2)
ns['DEVICE'] = 'cpu'
pd, np = ns['pd'], ns['np']
raw = pd.read_csv(root.parent / 'auditData/audit_anomalies_joined_dataset.csv')
frame = ns['build_features'](raw)
for name in ['NUM_A', 'NUM_C', 'CAT_BASE']:
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'feature_lists', 'exec'), ns)
for c in ns['CAT_BASE']:
    if c in frame:
        frame[c] = frame[c].fillna('__MISSING__').astype(str)
n = len(frame)
train, val, test = frame.iloc[:int(.7*n)], frame.iloc[int(.7*n):int(.85*n)], frame.iloc[int(.85*n):]
nt, nv = train[train.is_anomaly == 0], val[val.is_anomaly == 0]
ns.update(y_val=val.is_anomaly.to_numpy(), y_test=test.is_anomaly.to_numpy())
results = []
for key, numeric, robust in [('A', ns['NUM_A'], False), ('C_no_OCR', [c for c in ns['NUM_C'] if c not in ['log_ocr_amount', 'log_receipt_amount', 'ocr_mismatch_ratio', 'has_receipt']], True)]:
    num = [c for c in numeric if c in frame]
    cat = [c for c in ns['CAT_BASE'] if c in frame and nt[c].nunique() <= 30]
    pre = ns['make_preprocessor'](num, cat, robust)
    xt = pre.fit_transform(nt).astype('float32')
    xn, xv, xe = [pre.transform(d).astype('float32') for d in [nv, val, test]]
    for seed in [42, 43, 44]:
        ae = ns['train_autoencoder'](xt, xn, seed)
        iso = ns['IsolationForest'](n_estimators=300, random_state=seed, n_jobs=2).fit(xt)
        refs = ns['make_refs'](ae, iso, xt, xn)
        sv, _, _ = ns['score_families'](ae, iso, xv, refs)
        st, err, _ = ns['score_families'](ae, iso, xe, refs)
        for fam in ['AE only', 'IF only', 'Combined mean', 'Legacy 0-1 clipped']:
            row = ns['result_row'](key, seed, fam, sv[fam], st[fam])
            row.update(val_train=float(ae.errors(xn).mean()/ae.errors(xt).mean()), test_val=float(err[test.is_anomaly.to_numpy()==0].mean()/ae.errors(xn).mean()), inputs=xt.shape[1])
            results.append(row)
        print(key, seed, 'complete', flush=True)
pd.DataFrame(results).to_csv(root / 'no_ocr_results.csv', index=False)
summary = pd.DataFrame(results).groupby(['variant','family'])[['val_pr','pr_auc','f1thr_precision','f1thr_recall','f1thr_f1','val_train','test_val']].mean()
print(summary.round(4).to_string())
print('Rows:', len(raw), 'test anomalies:', int(test.is_anomaly.sum()))
