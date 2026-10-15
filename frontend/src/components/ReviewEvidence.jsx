import React from 'react';

const OBSERVED_SIGNALS = [
  { key: 'is_holiday', label: 'Holiday claim date', test: value => value >= 0.5, detail: 'The claim date appears on the configured holiday calendar.' },
  { key: 'weekend_flag', label: 'Weekend claim date', test: value => value >= 0.5, detail: 'The claim date falls on a weekend.' },
  { key: 'is_after_hours', label: 'Outside business hours', test: value => value >= 0.5, detail: 'The recorded time is outside normal business hours.' },
  { key: 'duplicate_prior', label: 'Prior amount match', test: value => value >= 0.5, detail: 'A previous claim from the same employee and vendor has the same amount.' },
  { key: 'ocr_mismatch_ratio', label: 'Receipt amount mismatch', test: value => value > 0.05, detail: 'The extracted receipt amount differs from the claimed amount by more than 5%.' },
  { key: 'ocr_vendor_mismatch', label: 'Receipt vendor mismatch', test: value => value >= 0.5, detail: 'The extracted receipt vendor differs from the claimed vendor.' },
  { key: 'vendor_name_deviation', label: 'Unusual vendor name', test: value => value >= 0.3, detail: 'The vendor name differs from names seen in the prior ledger.' },
  { key: 'z_employee', label: 'Amount outside employee pattern', test: value => Math.abs(value) >= 1, detail: 'The amount differs from this employee’s prior claim amounts.' },
  { key: 'z_vendor', label: 'Amount outside vendor pattern', test: value => Math.abs(value) >= 1, detail: 'The amount differs from prior claims for this vendor.' },
  { key: 'vendor_is_new', label: 'New vendor', test: value => value >= 0.5, detail: 'No earlier claim for this vendor was available to the model.' },
];

export default function ReviewEvidence({ prediction }) {
  const values = prediction?.feature_values || {};
  const timeKnown = Number(values._event_time_known || 0) >= 0.5;
  const staleAfterHoursSignal = !timeKnown && Number(values.is_after_hours || 0) >= 0.5;
  const holidayPolicyFlag = Number(values._holiday_policy_flag || 0) >= 0.5;
  const needsReview = Boolean(prediction?.is_flagged || holidayPolicyFlag);
  const observed = OBSERVED_SIGNALS.filter(signal => {
    if (signal.key === 'is_after_hours' && !timeKnown) return false;
    const value = Number(values[signal.key]);
    return Number.isFinite(value) && signal.test(value);
  }).filter(signal => !holidayPolicyFlag || signal.key !== 'is_holiday').slice(0, 5);

  return (
    <div className="glass-card review-evidence-card">
      <div>
        <h3 className="text-lg font-semibold text-accent-primary">Observed claim signals</h3>
        <p className="review-evidence-intro">
          {holidayPolicyFlag
            ? 'The holiday policy requires an auditor to check this claim, even when the anomaly index is low.'
            : needsReview
              ? 'This claim was flagged for review. The observations below are not ranked model contributions or proof of fraud.'
              : 'This claim was scored and not flagged. The observations below are data checks, not reasons for a review decision.'}
        </p>
      </div>

      <div className="review-evidence-list">
        {staleAfterHoursSignal && (
          <div className="review-evidence-item">
            <strong>Time of day unavailable</strong>
            <span>This claim has a date but no recorded transaction time. An earlier score treated the date as midnight; the outside-business-hours signal is unreliable until the claim is rescored.</span>
          </div>
        )}
        {holidayPolicyFlag && (
          <div className="review-evidence-item review-evidence-policy">
            <strong>Holiday receipt policy</strong>
            <span>The claim date is on the configured holiday calendar. An auditor should confirm when the expense occurred and when the receipt was submitted.</span>
            <small>Policy rule · requires review</small>
          </div>
        )}
        {observed.map(signal => (
          <div className="review-evidence-item" key={signal.key}>
            <strong>{signal.label}</strong>
            <span>{signal.detail}</span>
          </div>
        ))}
        {!holidayPolicyFlag && observed.length === 0 && needsReview && (
          <div className="review-evidence-item">
            <strong>Model review threshold reached</strong>
            <span>This claim was flagged by the model. Its per-feature explanation was not saved for this score.</span>
          </div>
        )}
        {!needsReview && observed.length === 0 && (
          <div className="review-evidence-item">
            <strong>No specific review trigger</strong>
            <span>The model evaluated this claim, but its anomaly index stayed below the review threshold. Feature attribution is stored only for flagged claims.</span>
          </div>
        )}
      </div>

      <p className="review-evidence-note">
        {!timeKnown && 'No transaction time was supplied, so business-hours status cannot be determined. '}
        Observed signals describe claim data; they are not SHAP values or a probability of fraud.
      </p>
    </div>
  );
}
