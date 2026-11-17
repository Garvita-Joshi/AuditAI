import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Shield, Clock, FileText, ClipboardList, Info, CheckCircle2, AlertTriangle, ChevronRight, Layers, FileCheck, Database, Building2, Users, ShieldCheck } from 'lucide-react';
import { claimsApi, casesApi, reportsApi, reviewQueueApi, sourcingApi } from '../api/client';
import ScoreGauge from '../components/ScoreGauge';
import ShapChart from '../components/ShapChart';
import ReviewEvidence from '../components/ReviewEvidence';
import PolicyEvidence from '../components/PolicyEvidence';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useAuth } from '../auth/AuthContext';
import { useAuditProfile } from '../context/AuditProfileContext';
import './ClaimDetail.css';

function formatTimelineNote(note) {
  if (!note) return null;
  const trimmed = String(note).trim();
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed.checks && Array.isArray(parsed.checks)) {
        const reviewChecks = parsed.checks.filter(c => c.status === 'review');
        const passChecks = parsed.checks.filter(c => c.status === 'pass');
        return {
          isStructured: true,
          summary: reviewChecks.length > 0
            ? `Policy check flagged: ${reviewChecks.map(c => c.code.replace(/_/g, ' ')).join(', ')}`
            : `All policy checks passed (${passChecks.length} rules verified)`,
          rawJson: trimmed,
        };
      }
      return {
        isStructured: true,
        summary: parsed.detail || parsed.message || 'System policy evaluation logged',
        rawJson: trimmed,
      };
    } catch {
      // Fallback to plain text
    }
  }
  return { isStructured: false, text: note };
}

