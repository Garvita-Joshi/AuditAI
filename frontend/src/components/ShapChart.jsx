import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const FEATURE_LABELS = {
  log_amount: 'Claim amount (log scale)',
  is_negative: 'Negative amount',
  is_round: 'Round amount',
  hour: 'Submission hour',
  weekend_flag: 'Weekend submission',
  is_after_hours: 'After-hours submission',
  z_global: 'Amount vs. all claims',
  z_vendor: 'Amount vs. vendor history',
  z_employee: 'Amount vs. employee history',
  z_category: 'Amount vs. category history',
  log_vendor_prior_n: 'Vendor history volume',
  log_employee_prior_n: 'Employee history volume',
  vendor_is_new: 'New vendor',
  employee_is_new: 'New employee',
  pair_is_new: 'New employee-vendor pair',
  vendor_missing: 'Missing vendor identity',
  employee_missing: 'Missing employee identity',
  log_vendor_freq_30d: 'Vendor frequency (30 days)',
  log_employee_freq_7d: 'Employee frequency (7 days)',
  log_days_since_vendor: 'Days since vendor was seen',
  duplicate_prior: 'Prior duplicate match',
  log_pair_amount_1d: 'Same-pair amount (1 day)',
  log_pair_count_1d: 'Same-pair count (1 day)',
  has_receipt: 'Receipt present',
  ocr_amount_missing: 'Receipt amount missing',
  ocr_confidence: 'OCR confidence',
  ocr_confidence_missing: 'OCR confidence missing',
  ocr_low_confidence: 'OCR low confidence',
  log_ocr_amount: 'Receipt amount',
  ocr_mismatch_ratio: 'Receipt amount mismatch',
  ocr_vendor_mismatch: 'Receipt vendor mismatch',
  ocr_date_gap: 'Receipt date gap',
  vendor_name_deviation: 'Vendor name deviation',
  amount_mismatch_ratio: 'Receipt amount mismatch',
  has_amount_mismatch: 'Amount mismatch flag',
  duplicate_score: 'Duplicate similarity',
  is_likely_duplicate: 'Likely duplicate',
  vendor_anomaly_score: 'Vendor anomaly',
  is_known_vendor: 'Known vendor signal',
  amount_zscore: 'Employee amount outlier',
  claim_frequency_7d: '7-day claim frequency',
  claim_frequency_30d: '30-day claim frequency',
  is_weekend: 'Weekend submission',
  is_holiday: 'Holiday submission',
  is_round_amount: 'Round amount',
  amount_log: 'Claim amount scale',
  split_transaction_flag: 'Split transaction',
  category_risk_score: 'Category risk',
};

export default function ShapChart({ shapValues, featureValues = {}, maxFeatures = 10, supervised = false }) {
  if (!shapValues || Object.keys(shapValues).length === 0) {
    return (
      <div className="glass-card text-center py-12">
        <p className="text-secondary">No explanation data available.</p>
      </div>
    );
  }

  // Convert to array and sort by absolute magnitude
  const data = Object.entries(shapValues)
    .map(([name, value]) => ({
      name,
      label: FEATURE_LABELS[name] || name.replace(/_/g, ' '),
      value,
      rawValue: featureValues[name],
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, maxFeatures)
    .reverse(); // Reverse for horizontal chart (biggest at top)

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="glass-card" style={{ padding: '12px' }}>
          <p className="font-semibold">{data.label}</p>
          <p className={data.value > 0 ? "text-status-danger" : "text-status-success"}>
            {data.value > 0 ? 'Increases' : 'Reduces'} anomaly evidence: {Math.abs(data.value).toFixed(4)}
          </p>
          <p className="text-xs text-secondary mt-1">Feature value: {data.rawValue ?? 'not available'}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glass-card h-full">
      <h3 className="text-lg font-semibold mb-6">{supervised ? 'Detection model evidence (SHAP)' : 'Isolation Forest evidence (SHAP)'}</h3>
      <div style={{ height: '300px', width: '100%' }}>
        <ResponsiveContainer>
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 12 }}
              width={140}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.value > 0 ? 'var(--status-danger)' : 'var(--status-success)'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-center gap-6 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div style={{ width: 12, height: 12, background: 'var(--status-danger)', borderRadius: 2 }}></div>
          <span className="text-secondary">Increases anomaly evidence</span>
        </div>
        <div className="flex items-center gap-2">
          <div style={{ width: 12, height: 12, background: 'var(--status-success)', borderRadius: 2 }}></div>
          <span className="text-secondary">Reduces anomaly evidence</span>
        </div>
      </div>
      <p className="text-xs text-muted text-center mt-3">SHAP explains model evidence; it is not a fraud probability.</p>
    </div>
  );
}
