import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Info, AlertTriangle, ArrowRight } from 'lucide-react';

export default function AutomaticCheckResult({ checks }) {
  if (!checks) return null;

  return (
    <section aria-label="Automatic check results" className="master-checks-container mt-2">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-border-light">
        <ShieldCheck size={18} className="text-accent-primary" />
        <h3 className="m-0 font-semibold text-primary text-sm tracking-wide">Automatic checks</h3>
        {checks.status && (
          <span
            className={`badge text-[11px] ml-auto ${
              checks.status === 'completed'
                ? 'badge-green'
                : checks.status === 'partial'
                ? 'badge-amber'
                : 'badge-blue'
            }`}
          >
            {checks.status.toUpperCase()}
          </span>
        )}
      </div>

      {checks.status === 'partial' && (
        <div
          role="alert"
          className="p-2.5 mb-3 rounded-lg bg-amber-950/20 border border-amber-500/30 text-amber-200 text-xs flex items-center gap-2"
        >
          <AlertTriangle size={15} className="flex-shrink-0 text-status-warning" />
          <span>Your upload was saved, but some checks could not finish. See the status below.</span>
        </div>
      )}

      <ul className="list-none p-0 m-0 space-y-2">
        {checks.stages.map((stage) => (
          <li
            key={stage.detector}
            className="p-3 rounded-lg bg-surface/50 border border-border-light flex flex-col gap-2"
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <strong>{stage.detector.replaceAll('_', ' ')}:</strong>
                <span className="text-secondary font-medium">
                  {stage.status === 'failed' ? (
                    stage.message
                  ) : stage.missing_datasets?.length ? (
                    `Waiting for ${stage.missing_datasets.join(', ')}`
                  ) : stage.finding_count != null ? (
                    <span className="badge badge-amber text-xs">
                      {stage.finding_count} current findings
                    </span>
                  ) : stage.scored_count != null ? (
                    <span className="badge badge-blue text-xs">
                      {stage.scored_count} claims scored, {stage.flagged_count} flagged
                    </span>
                  ) : stage.circular_findings != null ? (
                    <span className="badge badge-orange text-xs">
                      {stage.circular_findings} cycles; {stage.reconciliation_findings} reconciliation findings
                    </span>
                  ) : (
                    'Completed'
                  )}
                </span>
              </div>

              {stage.finding_count > 0 && (
                <Link
                  to="/review-queue"
                  className="btn btn-outline text-xs px-2.5 py-1 text-accent-primary hover:bg-accent-primary/10 transition-colors"
                  style={{ textDecoration: 'none' }}
                >
                  Review In Queue &rarr;
                </Link>
              )}
            </div>

            {stage.availability
              ?.filter((s) => s.rule_id === 'VENDOR_NEW_LARGE_PAYMENT')
              .map((s) => (
                <div
                  key={s.rule_id}
                  className="mt-1 p-2.5 rounded bg-bg-surface border border-border-light text-xs text-muted flex items-start gap-2.5"
                >
                  <Info size={15} className="text-secondary flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-secondary">Rule Status: </span>
                    <p key={s.rule_id} className="inline m-0 text-secondary">
                      {s.message}
                    </p>
                    <p className="text-[11px] text-muted mt-1 mb-0">
                      Cross-dataset rule VENDOR_NEW_LARGE_PAYMENT verifies high-value transfers against new vendor creation dates once bank transfer feeds are linked.
                    </p>
                  </div>
                </div>
              ))}

            {stage.search_limited && (
              <p role="alert" className="mt-1 text-xs text-status-warning">
                Transfer search reached its limit; results are incomplete.
              </p>
            )}
          </li>
        ))}
      </ul>

      <div className="mt-3 pt-2.5 border-t border-border-light flex items-center justify-between">
        <Link
          className="record-link text-xs inline-flex items-center gap-1.5 text-accent-primary hover:underline font-medium"
          to="/audit-screens"
        >
          <span>View all anomaly signals</span>
          <ArrowRight size={13} />
        </Link>
      </div>
    </section>
  );
}