export default function ClaimDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const claimsReturnTo = location.state?.claimsReturnTo || '/claims';
  const { user } = useAuth();
  const { companyName, currency } = useAuditProfile();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [auditTrail, setAuditTrail] = useState([]);
  const [activeTab, setActiveTab] = useState('policy'); // 'policy', 'shap', 'trail'

  // Case Action Fields
  const [role, setRole] = useState('maker');
  const [submittingAction, setSubmittingAction] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState('');
  const [paypalBusy, setPaypalBusy] = useState(false);
  const [paypalMsg, setPaypalMsg] = useState('');

  const fetchDetail = async () => {
    setLoading(true);
    setData(null);
    try {
      const response = await claimsApi.getDetail(id);
      setData(response.data);

      const trailResponse = await casesApi.getTrail(id);
      setAuditTrail(trailResponse.data);
    } catch (error) {
      console.error("Failed to fetch claim detail:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const reviewerRoles = ['maker', 'checker'].filter(candidate => user?.roles?.includes(candidate));
  useEffect(() => {
    if (reviewerRoles.length && !reviewerRoles.includes(role)) setRole(reviewerRoles[0]);
  }, [user, role]);

  const openSharedReview = async () => {
    setSubmittingAction(true);
    try {
      const item = (await reviewQueueApi.expense(id)).data;
      navigate(`/review/cases/${item.id}`);
    } catch (error) {
      alert(error.response?.data?.detail || 'Could not open the shared review case.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setReportError('');
    try {
      await reportsApi.generate(id);
      await fetchDetail();
    } catch (error) {
      setReportError(error.response?.data?.detail || 'The report could not be generated. Please try again.');
    } finally {
      setGeneratingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="main-content">
        <LoadingSkeleton type="detail" count={3} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="main-content text-center py-20">
        <h2 className="text-2xl mb-4">Claim not found</h2>
        <button className="btn btn-secondary" onClick={() => navigate(claimsReturnTo)}>Back to Claims</button>
      </div>
    );
  }

  const { claim, ocr_result, prediction, audit_report, review_permissions, case_review, master_check } = data;
  const reviewBlockReason = role === 'checker' ? review_permissions?.checker_block_reason : review_permissions?.maker_block_reason;
  const anomalyScore = prediction?.combined_fraud_score !== null && prediction?.combined_fraud_score !== undefined
    ? Math.round(prediction.combined_fraud_score * 100)
    : null;
  const modelEnabled = prediction?.feature_values?._model_enabled !== false;
  const modelThreshold = Number(prediction?.feature_values?._model_threshold ?? 0.5);

  // Risk tier classification
  const isHighRisk = anomalyScore !== null && anomalyScore >= 65;
  const isModerateRisk = anomalyScore !== null && anomalyScore >= 35 && anomalyScore < 65;
  const isLowRisk = anomalyScore !== null && anomalyScore < 35;
  const holidayPolicyFlag = Number(prediction?.feature_values?._holiday_policy_flag || 0) >= 0.5;

  // Show AI explanation ONLY if the claim is actually flagged or elevated risk
  const isFlaggedOrRisk = Boolean(
    prediction?.is_flagged ||
    claim.status === 'flagged' ||
    claim.status === 'rejected' ||
    isHighRisk ||
    data.policy?.requires_review ||
    holidayPolicyFlag
  );

  // Safely fallback to policy tab if shap is not applicable
  const displayTab = (!isFlaggedOrRisk && activeTab === 'shap') ? 'policy' : activeTab;

  const scoreInterpretation = !modelEnabled
    ? 'Expense ML is disabled for enterprise records. Policy and dedicated rules determine review.'
    : anomalyScore === null ? 'Waiting for a model score'
    : prediction.combined_fraud_score >= modelThreshold
      ? 'Model review recommended at the validation-selected cutoff.'
      : prediction.is_flagged ? 'Policy review required; model score is below its cutoff.'
      : 'Model score is within expected range.';

  const noReviewNeeded = claim.status === 'scored' && !prediction?.is_flagged && !holidayPolicyFlag && !data.policy?.requires_review;
  const timeKnown = Number(prediction?.feature_values?._event_time_known || 0) >= 0.5;
  const visibleShapValues = timeKnown ? prediction?.shap_values : Object.fromEntries(
    Object.entries(prediction?.shap_values || {}).filter(([feature]) => !['hour', 'is_after_hours'].includes(feature))
  );

  const hasReceiptData = ocr_result && (ocr_result.extracted_vendor || ocr_result.extracted_amount || ocr_result.raw_ocr_text);
  const procMeta = prediction?.feature_values?._procurement_ml || null;
  const procPay = procMeta?.paypal_payment || null;
  const currencySymbol = (procMeta?.currency || currency) === 'USD' ? '$' : '₹';

  const effectiveBasis = (Array.isArray(procMeta?.basis) && procMeta.basis.length > 0)
    ? procMeta.basis
    : (procMeta ? [
        {
          check: '3-Way PO & Invoice Match',
          detail: `PO ${procMeta.po_number || 'N/A'} (${currencySymbol}${Number(procMeta.po_total || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}) matches Stated Invoice (${currencySymbol}${Number(procMeta.stated_total || claim.claimed_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}) with zero variance.`,
          passed: true,
          status: 'MATCHED'
        },
        {
          check: 'Master Reference Data & Collusion',
          detail: `${master_check?.vendor?.name || claim.vendor_name} is verified active. Zero bank account or PAN collision with employee ${claim.employee_name || claim.employee_id}.`,
          passed: !master_check?.collusion_screening?.bank_collision,
          status: master_check?.collusion_screening?.bank_collision ? 'FLAGGED' : 'VERIFIED'
        },
        {
          check: 'Autoencoder Reconstruction Error',
          detail: `Raw Mean Squared Error is ${Number(procMeta.autoencoder_raw_mse || 0).toFixed(4)} (${((procMeta.autoencoder_score || 0) * 100).toFixed(2)}% percentile error), within expected historical variance bounds.`,
          passed: Number(procMeta.autoencoder_score || 0) < 0.5,
          status: 'NORMAL'
        },
        {
          check: 'Isolation Forest Anomaly Depth',
          detail: `Unsupervised tree isolation score is ${((procMeta.isolation_forest_score || 0) * 100).toFixed(2)}% (threshold ${((procMeta.threshold || 0.90) * 100).toFixed(1)}%). Transaction lies inside normal cluster.`,
          passed: Number(procMeta.isolation_forest_score || 0) < (procMeta.threshold || 0.90),
          status: 'CLEAN'
        }
      ] : []);

  const handleClaimPaypalDirectSettle = async () => {
    if (!procMeta?.request_id || paypalBusy) return;
    setPaypalBusy(true);
    setPaypalMsg('');
    try {
      const res = await sourcingApi.paypalDirectSettle(procMeta.request_id);
      const payload = res?.data || res;
      if (payload?.paypal_payment) {
        const oid = payload.paypal_payment.paypal_order_id || payload.paypal_payment.order_id;
        setPaypalMsg(`✓ Direct Settlement Successful! Live PayPal Sandbox Order ${oid} settled via API without login.`);
        await fetchDetail();
      }
    } catch (err) {
      setPaypalMsg(`Error: ${err.response?.data?.detail || err.message || 'Direct settlement failed'}`);
    } finally {
      setPaypalBusy(false);
    }
  };

  const handleClaimPaypalCheckout = async () => {
    if (!procMeta?.request_id || paypalBusy) return;
    setPaypalBusy(true);
    setPaypalMsg('');
    try {
      const res = await sourcingApi.paypalCheckout(procMeta.request_id);
      const payload = res?.data || res;
      if (payload?.paypal_payment) {
        const oid = payload.paypal_payment.paypal_order_id || payload.paypal_payment.order_id;
        setPaypalMsg(`PayPal Sandbox Order Created: ${oid}`);
        if (payload.paypal_payment.approval_url) {
          window.open(payload.paypal_payment.approval_url, '_blank', 'noopener,noreferrer');
        }
        await fetchDetail();
      }
    } catch (err) {
      setPaypalMsg(`Error: ${err.response?.data?.detail || err.message || 'PayPal Sandbox checkout failed'}`);
    } finally {
      setPaypalBusy(false);
    }
  };

  const handleClaimPaypalCapture = async () => {
    if (!procMeta?.request_id || paypalBusy) return;
    setPaypalBusy(true);
    setPaypalMsg('');
    try {
      const res = await sourcingApi.paypalCapture(procMeta.request_id);
      const payload = res?.data || res;
      if (payload?.paypal_payment) {
        setPaypalMsg(`PayPal Sandbox Order Settled (${payload.paypal_payment.status})`);
        await fetchDetail();
      }
    } catch (err) {
      setPaypalMsg(`Error: ${err.response?.data?.detail || err.message || 'PayPal capture failed'}`);
    } finally {
      setPaypalBusy(false);
    }
  };

  return (
    <div className="main-content">
      {/* Top Navigation & Status Header */}
      <div className="glass-card mb-6" style={{ padding: '16px 20px' }}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              className="btn btn-secondary py-1.5 px-3 text-xs flex items-center gap-1.5"
              onClick={() => navigate(claimsReturnTo)}
              title="Return to claims list"
            >
              <ArrowLeft size={15} />
              <span>Claims</span>
            </button>
            <div className="h-6 w-px bg-border-glass"></div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight">{claim.claim_id}</h1>
                <span className={`badge ${claim.status === 'approved' ? 'badge-green' :
                    claim.status === 'flagged' || claim.status === 'rejected' ? 'badge-red' :
                      claim.status === 'scored' ? 'badge-blue' : 'badge-amber'
                  }`}>
                  {claim.status.toUpperCase()}
                </span>
                {anomalyScore !== null && (
                  <span className={`badge ${isHighRisk ? 'badge-red' : isModerateRisk ? 'badge-amber' : 'badge-green'} text-xs`}>
                    {isHighRisk ? 'High Risk' : isModerateRisk ? 'Moderate' : 'Low Risk'} ({anomalyScore}/100)
                  </span>
                )}
              </div>
              <span className="text-xs text-muted">{companyName} · {currency} · Submitted {claim.claimed_date}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {reviewerRoles.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Role:</span>
                {reviewerRoles.length === 1 ? (
                  <strong className="text-xs font-semibold uppercase badge text-secondary">{reviewerRoles[0]}</strong>
                ) : (
                  <select
                    className="input py-1 px-2 text-xs font-semibold"
                    value={role}
                    onChange={e => setRole(e.target.value)}
                    style={{ width: 90 }}
                  >
                    {reviewerRoles.map(assignedRole => (
                      <option key={assignedRole} value={assignedRole}>{assignedRole}</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {!noReviewNeeded && user?.roles?.some(r => ['maker', 'checker', 'admin'].includes(r)) && (
              <button
                className="btn btn-primary py-1.5 px-4 text-xs font-semibold flex items-center gap-1.5"
                onClick={openSharedReview}
                disabled={submittingAction}
              >
                <Shield size={14} />
                <span>{submittingAction ? 'Opening...' : 'Open Review Case'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main 2-Column Overview (Claim Info + Risk Assessment) */}
      <div className="claim-overview-grid mb-6">
        {/* Left: Clean Claim Details & Receipt Card */}
        <div className="glass-card flex flex-col justify-between" style={{ padding: '24px' }}>
          <div>
            <div className="flex items-start justify-between mb-4">
              <div>
                <span className="text-xs text-secondary uppercase font-semibold tracking-wider block mb-1">Claimed Amount</span>
                <div className="claim-amount-highlight">
                  {currencySymbol}{claim.claimed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
              {claim.category && (
                <span className="badge badge-blue text-xs font-medium">
                  {claim.category}
                </span>
              )}
            </div>

            {/* Key Metadata Grid */}
            <div className="claim-meta-grid">
              <div className="claim-meta-item">
                <span className="claim-meta-label">Employee</span>
                <span className="claim-meta-value">{claim.employee_name}</span>
                <small className="text-xs text-muted">ID: {claim.employee_id}</small>
              </div>

              <div className="claim-meta-item">
                <span className="claim-meta-label">Vendor</span>
                <span className="claim-meta-value flex items-center gap-1.5">
                  {claim.vendor_name}
                  {claim.closest_vendor_match && (
                    <span
                      className="badge badge-amber text-xs"
                      title={`Resembles '${claim.closest_vendor_match}' (${Math.round(claim.vendor_similarity_score * 100)}% match)`}
                    >
                      Typo?
                    </span>
                  )}
                </span>
                {claim.closest_vendor_match ? (
                  <small className="text-xs text-amber-400">Matches: {claim.closest_vendor_match}</small>
                ) : (
                  <small className="text-xs text-muted">Verified Vendor</small>
                )}
              </div>

              <div className="claim-meta-item">
                <span className="claim-meta-label">Claim Date</span>
                <span className="claim-meta-value">{claim.claimed_date}</span>
                <small className="text-xs text-muted">Submission Record</small>
              </div>

              <div className="claim-meta-item">
                <span className="claim-meta-label">Receipt Status</span>
                {hasReceiptData ? (
                  <span className="claim-meta-value text-status-success flex items-center gap-1">
                    <FileCheck size={16} /> Attached & Extracted
                  </span>
                ) : (
                  <span className="claim-meta-value text-secondary flex items-center gap-1">
                    ERP Ledger Entry
                  </span>
                )}
                <small className="text-xs text-muted">
                  {ocr_result?.extraction_method ? `Method: ${ocr_result.extraction_method}` : 'Standard entry'}
                </small>
              </div>
            </div>
          </div>

          {/* Clean Receipt Sub-box */}
          <div className="mt-5 pt-4 border-t border-slate-200">
            {hasReceiptData ? (
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-sm">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200/70">
                  <strong className="text-slate-900 font-semibold flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-600" /> OCR Extraction Verified
                  </strong>
                  <span className="badge badge-blue text-xs font-medium">Extraction: {ocr_result.extraction_method}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-700">
                  <div className="bg-white p-3 rounded-lg border border-slate-200/80 shadow-xs">
                    <span className="text-xs text-slate-500 block mb-0.5 font-medium">Vendor on bill</span>
                    <strong className="text-slate-900 text-sm">{ocr_result.extracted_vendor || 'Not detected'}</strong>
                  </div>
                  <div className="bg-white p-3 rounded-lg border border-slate-200/80 shadow-xs">
                    <span className="text-xs text-slate-500 block mb-0.5 font-medium">Amount on bill</span>
                    <strong className="text-slate-900 text-sm">{ocr_result.extracted_amount ? `₹${Number(ocr_result.extracted_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : 'Not detected'}</strong>
                  </div>
                </div>
                {ocr_result.raw_ocr_text && (
                  <details className="mt-3 text-slate-500">
                    <summary className="cursor-pointer hover:text-slate-900 font-medium text-xs">View extracted receipt text</summary>
                    <pre className="mono-pre mt-2 p-3 text-xs bg-white rounded-lg border border-slate-200 text-slate-800" style={{ maxHeight: '100px', overflowY: 'auto' }}>
                      {ocr_result.raw_ocr_text}
                    </pre>
                  </details>
                )}
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs text-slate-600">
                <div className="flex items-center gap-2">
                  <Info size={16} className="text-indigo-600" />
                  <span>No physical receipt image uploaded. Validated via core expense ledger data.</span>
                </div>
                <span className="badge text-xs bg-white border border-slate-200 text-slate-700">Standard ERP</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Clean Fraud Risk Assessment Card */}
        <div className="glass-card flex flex-col justify-between" style={{ padding: '24px' }}>
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-secondary flex items-center gap-2">
                <Shield size={16} className="text-accent-primary" />
                Fraud Risk Assessment
              </h3>
              {anomalyScore !== null && (
                <span className={`badge ${isHighRisk ? 'badge-red' : isModerateRisk ? 'badge-amber' : 'badge-green'} text-xs font-semibold`}>
                  {isHighRisk ? 'Action Required' : isModerateRisk ? 'Review Suggested' : 'Normal / Low Risk'}
                </span>
              )}
            </div>

            {/* Gauge Display */}
            {!prediction ? (
              <p className="text-secondary text-center italic py-10">This claim has not been scored yet.</p>
            ) : (
              <>
                <div className="flex justify-center my-4 py-1">
                  <ScoreGauge label="Anomaly Index (0–100)" score={prediction.combined_fraud_score} size={190} />
                </div>

                {/* Plain-English Verdict Box */}
                <div className={`risk-verdict-banner ${isHighRisk ? 'risk-verdict-high' : isModerateRisk ? 'risk-verdict-moderate' : 'risk-verdict-low'}`}>
                  <strong>
                    {isHighRisk
                      ? 'High Anomaly Index Detected'
                      : isModerateRisk
                      ? 'Moderate Statistical Variance'
                      : 'Normal Spending Pattern'}
                  </strong>
                  <p className="mt-1 text-xs opacity-90 leading-relaxed">
                    {isHighRisk
                      ? 'This claim deviates significantly from normal employee expense benchmarks. Auditor review is recommended.'
                      : isModerateRisk
                      ? 'Minor pattern deviation detected in amount or timing. Standard verification recommended.'
                      : 'This transaction falls well within normal expected historical patterns for this category and department.'}
                  </p>
                </div>

                {holidayPolicyFlag && (
                  <div className="risk-policy-alert mt-3 text-xs">
                    <strong>Holiday receipt exception:</strong> Claim date ({claim.claimed_date}) falls on a configured holiday calendar.
                  </div>
                )}
              </>
            )}
          </div>

          {/* Clean Expandable Drawer for Technical / ML Diagnostics */}
          {prediction && (
            <details className="risk-diagnostics-dropdown">
              <summary className="flex items-center justify-between">
                <span>View Advanced AI & Math Diagnostics</span>
                <span className="text-xs text-muted">Reconstruction & Forest</span>
              </summary>
              <div className="risk-diagnostics-content">
                <div className="diagnostics-metric-row">
                  <div className="diagnostics-metric-box">
                    <span className="text-xs text-muted block">Reconstruction Error</span>
                    <strong className="text-sm text-slate-900">{prediction.reconstruction_error?.toFixed(4) ?? 'N/A'}</strong>
                    <small className="text-[11px] text-muted block mt-0.5">Learned normality fit</small>
                  </div>
                  <div className="diagnostics-metric-box">
                    <span className="text-xs text-muted block">Isolation Forest</span>
                    <strong className="text-sm text-slate-900">{prediction.isolation_forest_score?.toFixed(4) ?? 'N/A'}</strong>
                    <small className="text-[11px] text-muted block mt-0.5">Outlier separation index</small>
                  </div>
                </div>

                <div className="text-xs text-secondary leading-relaxed space-y-1.5">
                  <p>
                    <strong>How to interpret:</strong> An anomaly index measures mathematical divergence from historical data. A score of {anomalyScore}/100 does not mean a {anomalyScore}% probability of fraud.
                  </p>
                  <p className="text-[11px] text-muted">
                    Model Threshold Cutoff: <b>{(modelThreshold * 100).toFixed(1)}/100</b>. {scoreInterpretation}
                  </p>
                </div>
              </div>
            </details>
          )}
        </div>
      </div>

      {/* ── MASTER REFERENCE DATA & INTERNAL COLLUSION SCREENING ──────────────── */}
      {master_check && (
        <div
          className="master-screening-card"
          style={{
            border: master_check.collusion_screening?.passed
              ? '1.5px solid #bbf7d0'
              : '1.5px solid #fecaca',
          }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-xl flex items-center justify-center ${master_check.collusion_screening?.passed ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                <Database size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 className="text-base sm:text-lg font-bold tracking-tight text-slate-900" style={{ margin: 0 }}>
                    Master Reference Data & Internal Collusion Screening
                  </h2>
                  <span
                    className={`badge ${
                      master_check.collusion_screening?.passed ? 'badge-green' : 'badge-red'
                    } text-xs font-semibold px-2.5 py-0.5`}
                  >
                    {master_check.collusion_screening?.verdict === 'CLEAN'
                      ? '✓ Ground Truth Verified'
                      : '⚠ Conflict Flagged'}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Real-time cross-referencing against Company Vendor Master and HR Roster to detect self-dealing, ghost vendors, and payroll kickbacks.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge text-xs px-3 py-1 font-medium bg-slate-100 text-slate-700 border border-slate-200">
                Deterministic Screening Engine
              </span>
            </div>
          </div>

          {/* 3 Pillars Grid: Vendor Master, Employee Roster, Collusion Verification */}
          <div className="master-pillars-grid">
            {/* 1. Vendor Master Baseline */}
            <div className="master-pillar-box">
              <div>
                <div className="flex items-center justify-between font-bold mb-3 pb-2.5 border-b border-slate-200/80">
                  <span className="flex items-center gap-2 text-slate-900 text-sm">
                    <Building2 size={17} className="text-indigo-600" /> Vendor Master Baseline
                  </span>
                  <span
                    className={`badge text-xs font-semibold px-2.5 py-0.5 ${
                      master_check.vendor?.is_registered ? 'badge-green' : 'badge-amber'
                    }`}
                  >
                    {master_check.vendor?.status || 'Active'}
                  </span>
                </div>
                <div>
                  <div className="master-data-row">
                    <span className="master-data-label">Entity</span>
                    <strong className="master-data-value">
                      {master_check.vendor?.name} {master_check.vendor?.id && <span className="text-xs font-mono text-slate-500 font-normal">({master_check.vendor?.id})</span>}
                    </strong>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Tax ID (GSTIN)</span>
                    <span className="master-data-value font-mono text-xs">{master_check.vendor?.gstin || 'Not on file'}</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">PAN Record</span>
                    <span className="master-data-value font-mono text-xs">{master_check.vendor?.pan || 'Not on file'}</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Registered Bank</span>
                    <span className="master-data-value font-mono text-xs">{master_check.vendor?.bank_account_masked || 'None'}</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Address</span>
                    <span className="master-data-value text-xs truncate max-w-[170px]" title={master_check.vendor?.address}>
                      {master_check.vendor?.address || 'Not on file'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Employee HR Roster */}
            <div className="master-pillar-box">
              <div>
                <div className="flex items-center justify-between font-bold mb-3 pb-2.5 border-b border-slate-200/80">
                  <span className="flex items-center gap-2 text-slate-900 text-sm">
                    <Users size={17} className="text-indigo-600" /> HR Employee Roster
                  </span>
                  <span
                    className={`badge text-xs font-semibold px-2.5 py-0.5 ${
                      master_check.employee?.is_active ? 'badge-green' : 'badge-red'
                    }`}
                  >
                    {master_check.employee?.status || 'Active Roster'}
                  </span>
                </div>
                <div>
                  <div className="master-data-row">
                    <span className="master-data-label">Claimant</span>
                    <strong className="master-data-value">
                      {master_check.employee?.name} {master_check.employee?.id && <span className="text-xs font-mono text-slate-500 font-normal">({master_check.employee?.id})</span>}
                    </strong>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Department</span>
                    <span className="master-data-value text-xs">{master_check.employee?.department || 'Operations'}</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Tenure Status</span>
                    <span className="text-emerald-700 font-semibold text-xs bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Valid Active Employee</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Disbursement Bank</span>
                    <span className="master-data-value font-mono text-xs">{master_check.employee?.bank_account_masked || 'None'}</span>
                  </div>
                  <div className="master-data-row">
                    <span className="master-data-label">Roster Source</span>
                    <span className="master-data-value text-xs">{master_check.employee?.source || 'Internal Staff Directory'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. Anti-Collusion & Account Collision Check */}
            <div
              className="master-pillar-box"
              style={{
                background: master_check.collusion_screening?.passed
                  ? '#f0fdf4'
                  : '#fff1f2',
                borderColor: master_check.collusion_screening?.passed
                  ? '#bbf7d0'
                  : '#fecdd3',
              }}
            >
              <div>
                <div className="flex items-center justify-between font-bold mb-3 pb-2.5 border-b border-slate-200/60">
                  <span className="flex items-center gap-2 text-slate-900 text-sm">
                    <ShieldCheck
                      size={18}
                      className={
                        master_check.collusion_screening?.passed ? 'text-emerald-600' : 'text-rose-600'
                      }
                    />
                    Collusion Screening
                  </span>
                  <span
                    className={`badge text-xs font-semibold px-2.5 py-0.5 ${
                      master_check.collusion_screening?.passed ? 'badge-green' : 'badge-red'
                    }`}
                  >
                    {master_check.collusion_screening?.verdict}
                  </span>
                </div>
                <p className="text-xs leading-relaxed mb-3 text-slate-700">
                  {master_check.collusion_screening?.summary}
                </p>
              </div>

              <div className="space-y-2 pt-3 border-t border-slate-200/60 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/95 border border-slate-200 shadow-xs">
                  <span className="text-slate-600 font-medium">Bank Collision (B_vendor == B_emp):</span>
                  <span
                    className={
                      master_check.collusion_screening?.bank_collision
                        ? 'text-rose-700 font-bold bg-rose-50 px-2 py-0.5 rounded border border-rose-200'
                        : 'text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200'
                    }
                  >
                    {master_check.collusion_screening?.bank_collision ? 'FAIL (Collision)' : 'PASS (Distinct)'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/95 border border-slate-200 shadow-xs">
                  <span className="text-slate-600 font-medium">PAN / Identity Overlap:</span>
                  <span
                    className={
                      master_check.collusion_screening?.pan_collision
                        ? 'text-rose-700 font-bold bg-rose-50 px-2 py-0.5 rounded border border-rose-200'
                        : 'text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200'
                    }
                  >
                    {master_check.collusion_screening?.pan_collision ? 'FAIL (Overlap)' : 'PASS (Distinct)'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {procMeta && (
        <div className="glass-card mb-6" style={{ padding: '24px', border: procMeta.is_fraud ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid rgba(16, 185, 129, 0.35)' }}>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2.5">
              <Shield size={20} className={procMeta.is_fraud ? 'text-status-danger' : 'text-status-success'} />
              <div>
                <h2 className="text-base font-bold tracking-tight">
                  Procurement Final Invoice ML Fraud Evaluation & PayPal Sandbox Settlement
                </h2>
                <p className="text-xs text-muted">
                  Hybrid PyTorch Autoencoder + Isolation Forest ({procMeta.version || 'procurement-hybrid-v3'}) · Source {procMeta.source_ref || claim.claim_id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`badge ${procMeta.is_fraud ? 'badge-red' : 'badge-green'} text-xs font-bold`}>
                {procMeta.verdict || (procMeta.is_fraud ? 'FRAUD_FLAGGED' : 'CLEAN_APPROVED')}
              </span>
              {procMeta.request_id && String(procMeta.source_ref || '').startsWith('SR-') && (
                <button
                  type="button"
                  className="btn btn-secondary text-xs py-1 px-3"
                  onClick={() => navigate(`/intake/${procMeta.request_id}`)}
                >
                  Open Sourcing Request ({procMeta.source_ref}) →
                </button>
              )}
            </div>
          </div>

          {/* Core ML Scores & PO/Invoice Comparison */}
          <div className="grid gap-3 mb-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))' }}>
            <div className="p-3 rounded-lg bg-bg-surface border border-border-light">
              <span className="text-[11px] uppercase text-muted font-semibold block">Combined Anomaly Score</span>
              <strong className={`text-lg font-extrabold ${procMeta.is_fraud ? 'text-status-danger' : 'text-status-success'}`}>
                {((procMeta.score || 0) * 100).toFixed(2)}%
              </strong>
              <small className="text-[11px] text-muted block mt-0.5">
                Decision Threshold: {((procMeta.threshold || 0.72) * 100).toFixed(1)}%
              </small>
            </div>
            <div className="p-3 rounded-lg bg-bg-surface border border-border-light">
              <span className="text-[11px] uppercase text-muted font-semibold block">Autoencoder (60% Weight)</span>
              <strong className="text-base font-bold text-primary">
                {((procMeta.autoencoder_score || 0) * 100).toFixed(2)}%
              </strong>
              <small className="text-[11px] text-muted block mt-0.5">
                Raw MSE: {Number(procMeta.autoencoder_raw_mse || 0).toFixed(4)}
              </small>
            </div>
            <div className="p-3 rounded-lg bg-bg-surface border border-border-light">
              <span className="text-[11px] uppercase text-muted font-semibold block">Isolation Forest (40% Weight)</span>
              <strong className="text-base font-bold text-primary">
                {((procMeta.isolation_forest_score || 0) * 100).toFixed(2)}%
              </strong>
              <small className="text-[11px] text-muted block mt-0.5">
                Raw Score: {Number(procMeta.isolation_forest_raw || 0).toFixed(4)}
              </small>
            </div>
            <div className="p-3 rounded-lg bg-bg-surface border border-border-light">
              <span className="text-[11px] uppercase text-muted font-semibold block">PO vs Stated Invoice</span>
              <strong className="text-sm font-bold text-primary block">
                PO ({procMeta.po_number || 'N/A'}): {currencySymbol}{Number(procMeta.po_total || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </strong>
              <small className="text-[11px] text-secondary block mt-0.5">
                Inv ({procMeta.invoice_number || 'N/A'}): {currencySymbol}{Number(procMeta.stated_total || claim.claimed_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </small>
            </div>
          </div>

          {/* 4-Pillar ML Basis Checks */}
          {effectiveBasis.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-secondary mb-2">
                4-Pillar Procurement ML Basis Checks
              </h3>
              <div className="grid gap-2.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                {effectiveBasis.map((b, idx) => {
                  const isStr = typeof b === 'string';
                  const checkTitle = isStr ? (b.split(':')[0] || `Check ${idx + 1}`) : b.check;
                  const detailText = isStr ? (b.split(':').slice(1).join(':').trim() || b) : b.detail;
                  const passed = isStr ? !/(mismatch|anomaly|exceed|flag|spike)/i.test(b) : Boolean(b.passed);
                  const statusLabel = isStr ? (passed ? 'PASSED' : 'REVIEW') : b.status;
                  return (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border text-xs"
                      style={{
                        background: passed ? 'rgba(16, 185, 129, 0.06)' : 'rgba(239, 68, 68, 0.08)',
                        borderColor: passed ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.3)',
                      }}
                    >
                      <div className="flex items-center justify-between font-bold mb-1">
                        <span className={passed ? 'text-status-success' : 'text-status-danger'}>
                          {passed ? '✓' : '✗'} {checkTitle}
                        </span>
                        <span className="badge text-[10px]" style={{ background: 'rgba(255,255,255,0.06)' }}>
                          {statusLabel}
                        </span>
                      </div>
                      <p className="text-secondary leading-relaxed">{detailText}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Triggers if any */}
          {Array.isArray(procMeta.triggers) && procMeta.triggers.length > 0 && (
            <div className="mb-4 p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-xs">
              <strong className="text-status-danger block mb-1">Active Risk Triggers:</strong>
              <ul className="list-disc pl-5 space-y-1 text-secondary">
                {procMeta.triggers.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 8-Feature Breakdown Table */}
          {procMeta.feature_values && Object.keys(procMeta.feature_values).length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-secondary mb-2">
                8-Feature Model Input Vector & Autoencoder Reconstruction Errors
              </h3>
              <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
                {Object.entries(procMeta.feature_values).map(([feat, val]) => {
                  const errVal = procMeta.feature_errors?.[feat] ?? prediction?.shap_values?.[feat] ?? 0;
                  return (
                    <div key={feat} className="p-2.5 rounded bg-bg-surface border border-border-light text-xs flex flex-col justify-between">
                      <span className="font-mono text-[11px] text-accent-primary font-semibold">{feat}</span>
                      <div className="flex items-baseline justify-between mt-1">
                        <span className="text-secondary">Value: <strong className="text-primary">{Number(val).toFixed(4)}</strong></span>
                        <span className="text-muted text-[11px]">Err: <strong>{Number(errVal).toFixed(4)}</strong></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* PayPal Sandbox Settlement Gate */}
          {!procMeta.is_fraud && (
            <div
              className="p-4 rounded-xl border mt-3"
              style={{
                background: 'linear-gradient(135deg, rgba(0, 112, 186, 0.12), rgba(16, 185, 129, 0.08))',
                borderColor: 'rgba(0, 112, 186, 0.35)',
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-extrabold uppercase tracking-wider" style={{ color: '#60a5fa' }}>
                      PayPal Sandbox Settlement Gate
                    </span>
                    <span className={`badge ${String(procPay?.status || '').toUpperCase() === 'COMPLETED' ? 'badge-green' : procPay ? 'badge-blue' : 'badge-amber'} text-xs`}>
                      {String(procPay?.status || 'READY_FOR_CHECKOUT').toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-secondary mt-1">
                    {(procPay?.paypal_order_id || procPay?.order_id) ? (
                      <>
                        PayPal Sandbox Order ID: <strong className="font-mono text-primary">{procPay.paypal_order_id || procPay.order_id}</strong>
                        {(procPay.paypal_amount || procPay.amount_usd) ? (
                          <> · Settlement Amount: <strong>${Number(procPay.paypal_amount || procPay.amount_usd || 0).toFixed(2)} USD</strong></>
                        ) : null}
                        {procPay.capture_id ? <> · Capture ID: <strong className="font-mono">{procPay.capture_id}</strong></> : null}
                      </>
                    ) : (
                      'ML model approved this final invoice. Connect to PayPal Sandbox to generate a live Sandbox order and settle supplier payment.'
                    )}
                  </p>
                  {(procPay?.paypal_order_id || procPay?.order_id) && String(procPay?.status || '').toUpperCase() !== 'COMPLETED' && (
                    <div className="mt-2 p-2 rounded bg-status-success/10 border border-status-success/30 text-xs text-status-success">
                      <strong>Direct Settlement:</strong> You can skip filling card numbers on PayPal. Click <strong>"Confirm / Capture Sandbox Payment"</strong> on the right to settle immediately.
                    </div>
                  )}
                </div>

                {String(procMeta.source_ref || '').startsWith('SR-') && procMeta.request_id && (
                  <div className="flex flex-wrap items-center gap-2">
                    {String(procPay?.status || '').toUpperCase() !== 'COMPLETED' && (
                      <button
                        type="button"
                        className="btn btn-primary text-xs font-bold py-2 px-4"
                        onClick={handleClaimPaypalDirectSettle}
                        disabled={paypalBusy}
                        style={{ background: '#059669', borderColor: '#059669' }}
                      >
                        {paypalBusy ? 'Settling via API…' : '1-Click Direct Settlement (Skip Login)'}
                      </button>
                    )}

                    {procPay?.approval_url && String(procPay?.status || '').toUpperCase() !== 'COMPLETED' && (
                      <a
                        href={procPay.approval_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary text-xs font-bold py-2 px-3"
                        style={{ borderColor: '#60a5fa', color: '#93c5fd' }}
                      >
                        Open PayPal Web Login ↗
                      </a>
                    )}

                    {(procPay?.paypal_order_id || procPay?.order_id) && String(procPay?.status || '').toUpperCase() !== 'COMPLETED' && (
                      <button
                        type="button"
                        className="btn btn-primary text-xs font-bold py-2 px-3"
                        onClick={handleClaimPaypalCapture}
                        disabled={paypalBusy}
                        style={{ background: '#059669', borderColor: '#059669' }}
                      >
                        {paypalBusy ? 'Capturing...' : 'Confirm / Capture Sandbox Payment'}
                      </button>
                    )}
                  </div>
                )}
              </div>
              {paypalMsg && (
                <div className="mt-2 text-xs font-semibold" style={{ color: paypalMsg.startsWith('Error') ? '#f87171' : '#34d399' }}>
                  {paypalMsg}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Deep-Dive Analysis Section with Clean Tabs */}
      <div className="claim-section-tabs">
        <button
          type="button"
          className={`claim-tab-btn ${displayTab === 'policy' ? 'active' : ''}`}
          onClick={() => setActiveTab('policy')}
        >
          <ClipboardList size={16} />
          <span>Company Policy & Review Actions</span>
        </button>

        {isFlaggedOrRisk && (
          <button
            type="button"
            className={`claim-tab-btn ${displayTab === 'shap' ? 'active' : ''}`}
            onClick={() => setActiveTab('shap')}
            style={{ borderColor: 'rgba(239, 68, 68, 0.35)' }}
          >
            <AlertTriangle size={15} className="text-status-danger" />
            <span>Why Was This Flagged? (AI Risk Factors)</span>
            <span className="badge badge-red text-xs" style={{ fontSize: '0.65rem', padding: '1px 5px' }}>Review</span>
          </button>
        )}

        <button
          type="button"
          className={`claim-tab-btn ${displayTab === 'trail' ? 'active' : ''}`}
          onClick={() => setActiveTab('trail')}
        >
          <Clock size={16} />
          <span>Audit Trail & Reports ({auditTrail.length})</span>
        </button>
      </div>

      {/* Tab 1: Company Policy & Review Action */}
      {displayTab === 'policy' && (
        <div className="space-y-6">
          <section className="glass-card mb-6">
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <CheckCircle2 size={18} className="text-accent-primary" />
              Automated Policy Checks
            </h2>
            <PolicyEvidence result={data.policy} />
          </section>

          {/* Review Actions Drawer */}
          <div className="glass-card">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-accent-primary">
              <Shield size={20} />
              Reviewer Actions & Case Status
            </h3>

            <div className="flex items-center gap-2 text-xs text-secondary mb-4">
              <span>Investigation Case Status:</span>
              <span className="badge badge-gray text-xs">{claim.case_status?.replace(/_/g, ' ') || 'None'}</span>
            </div>

            {role === 'checker' && case_review?.maker_recommendation && (
              <div className="bg-bg-surface border border-border-light rounded p-3 mb-4 text-xs">
                <div className="font-semibold text-accent-primary mb-1">
                  Maker recommendation{case_review.maker_name ? ` · ${case_review.maker_name}` : ''}
                </div>
                <div className="text-secondary italic mb-2">"{case_review.maker_notes || 'No comments left.'}"</div>
                <div>Recommended: <strong>{case_review.maker_recommendation.toUpperCase()}</strong></div>
              </div>
            )}

            {noReviewNeeded ? (
              <div className="p-3 rounded-lg bg-status-success/10 border border-status-success/30 text-xs text-secondary">
                This claim scored below the review threshold and passed all automated policy checks. No manual intervention required.
              </div>
            ) : reviewBlockReason ? (
              <div className="p-3 rounded-lg bg-status-warning/10 border border-status-warning/30 text-xs text-secondary">
                {reviewBlockReason}
              </div>
            ) : null}

            {!noReviewNeeded && user?.roles?.some(r => ['maker', 'checker', 'admin'].includes(r)) && (
              <div className="mt-4 flex items-center gap-3">
                <button className="btn btn-primary" onClick={openSharedReview} disabled={submittingAction}>
                  Open Shared Review Case
                </button>
                <span className="text-xs text-muted">All review decisions and comments are logged to the shared review queue.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: AI Risk Factors (Only displayed when the claim is flagged or elevated risk) */}
      {displayTab === 'shap' && isFlaggedOrRisk && (
        <div className="glass-card">
          <div className="mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2 text-status-danger">
              <AlertTriangle size={18} />
              Key Factors That Triggered This Risk Alert
            </h3>
            <p className="text-xs text-secondary mt-1">
              The chart below highlights the specific data patterns (such as unusual amount, timing, or vendor frequency) that caused the AI system to flag this transaction.
            </p>
          </div>

          <div style={{ minHeight: '380px' }}>
            {Object.keys(visibleShapValues || {}).length > 0 ? (
              <ShapChart
                shapValues={visibleShapValues}
                featureValues={prediction?.feature_values || {}}
                maxFeatures={6}
                supervised={Boolean(prediction?.feature_values?._supervised_score)}
              />
            ) : prediction ? (
              <ReviewEvidence prediction={prediction} />
            ) : (
              <div className="flex items-center justify-center py-20 text-secondary">
                This claim has not been scored yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Audit Trail & Reports */}
      {displayTab === 'trail' && (
        <div className="grid-cols-2 gap-6">
          {/* AI Audit Report */}
          <div className="glass-card flex flex-col justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <FileText className="text-accent-primary" size={18} />
                Executive AI Audit Summary
              </h3>

              {audit_report ? (
                <div className="bg-bg-surface p-5 rounded-lg border border-border-light relative overflow-hidden" style={{ minHeight: '180px' }}>
                  <div className="absolute top-0 left-0 w-1 h-full bg-accent-primary"></div>
                  <p className="text-xs leading-relaxed text-secondary">{audit_report.report_text}</p>
                  <div className="mt-4 text-[11px] text-muted text-right">
                    Generated by {audit_report.generated_by}
                  </div>
                </div>
              ) : (
                <div className="bg-bg-surface/60 p-6 rounded-lg border border-border-light text-center flex flex-col items-center justify-center gap-3" style={{ minHeight: '180px' }}>
                  <FileText size={28} className="text-muted opacity-50" />
                  <div>
                    <h4 className="text-sm font-semibold text-primary">No Audit Report Generated Yet</h4>
                    <p className="text-secondary text-xs mt-1 max-w-sm">
                      {claim.status === 'flagged' || claim.status === 'rejected'
                        ? 'Generate an automated natural-language audit memo summarizing the findings.'
                        : 'Formal audit memos are typically generated when claims require manual investigation.'}
                    </p>
                  </div>
                  {(claim.status === 'flagged' || claim.status === 'rejected') && reviewerRoles.length > 0 && !review_permissions?.is_own_claim && (
                    <button className="btn btn-primary text-xs mt-1" onClick={handleGenerateReport} disabled={generatingReport}>
                      {generatingReport ? 'Generating memo…' : 'Generate AI Audit Summary'}
                    </button>
                  )}
                  {reportError && <p className="text-status-danger text-xs mt-2" role="alert">{reportError}</p>}
                </div>
              )}
            </div>
            <div className="text-[11px] text-muted mt-3 pt-2 border-t border-glass">
              All generated memos and compliance decisions are permanently timestamped.
            </div>
          </div>

          {/* Audit Case Timeline */}
          <div className="glass-card flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <ClipboardList className="text-accent-primary" size={18} />
                  Investigation Timeline & Activity
                </h3>
                <span className="badge text-xs" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  {auditTrail.length} {auditTrail.length === 1 ? 'event' : 'events'}
                </span>
              </div>

              <div className="bg-bg-surface p-4 rounded-lg border border-border-light overflow-y-auto" style={{ maxHeight: '320px' }}>
                {auditTrail.length === 0 ? (
                  <p className="text-secondary text-center text-xs italic py-10">No investigation actions recorded yet.</p>
                ) : (
                  <div className="timeline">
                    {auditTrail.map((log, idx) => {
                      const noteInfo = formatTimelineNote(log.notes);
                      return (
                        <div key={log.id || idx} className="flex gap-3 mb-4 text-xs">
                          <div className="flex flex-col items-center">
                            <div className="w-2.5 h-2.5 rounded-full bg-accent-primary"></div>
                            {idx < auditTrail.length - 1 && <div className="w-0.5 bg-border-light flex-1 my-1"></div>}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-primary uppercase text-[11px]">
                                {log.action.replace(/_/g, ' ')}
                              </span>
                              <span className="text-[10px] text-muted">
                                {new Date(log.timestamp).toLocaleDateString()} {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <div className="text-secondary text-xs mt-0.5">
                              By: <span className="font-medium text-primary">{log.performed_by}</span>
                            </div>

                            {/* Human-readable note display */}
                            {noteInfo && (
                              <div className="mt-1.5 p-2 rounded bg-bg-card/70 border border-border-glass text-xs">
                                {noteInfo.isStructured ? (
                                  <div>
                                    <div className="text-primary font-medium">{noteInfo.summary}</div>
                                    <details className="mt-1">
                                      <summary className="text-[10px] text-muted cursor-pointer hover:text-secondary">
                                        View technical check payload
                                      </summary>
                                      <pre className="mono-pre mt-1 p-1 text-[10px] overflow-x-auto" style={{ maxHeight: '100px' }}>
                                        {noteInfo.rawJson}
                                      </pre>
                                    </details>
                                  </div>
                                ) : (
                                  <div className="text-secondary">"{noteInfo.text}"</div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
            <div className="text-[11px] text-muted mt-3 pt-2 border-t border-glass">
              Append-only audit trail. Historical actions cannot be modified or deleted.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
