import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { claimsApi, fraudApi, receiptsApi, procurementApi, sourcingApi } from '../api/client';
import FileUpload from '../components/FileUpload';
import MasterDataImport from '../components/MasterDataImport';
import AutomaticCheckResult from '../components/AutomaticCheckResult';
import { Play, FileText, Search, CheckCircle, Clock, AlertTriangle, Loader, Link2, FilePlus, Database, Bell, CreditCard, ShieldCheck } from 'lucide-react';
import { isReviewer, useAuth } from '../auth/AuthContext';
import { useAuditProfile } from '../context/AuditProfileContext';
import './Upload.css';

// ── Procurement Invoice Upload Pipeline ──────────────────────────────────────
function PipelineStep({ label, status, timestamp }) {
  const icon = status === 'done'
    ? <CheckCircle size={13} style={{ color: 'var(--color-status-success, #10b981)' }} />
    : status === 'partial'
    ? <AlertTriangle size={13} style={{ color: '#f59e0b' }} />
    : <Clock size={13} style={{ color: 'var(--color-muted, #6b7280)' }} />;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 90 }}>
      {icon}
      <span style={{ fontSize: 11, fontWeight: 500, color: status === 'done' ? 'var(--color-status-success, #10b981)' : status === 'partial' ? '#f59e0b' : 'var(--color-muted, #6b7280)' }}>{label}</span>
      {timestamp && <span style={{ fontSize: 9, color: 'var(--color-muted, #6b7280)' }}>{timestamp.slice(0, 19).replace('T', ' ')} UTC</span>}
    </div>
  );
}

function AuditTimeline({ events }) {
  if (!events || !events.length) return null;
  const dotColor = a => a?.includes('ml') ? '#f59e0b' : a?.includes('ocr') ? '#6366f1' : '#10b981';
  return (
    <div className="glass-card" style={{ padding: '14px 18px', marginTop: 14 }}>
      <h4 style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 13, marginBottom: 10 }}>
        <FileText size={13} /> Audit Trail
        <span className="badge text-xs" style={{ background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)', marginLeft: 4 }}>Immutable</span>
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {events.map((e, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor(e.action), marginTop: 4, flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 500, textTransform: 'capitalize' }}>{(e.action || '').replaceAll('_', ' ')}</div>
              <div style={{ fontSize: 10, color: 'var(--color-muted, #6b7280)' }}>{e.log_time || e.timestamp}</div>
              {e.detail && <div style={{ fontSize: 11, color: 'var(--color-secondary, #9ca3af)', marginTop: 2 }}>{e.detail}</div>}
              {e.error && <div style={{ fontSize: 10, color: '#f87171', marginTop: 2 }}>{e.error}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InvoiceUploadSection({ onUploaded }) {
  const [mode, setMode] = useState('attach');
  const [requests, setRequests] = useState([]);
  const [requestsLoaded, setRequestsLoaded] = useState(false);
  const [requestSearch, setRequestSearch] = useState('');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [invState, setInvState] = useState('idle');
  const [invResult, setInvResult] = useState(null);
  const [invError, setInvError] = useState('');
  const [authorities, setAuthorities] = useState([]);
  const [allApproved, setAllApproved] = useState(false);
  const [busyNodeId, setBusyNodeId] = useState(null);
  const [busyMl, setBusyMl] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState('pending');
  const [busyPay, setBusyPay] = useState(false);
  const [paidDetails, setPaidDetails] = useState(null);
  const [approveMsg, setApproveMsg] = useState('');
  const navigate = useNavigate();

  const loadRequests = async () => {
    try { const { data } = await procurementApi.requestsIndex(); setRequests(data); setRequestsLoaded(true); } catch { setRequests([]); }
  };
  const filtered = requests.filter(r => `${r.label} ${r.supplier}`.toLowerCase().includes(requestSearch.toLowerCase()));

  const handleInvoiceUpload = async (file) => {
    if (mode === 'attach' && !selectedRequest) { setInvError('Select a procurement request to attach this invoice to.'); setInvState('error'); return; }
    setInvState('uploading'); setInvError(''); setInvResult(null);
    setAuthorities([]); setAllApproved(false); setPaymentStatus('pending'); setPaidDetails(null); setApproveMsg('');
    try {
      const { data } = await procurementApi.uploadInvoice(file, mode === 'attach' ? selectedRequest?.id : null, mode);
      setInvResult(data);
      setInvState('done');
      setAuthorities(data.required_authorities || []);
      setAllApproved(false);
      setPaymentStatus('pending');
      if (onUploaded) onUploaded(data);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Invoice upload failed.';
      setInvError(typeof msg === 'string' ? msg : JSON.stringify(msg)); setInvState('error');
    }
  };

  const handleApproveAuthority = async (nodeId, label, ownerGroup) => {
    const srId = invResult?.sourcing_request_id || invResult?.request_id;
    if (!srId) return;
    setBusyNodeId(nodeId);
    setInvError('');
    try {
      const { data } = await sourcingApi.approveCheckpoint(srId, {
        node_id: nodeId,
        label,
        owner_group: ownerGroup,
      });
      setAuthorities(data.required_authorities || []);
      setAllApproved(Boolean(data.all_authorities_approved));
      setApproveMsg(data.message || 'Authority approval recorded.');
      setInvResult(prev => ({
        ...prev,
        pipeline_steps: (prev.pipeline_steps || []).map(s => {
          if (s.step.includes('Authority')) return { ...s, status: data.all_authorities_approved ? 'done' : 'ready' };
          if (s.step.includes('ML')) return { ...s, status: data.all_authorities_approved ? 'ready' : 'pending' };
          return s;
        }),
      }));
    } catch (e) {
      setInvError(e.response?.data?.detail || 'Authority approval failed.');
    } finally {
      setBusyNodeId(null);
    }
  };

  const handleRunFinalMl = async () => {
    const srId = invResult?.sourcing_request_id || invResult?.request_id;
    if (!srId) return;
    setBusyMl(true);
    setInvError('');
    try {
      const { data } = await sourcingApi.evaluateFinalInvoice(srId, {
        invoice_number: invResult?.ocr_result?.invoice_number,
        supplier_id: invResult?.ocr_result?.supplier_id,
        stated_total: invResult?.ocr_result?.total,
      });
      setInvResult(prev => ({
        ...prev,
        ml_assessment: data.assessment,
        pipeline_steps: (prev.pipeline_steps || []).map(s => {
          if (s.step.includes('ML')) return { ...s, status: 'done', timestamp: new Date().toISOString() };
          if (s.step.includes('Payment')) return { ...s, status: data.assessment && !data.assessment.is_fraud ? 'ready' : 'pending' };
          return s;
        }),
      }));
    } catch (e) {
      setInvError(e.response?.data?.detail || 'ML fraud check failed.');
    } finally {
      setBusyMl(false);
    }
  };

  const handlePay = async () => {
    const srId = invResult?.sourcing_request_id || invResult?.request_id;
    if (!srId) return;
    setBusyPay(true);
    setInvError('');
    try {
      const { data } = await sourcingApi.paypalDirectSettle(srId);
      setPaymentStatus('paid');
      setPaidDetails(data);
      setInvResult(prev => ({
        ...prev,
        request_status: 'approved',
        pipeline_steps: (prev.pipeline_steps || []).map(s => {
          if (s.step.includes('Payment')) return { ...s, status: 'done', timestamp: new Date().toISOString() };
          return s;
        }),
      }));
    } catch (e) {
      setInvError(e.response?.data?.detail || 'Payment settlement failed.');
    } finally {
      setBusyPay(false);
    }
  };

  const ocr = invResult?.ocr_result || {};
  const ml = invResult?.ml_assessment;
  const steps = invResult?.pipeline_steps || [];
  const trail = invResult?.audit_trail || [];
  const srId = invResult?.sourcing_request_id || invResult?.request_id;
  const approvedCount = authorities.filter(a => a.status === 'approved').length;

  return (
    <div className="upload-section-card mb-6">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 8 }}>
        <div>
          <h3 id="invoice-import" className="upload-section-title">
            2. Upload Invoice & Receipt
            <span className="badge text-xs" style={{ background: 'rgba(239,153,118,0.18)', color: '#ef9976', border: '1px solid rgba(239,153,118,0.35)', marginLeft: 8, verticalAlign: 'middle' }}>OCR & 3-Way Match</span>
          </h3>
          <p className="upload-section-sub" style={{ marginBottom: 12 }}>
            Upload a supplier invoice or receipt document — OCR extracts the fields & line items, notifies each respective approval authority in AuditAI, then unlocks Final ML Fraud Check and Payment Settlement.
          </p>
        </div>
      </div>

      {/* Mode selector: Exactly two options */}
      <div className="upload-mode-buttons">
        {[['attach', Link2, 'Attach to existing request'], ['new', FilePlus, 'New standalone invoice']].map(([m, Icon, label]) => (
          <button key={m} className={`upload-mode-btn ${mode === m ? 'active' : ''}`}
            onClick={() => { setMode(m); setInvResult(null); setInvState('idle'); setInvError(''); setAuthorities([]); setAllApproved(false); setPaymentStatus('pending'); setPaidDetails(null); if (m === 'attach') loadRequests(); else setSelectedRequest(null); }}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* Attach mode: request search */}
      {mode === 'attach' && (
        <div className="upload-target-search">
          <label className="text-xs text-secondary mb-2 block font-semibold">Target Procurement Request</label>
          <div style={{ position: 'relative', marginBottom: 8 }}>
            <Search size={15} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', opacity: 0.5, pointerEvents: 'none' }} />
            <input type="text" className="input"
              placeholder="Search SR / PR number, title, or supplier…"
              value={requestSearch}
              onFocus={loadRequests}
              onChange={e => { setRequestSearch(e.target.value); loadRequests(); }} />
          </div>
          {(requestSearch || !selectedRequest) && filtered.length > 0 && (
            <div className="glass-card" style={{ padding: '6px 0', maxHeight: 200, overflowY: 'auto', marginBottom: 12, background: '#241e1a' }}>
              {filtered.slice(0, 12).map(r => (
                <button key={r.id} style={{ width: '100%', padding: '10px 16px', textAlign: 'left', display: 'block', background: selectedRequest?.id === r.id ? 'rgba(239,153,118,0.15)' : 'transparent', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
                  className="text-xs text-primary" onClick={() => { setSelectedRequest(r); setRequestSearch(''); }}>
                  <span className="font-semibold text-accent-primary">{r.label}</span>
                  <span className="text-muted" style={{ marginLeft: 10 }}>{r.status} · {r.supplier}</span>
                </button>
              ))}
            </div>
          )}
          {selectedRequest && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', background: 'rgba(239,153,118,0.1)', borderRadius: 8, border: '1px solid rgba(239,153,118,0.3)', marginBottom: 14 }}>
              <CheckCircle size={16} style={{ color: '#34d399' }} />
              <span className="text-xs font-semibold text-primary">{selectedRequest.label}</span>
              <span className="text-muted text-xs">· {selectedRequest.status}</span>
              <button className="text-muted text-xs hover:text-primary" style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setSelectedRequest(null)}>✕ Clear</button>
            </div>
          )}
        </div>
      )}

      {/* New mode info */}
      {mode === 'new' && (
        <div className="mb-6" style={{ padding: '14px 18px', background: 'rgba(239,153,118,0.08)', borderRadius: 10, border: '1px solid rgba(239,153,118,0.25)' }}>
          <p className="text-xs text-secondary"><span className="font-semibold text-primary">Autonomous Direct Invoice Mapping:</span> Creates a new Procurement Request (SR-XXXX) with the Approval Mind Map and pre-lists the extracted company & all line items directly (AI vendor discovery is skipped because the supplier is already on the invoice).</p>
        </div>
      )}

      {/* File upload */}
      <FileUpload label="Upload invoice PDF / image"
        accept="image/*,application/pdf,.txt"
        onUpload={handleInvoiceUpload}
        uploadState={invState === 'uploading' ? 'uploading' : invState === 'done' ? 'complete' : invState === 'error' ? 'error' : 'idle'} />

      {invError && (
        <div className="glass-card mt-4 flex items-center p-4 border-l-4 border-status-danger">
          <AlertTriangle size={14} style={{ color: '#f87171', marginRight: 8, flexShrink: 0 }} />
          <span className="text-sm">{invError}</span>
        </div>
      )}

      {/* Results */}
      {invResult && (<>
        {/* Request linkage banner */}
        <div className="glass-card mt-4" style={{ padding: '14px 18px', background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.25)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle size={16} style={{ color: '#10b981' }} />
              <span className="text-sm font-medium">
                {mode === 'new' ? 'New procurement request created: ' : 'Existing request updated with invoice & mind map: '}
                <strong>{invResult.request_ref || `SR-${String(srId).padStart(4, '0')}`} · {invResult.request_title}</strong>
              </span>
              <span className="badge text-xs" style={{ background: 'rgba(239,153,118,0.18)', color: '#ef9976', border: '1px solid rgba(239,153,118,0.35)' }}>
                {paymentStatus === 'paid' ? 'Paid & Approved' : allApproved ? 'Authorities Approved' : 'Awaiting Respective Authorities'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn btn-primary text-xs"
                onClick={() => navigate(`/procurement/invoice-review/${srId}`)}
              >
                Open Dedicated Invoice Review &amp; Mind Map →
              </button>
              <button
                type="button"
                className="btn btn-secondary text-xs"
                onClick={() => navigate('/procurement')}
              >
                All Requests
              </button>
            </div>
          </div>
        </div>

        {/* Pipeline steps */}
        {steps.length > 0 && (
          <div className="glass-card mt-4" style={{ padding: '14px 18px' }}>
            <h4 style={{ fontWeight: 600, fontSize: 13, marginBottom: 14 }}>5-Stage Autonomous Audit Pipeline</h4>
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              {steps.map((s, i) => (
                <React.Fragment key={s.step}>
                  <PipelineStep label={s.step} status={s.status} timestamp={s.timestamp} />
                  {i < steps.length - 1 && <div style={{ flex: 1, height: 1, background: s.status === 'done' ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.08)', margin: '10px 8px 0' }} />}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Stage 1 & 2: OCR Result & Direct Company/Line-Item Mapping card */}
        {(ocr.supplier_id || ocr.total || ocr.invoice_number) && (
          <div className="glass-card mt-4" style={{ padding: '16px 18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <h4 style={{ fontWeight: 600, fontSize: 13, color: '#ef9976' }}>
                Stage 1 & 2 · OCR Extraction & Direct Procurement Mapping (AI Vendor Search Bypassed)
              </h4>
              <span className="badge badge-green text-xs">
                ✓ High Confidence OCR
              </span>
            </div>
            <div className="grid-cols-2 gap-3 text-xs mb-3">
              {ocr.supplier_id && <div><span className="text-secondary">Company / Supplier (Pre-listed):</span><div className="font-semibold text-primary">{ocr.supplier_id}</div></div>}
              {ocr.invoice_number && <div><span className="text-secondary">Invoice Number:</span><div className="font-semibold text-primary">{ocr.invoice_number}</div></div>}
              {ocr.total && <div><span className="text-secondary">Total Invoice Amount:</span><div className="font-semibold text-primary">{ocr.currency || 'INR'} {Number(ocr.total).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div></div>}
              {ocr.invoice_date && <div><span className="text-secondary">Invoice Date:</span><div className="font-semibold text-primary">{ocr.invoice_date}</div></div>}
              {ocr.tax && <div><span className="text-secondary">Taxes:</span><div className="font-medium">{ocr.currency || 'INR'} {ocr.tax}</div></div>}
              {ocr.delivery && <div><span className="text-secondary">Delivery:</span><div className="font-medium">{ocr.currency || 'INR'} {ocr.delivery}</div></div>}
            </div>

            {/* Extracted line items list */}
            {ocr.items?.length > 0 && (
              <div style={{ marginTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 10 }}>
                <div className="text-xs text-secondary mb-2 font-semibold">
                  Extracted Line Items ({ocr.items.length} item{ocr.items.length !== 1 ? 's' : ''} mapped to {invResult.request_ref})
                </div>
                {ocr.items.map((item, i) => (
                  <div key={i} className="text-xs" style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '7px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 6, marginBottom: 4 }}>
                    <span className="badge text-[10px]" style={{ background: 'rgba(239,153,118,0.18)', color: '#ef9976' }}>{item.sku || `#${i + 1}`}</span>
                    <span className="font-medium text-primary">{item.description || 'Invoice Item'}</span>
                    <span className="text-secondary">Qty: <strong>{item.quantity || 1}</strong></span>
                    <span className="text-secondary">Unit: <strong>{ocr.currency || 'INR'} {Number(item.unit_price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></span>
                    <span className="font-semibold text-accent-primary" style={{ marginLeft: 'auto' }}>
                      {ocr.currency || 'INR'} {(Number(item.quantity || 1) * Number(item.unit_price || 0)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Sourcing Request Created & Dedicated Review Navigation ── */}
        <div className="glass-card mt-4 p-5 border border-border-light" style={{ background: 'linear-gradient(135deg, rgba(34,28,25,0.96) 0%, rgba(22,19,17,0.96) 100%)', borderColor: 'rgba(239,153,118,0.38)', borderRadius: 12 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
            <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'rgba(16,185,129,0.18)', border: '1px solid rgba(16,185,129,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2 }}>
              <CheckCircle size={22} style={{ color: '#10b981' }} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
                <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fafaf9' }}>
                  {mode === 'new' ? 'Sourcing Request Created Successfully' : 'Request Updated with Invoice'}
                </h4>
                <span className="badge" style={{ background: 'rgba(239,153,118,0.2)', color: '#ef9976', border: '1px solid rgba(239,153,118,0.45)', fontWeight: 800, fontSize: 12 }}>
                  {invResult.request_ref || `SR-${String(srId).padStart(4, '0')}`}
                </span>
              </div>
              <p style={{ margin: '0 0 16px 0', fontSize: 13, color: '#d6d3d1', lineHeight: 1.55 }}>
                The request for this invoice has been created: <strong>{invResult.request_ref || `SR-${String(srId).padStart(4, '0')}`} · {invResult.request_title}</strong>.
                Approval notifications were dispatched to each respective authority (Procurement Team, Requesting Department, Legal, Finance, Accounts Payable, IT) in the AuditAI window.
                Open the dedicated review page to inspect itemized mind maps, review authority sign-offs, run the final ML check, and settle payment.
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ background: '#ef9976', color: '#14100c', fontWeight: 800, border: 'none', padding: '10px 20px', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 8 }}
                  onClick={() => navigate(`/procurement/invoice-review/${srId}`)}
                >
                  <span>Open Dedicated Invoice Review &amp; Mind Map</span>
                  <ArrowRight size={15} />
                </button>
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => navigate(`/claims/INV-SR-${String(srId).padStart(4, '0')}`)}
                >
                  View in Claims Ledger →
                </button>
                <button
                  type="button"
                  className="btn btn-secondary text-xs"
                  onClick={() => { setInvResult(null); setInvState('idle'); setFile(null); }}
                >
                  Upload Another Invoice
                </button>
              </div>
            </div>
          </div>
        </div>
      </>)}
    </div>
  );
}
// ── End Invoice Upload Pipeline ───────────────────────────────────────────────


export default function Upload() {
  const [csvUploadState, setCsvUploadState] = useState('idle');
  const [invoiceUploaded, setInvoiceUploaded] = useState(false);
  const [message, setMessage] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [automaticChecks, setAutomaticChecks] = useState(null);
  const [showMaster, setShowMaster] = useState(false);

  const navigate = useNavigate();
  const { user } = useAuth();
  const { profile, companyName, currency } = useAuditProfile();

  const handleCsvUpload = async (file) => {
    setCsvUploadState('uploading');
    setMessage(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await claimsApi.upload(formData);
      setCsvUploadState('complete');setAutomaticChecks(res.data.checks);
      setMessage({ type: 'success', text: res.data.message });
    } catch (err) {
      console.error(err);
      setCsvUploadState('error');
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || (err.response?.status >= 500 ? "The server could not finish importing the claims. Your file may be valid; please retry or contact support." : !err.response ? "Unable to reach the server. Check the connection and try again." : "Upload failed. Check the required columns and row values.")
      });
    }
  };

  const runScoring = async () => {
    setScoring(true);
    setMessage({ type: 'info', text: 'Running Autoencoder + Isolation Forest scoring pipeline...' });
    try {
      const res = await fraudApi.score();
      if (!res.data.scored_count) {
        setMessage({
          type: 'error',
          text: 'No pending claims were found to score. Upload a claims file or attach an invoice first.'
        });
        return;
      }
      setMessage({
        type: 'success',
        text: `Scoring complete! Scored ${res.data.scored_count} claims. Found ${res.data.flagged_count} anomalies.`
      });
      setTimeout(() => navigate('/claims'), 3000);
    } catch (err) {
      console.error(err);
      setMessage({ type: 'error', text: err.response?.data?.detail || "Scoring pipeline failed. Try retraining the model first." });
    } finally {
      setScoring(false);
    }
  };

  return (
    <div className="main-content">
      {/* Header Context */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm text-muted">
          <span>Global Auditing</span>
          <span>/</span>
          <span className="text-secondary font-medium">{companyName} · {currency}</span>
        </div>
        <span
          className="badge text-xs"
          style={{ background: `${profile.color}20`, color: profile.color, border: `1px solid ${profile.color}40` }}
        >
          {profile.name}
        </span>
      </div>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Data Ingestion</h1>
          <p className="text-xs text-secondary mt-1">
            Upload expense batches, attach receipt evidence for OCR, and synchronize reference datasets.
          </p>
        </div>
      </div>

      {message && (
        <div className={`glass-card mb-6 flex items-center p-4 border-l-4 ${message.type === 'error' ? 'border-status-danger' :
            message.type === 'success' ? 'border-status-success' : 'border-accent-primary'
          }`}>
          <span className="text-sm">{message.text}</span>
        </div>
      )}

      {/* ── SECTION 1: Expense Claims CSV ─────────────────────────────────── */}
      <div className="upload-section-card mb-6">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 8 }}>
          <div>
            <h3 id="expense-import" className="upload-section-title">
              1. Upload Expense Claims
              <span className="badge text-xs" style={{ background: 'rgba(239,153,118,0.18)', color: '#ef9976', border: '1px solid rgba(239,153,118,0.35)', marginLeft: 8, verticalAlign: 'middle' }}>Claims CSV</span>
            </h3>
            <p className="upload-section-sub" style={{ marginBottom: 16 }}>
              Upload employee expense claim CSV records for automated compliance screening and ML anomaly scoring.
            </p>
          </div>
          <a
            href="/sample-claims.csv"
            download
            className="btn btn-secondary text-xs"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, textDecoration: 'none', padding: '6px 12px' }}
          >
            <FileText size={13} />
            <span>Download Sample Claims (CSV)</span>
          </a>
        </div>

        <FileUpload
          label="Upload claims.csv or .json"
          accept=".csv,.json"
          onUpload={handleCsvUpload}
          uploadState={csvUploadState}
        />
      </div>

      {/* ── SECTION 2: Invoice & Receipt Upload (Two options: Attach or Standalone) ── */}
      <InvoiceUploadSection onUploaded={() => setInvoiceUploaded(true)} />

      <AutomaticCheckResult checks={automaticChecks}/>

      {/* ── OPTIONAL: Master Reference Data & Ledger Ingestion Toggle ── */}
      {isReviewer(user) && (
        <>
          <div className="glass-card mb-6 flex items-center justify-between p-4 flex-wrap gap-3">
            <div className="flex items-center gap-2.5">
              <Database size={18} className="text-accent-primary" />
              <div>
                <strong className="text-xs text-primary block">Master Reference Data & Ledger Ingestion</strong>
                <span className="text-[11px] text-muted">Upload company ground truth: Vendor Master, Employee Roster, and Payroll Payments.</span>
              </div>
            </div>
            <button
              type="button"
              className="btn btn-secondary text-xs flex items-center gap-1.5"
              onClick={() => setShowMaster(prev => !prev)}
            >
              <span>{showMaster ? 'Hide Master Data Ingestion' : 'Show Master Data Ingestion'}</span>
            </button>
          </div>

          {showMaster && (
            <div className="mb-6">
              <MasterDataImport />
            </div>
          )}
        </>
      )}

      {isReviewer(user) && (csvUploadState === 'complete' || invoiceUploaded) && (
        <div className="glass-card mb-6 flex items-center justify-between gap-5" style={{ padding: '18px 24px' }}>
          <div>
            <h3 className="font-semibold text-sm">Automated screening triggers after upload</h3>
            <p className="text-xs text-secondary mt-0.5">The pipeline combines claim metadata, vendor master checks, and any OCR extraction evidence.</p>
          </div>
          <button className="btn btn-primary text-xs" onClick={runScoring} disabled={scoring}>
            <Play size={15} />
            <span>{scoring ? 'Scoring…' : 'Run Pending Claim Scoring'}</span>
          </button>
        </div>
      )}

      <div className="pipeline-status-card">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-semibold" style={{ margin: 0 }}>End-to-End Ingestion Pipeline</h3>
            <p className="text-xs text-secondary mt-1">Multi-stage autonomous audit processing pipeline status.</p>
          </div>
          <span className="badge text-xs" style={{ background: 'rgba(239,153,118,0.15)', color: '#ef9976', border: '1px solid rgba(239,153,118,0.3)' }}>Active Engine</span>
        </div>
        <div className="pipeline-steps-grid">
          {[
            { num: 1, label: 'Data Ingestion', sub: 'CSV & Ledger sync', state: csvUploadState === 'complete' ? 'complete' : 'ready' },
            { num: 2, label: 'OCR Extraction', sub: 'Field & amount parsing', state: invoiceUploaded ? 'complete' : 'ready' },
            { num: 3, label: 'Feature Engineering', sub: 'Anomaly indicator build', state: (csvUploadState === 'complete' || invoiceUploaded) ? 'ready' : 'standby' },
            { num: 4, label: 'ML Scoring', sub: 'Fraud & risk inference', state: (csvUploadState === 'complete' || invoiceUploaded) ? 'ready' : 'standby' },
          ].map(s => (
            <div key={s.num} className={`pipeline-step-item ${s.state}`}>
              <div className="step-num">{s.state === 'complete' ? '✓' : `0${s.num}`}</div>
              <div className="step-info">
                <span className="step-title">{s.label}</span>
                <span className="step-sub">{s.sub}</span>
              </div>
              <span className={`step-badge ${s.state}`}>{s.state === 'complete' ? 'Complete' : s.state === 'ready' ? 'Ready' : 'Pending'}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
