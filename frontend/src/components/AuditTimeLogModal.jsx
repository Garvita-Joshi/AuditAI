import React, { useState, useEffect } from 'react';
import {
  Clock, X, Search, ShieldCheck, Mail, Send, Award, FileText, CheckCircle2,
  AlertTriangle, RefreshCw, Copy, Check, Download, ArrowUpRight, DollarSign,
  TrendingDown, FileSpreadsheet, Bot, UserCheck
} from 'lucide-react';
import { sourcingApi, procurementApi } from '../api/client';
import './AuditTimeLogModal.css';

const ACTION_CONFIG = {
  request_created: {
    label: 'Purchase Request Created',
    icon: FileText,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    category: 'lifecycle'
  },
  request_edited: {
    label: 'Intake Brief & Requirements Updated',
    icon: FileSpreadsheet,
    color: '#94a3b8',
    bg: 'rgba(148, 163, 184, 0.12)',
    category: 'lifecycle'
  },
  workflow_plan_generated: {
    label: 'Approval Workflow Mind Map Generated',
    icon: ShieldCheck,
    color: '#c084fc',
    bg: 'rgba(192, 132, 252, 0.12)',
    category: 'workflow'
  },
  contract_document_uploaded: {
    label: 'Contract Agreement Uploaded',
    icon: FileText,
    color: '#60a5fa',
    bg: 'rgba(96, 165, 250, 0.12)',
    category: 'contracts'
  },
  sourcing_agent_started: {
    label: 'Autonomous AI Sourcing Run Initiated',
    icon: Bot,
    color: '#ef9976',
    bg: 'rgba(239, 153, 118, 0.14)',
    category: 'outreach'
  },
  shortlist_ranked: {
    label: 'Suppliers Evaluated & Shortlisted',
    icon: UserCheck,
    color: '#ef9976',
    bg: 'rgba(239, 153, 118, 0.14)',
    category: 'outreach'
  },
  rfq_drafts_prepared: {
    label: 'Formal RFQ Drafts Prepared for Dispatch',
    icon: Mail,
    color: '#f5d0bc',
    bg: 'rgba(245, 208, 188, 0.12)',
    category: 'outreach'
  },
  rfq_batch_sent: {
    label: 'RFQ Batch Dispatched via SMTP',
    icon: Send,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    category: 'outreach'
  },
  rfq_sent: {
    label: 'RFQ Email Dispatched to Vendor',
    icon: Send,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    category: 'outreach'
  },
  rfq_send_failed: {
    label: 'RFQ Send Failed (SMTP Rejected)',
    icon: AlertTriangle,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.14)',
    category: 'outreach'
  },
  rfq_contact_required: {
    label: 'Vendor Contact Verification Required',
    icon: AlertTriangle,
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.12)',
    category: 'outreach'
  },
  rfq_follow_up_sent: {
    label: 'Autonomous Vendor Follow-Up Sent',
    icon: Mail,
    color: '#f5d0bc',
    bg: 'rgba(245, 208, 188, 0.12)',
    category: 'outreach'
  },
  vendor_reply_recorded: {
    label: 'Quotation Received & Terms Extracted',
    icon: CheckCircle2,
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.12)',
    category: 'negotiation'
  },
  vendor_quote_declined: {
    label: 'Vendor Declined RFQ Opportunity',
    icon: AlertTriangle,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.12)',
    category: 'negotiation'
  },
  clarification_auto_dispatched: {
    label: 'Commercial Clarification Auto-Dispatched',
    icon: Mail,
    color: '#fbbf24',
    bg: 'rgba(251, 191, 36, 0.12)',
    category: 'negotiation'
  },
  no_negotiation_decided: {
    label: 'AI Policy: Optimal Quote (No Neg Needed)',
    icon: CheckCircle2,
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.12)',
    category: 'negotiation'
  },
  auto_counteroffer_sent: {
    label: 'Round 1 AI Policy Counteroffer Sent',
    icon: TrendingDown,
    color: '#ef9976',
    bg: 'rgba(239, 153, 118, 0.14)',
    category: 'negotiation'
  },
  round_2_counteroffer_approved_and_sent: {
    label: 'Round 2 BAFO Approved by Human & Sent',
    icon: Award,
    color: '#ef9976',
    bg: 'rgba(239, 153, 118, 0.18)',
    category: 'negotiation'
  },
  counteroffer_response_analyzed: {
    label: 'Vendor Counteroffer Response Evaluated',
    icon: TrendingDown,
    color: '#c084fc',
    bg: 'rgba(192, 132, 252, 0.12)',
    category: 'negotiation'
  },
  purchase_order_authorized: {
    label: 'Purchase Order (PO) Formally Authorized',
    icon: Award,
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.16)',
    category: 'contracts'
  },
  final_invoice_recorded: {
    label: 'Final Supplier Invoice Recorded',
    icon: FileText,
    color: '#60a5fa',
    bg: 'rgba(96, 165, 250, 0.12)',
    category: 'invoice_ml'
  },
  invoice_uploaded: {
    label: 'Supplier Invoice Document Uploaded',
    icon: FileText,
    color: '#60a5fa',
    bg: 'rgba(96, 165, 250, 0.12)',
    category: 'invoice_ml'
  },
  invoice_ocr_extracted: {
    label: 'Invoice OCR & Multimodal Parsing Complete',
    icon: CheckCircle2,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    category: 'invoice_ml'
  },
  ml_fraud_evaluated: {
    label: 'ML Fraud Anomaly Detection Evaluated',
    icon: ShieldCheck,
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.14)',
    category: 'invoice_ml'
  },
  paypal_sandbox_checkout_created: {
    label: 'PayPal Sandbox Payment Order Created',
    icon: DollarSign,
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
    category: 'payment'
  },
  paypal_sandbox_payment_captured: {
    label: 'PayPal Payment Settled & Reconciled',
    icon: CheckCircle2,
    color: '#4ade80',
    bg: 'rgba(74, 222, 128, 0.18)',
    category: 'payment'
  },
  request_permanently_deleted: {
    label: 'Request Permanently Deleted',
    icon: AlertTriangle,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.2)',
    category: 'lifecycle'
  },
  restore_blocked: {
    label: 'Restoration Attempt Blocked',
    icon: AlertTriangle,
    color: '#f87171',
    bg: 'rgba(248, 113, 113, 0.15)',
    category: 'lifecycle'
  }
};

const CATEGORIES = [
  { id: 'all', label: 'All Events' },
  { id: 'outreach', label: 'RFQs & Outreach' },
  { id: 'negotiation', label: 'Quotes & Negotiations' },
  { id: 'contracts', label: 'POs & Agreements' },
  { id: 'invoice_ml', label: 'ML Risk & Invoices' },
  { id: 'payment', label: 'Settlement & PayPal' }
];

function formatLogRelativeTime(timestamp) {
  if (!timestamp) return 'Just now';
  try {
    const d = new Date(String(timestamp).endsWith('Z') ? timestamp : `${timestamp}Z`);
    const diffMs = Date.now() - d.getTime();
    if (diffMs < 0 || isNaN(diffMs)) return 'Just now';
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return '1 day ago';
    if (days < 7) return `${days} days ago`;
    const weeks = Math.floor(days / 7);
    return `${weeks}w ago`;
  } catch {
    return 'Recently';
  }
}

export default function AuditTimeLogModal({
  requestId,
  requestKind = 'sourcing',
  requestTitle,
  initialAuditLog = null,
  onClose
}) {
  const [logs, setLogs] = useState(initialAuditLog || []);
  const [loading, setLoading] = useState(!initialAuditLog);
  const [error, setError] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');
  const [expandedCardId, setExpandedCardId] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchLogs = async () => {
    if (!requestId) return;
    setLoading(true);
    setError(null);
    try {
      const res = requestKind === 'procurement'
        ? await procurementApi.auditLog(requestId)
        : await sourcingApi.auditLog(requestId);
      const data = res?.data || res;
      setLogs(data.audit_log || data.timeline || []);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load audit logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [requestId, requestKind]);

  // Handle escape key
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleCopy = () => {
    const text = logs.map((l, idx) => {
      const cfg = ACTION_CONFIG[l.action] || { label: l.action.replaceAll('_', ' ') };
      const actor = l.actor || l.details?.actor || `User #${l.actor_id || 1}`;
      const time = l.log_time || l.timestamp;
      const details = l.details ? JSON.stringify(l.details) : '';
      return `[${time}] #${idx + 1} ${cfg.label.toUpperCase()} (${l.action})\nActor: ${actor}\nDetails: ${details}\n`;
    }).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const payload = {
      request_id: requestId,
      kind: requestKind,
      title: requestTitle,
      exported_at: new Date().toISOString(),
      events_count: logs.length,
      audit_log: logs
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AuditAI_AuditLog_${requestKind.toUpperCase()}-${String(requestId).padStart(4, '0')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredLogs = logs.filter(item => {
    const cfg = ACTION_CONFIG[item.action] || { label: item.action, category: 'lifecycle' };
    if (filterCategory !== 'all' && cfg.category !== filterCategory) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      const matchAction = item.action.toLowerCase().includes(q) || cfg.label.toLowerCase().includes(q);
      const matchActor = String(item.actor || item.details?.actor || '').toLowerCase().includes(q);
      const matchDetails = JSON.stringify(item.details || {}).toLowerCase().includes(q);
      const matchTime = String(item.log_time || item.timestamp || '').toLowerCase().includes(q);
      return matchAction || matchActor || matchDetails || matchTime;
    }
    return true;
  });

  const sortedLogs = [...filteredLogs].sort((a, b) => {
    const timeA = new Date(a.timestamp || a.log_time || 0).getTime();
    const timeB = new Date(b.timestamp || b.log_time || 0).getTime();
    return sortOrder === 'newest' ? timeB - timeA : timeA - timeB;
  });

  const quoteId = `${requestKind.toUpperCase()}-${String(requestId).padStart(4, '0')}`;
  const firstLog = logs[0];
  const createdDate = firstLog?.timestamp || firstLog?.log_time;
  const createdDateFormatted = createdDate
    ? new Date(createdDate).toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' })
    : '11.12.2026';

  const amountEntry = logs.find(l => l.details?.amount || l.details?.total_price || l.details?.stated_total);
  const displayAmount = amountEntry?.details?.total_price || amountEntry?.details?.stated_total || amountEntry?.details?.amount;
  const currencySymbol = amountEntry?.details?.currency === 'USD' ? '$' : '₹';
  const displayPrice = displayAmount ? `${currencySymbol}${Number(displayAmount).toLocaleString()}` : 'Budget Cap';

  const getStageMeta = (action, category, details) => {
    const act = (action || '').toLowerCase();
    if (act.includes('created') || act.includes('intake')) return { title: 'Intake Requisition', sub: details?.actor || 'Requester' };
    if (act.includes('outreach') || act.includes('rfq') || act.includes('agent_started')) return { title: 'Commercial Outreach', sub: 'SMTP Dispatch' };
    if (act.includes('reply') || act.includes('quoted') || act.includes('quotation')) return { title: 'Quotation Received', sub: 'Vendor Reply' };
    if (act.includes('counter') || act.includes('negotiat') || act.includes('discount')) return { title: 'Commercial Negotiation', sub: 'Counteroffer' };
    if (act.includes('winner') || act.includes('po_') || act.includes('award')) return { title: 'PO Award & Commit', sub: 'Decision Finalized' };
    if (act.includes('invoice') || act.includes('ocr') || act.includes('ml')) return { title: 'Fraud Verification', sub: 'ML Evaluation' };
    if (act.includes('payment') || act.includes('paypal') || act.includes('settle')) return { title: 'B2B Settlement', sub: 'PayPal Sandbox' };
    return { title: category ? category.charAt(0).toUpperCase() + category.slice(1) : 'Milestone', sub: 'Audit Event' };
  };

  return (
    <div className="atl-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="atl-modal-card" onClick={e => e.stopPropagation()}>
        {/* Top Header */}
        <header className="atl-header">
          <div className="atl-header-left">
            <div className="atl-icon-badge">
              <Clock size={20} color="#ef9976" />
            </div>
            <div>
              <div className="atl-title-row">
                <h2>Immutable Audit Time Log Trail</h2>
                <span className="atl-count-chip">{logs.length} Events</span>
              </div>
              <p className="atl-sub">
                {requestKind.toUpperCase()}-{String(requestId).padStart(4, '0')} · {requestTitle || 'Purchase Requisition'} · All timestamps recorded in UTC
              </p>
            </div>
          </div>
          <div className="atl-header-actions">
            <button
              type="button"
              className="atl-btn atl-btn-secondary"
              onClick={fetchLogs}
              disabled={loading}
              title="Refresh log entries"
            >
              <RefreshCw size={13} className={loading ? 'atl-spinning' : ''} />
              <span>Refresh</span>
            </button>
            <button
              type="button"
              className="atl-btn atl-btn-secondary"
              onClick={handleCopy}
              title="Copy formatted audit log to clipboard"
            >
              {copied ? <Check size={13} color="#4ade80" /> : <Copy size={13} />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </button>
            <button
              type="button"
              className="atl-btn atl-btn-secondary"
              onClick={handleDownload}
              title="Export complete audit ledger as JSON"
            >
              <Download size={13} />
              <span>Export</span>
            </button>
            <button
              type="button"
              className="atl-close-btn"
              onClick={onClose}
              aria-label="Close audit log"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* Top Summary Metric Cards */}
        <div className="atl-summary-cards">
          <div className="atl-summary-card">
            <div className="atl-summary-val">{quoteId}</div>
            <div className="atl-summary-lbl">quote id</div>
          </div>
          <div className="atl-summary-card">
            <div className="atl-summary-val">{createdDateFormatted}</div>
            <div className="atl-summary-lbl">created</div>
          </div>
          <div className="atl-summary-card">
            <div className="atl-summary-val">{logs.length} events</div>
            <div className="atl-summary-lbl">milestones</div>
          </div>
          <div className="atl-summary-card">
            <div className="atl-summary-val">{displayPrice}</div>
            <div className="atl-summary-lbl">price estimate</div>
          </div>
        </div>

        {/* Toolbar: Search + Category Filter Tabs */}
        <div className="atl-toolbar">
          <div className="atl-search-wrap">
            <Search size={14} className="atl-search-icon" />
            <input
              type="search"
              placeholder="Search audit trail by vendor, action, amount, PO number, or actor..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              aria-label="Filter audit logs"
            />
            {searchQuery && (
              <button
                type="button"
                className="atl-search-clear"
                onClick={() => setSearchQuery('')}
              >
                Clear
              </button>
            )}
          </div>

          <div className="atl-filter-tabs">
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                type="button"
                className={`atl-tab-btn ${filterCategory === cat.id ? 'active' : ''}`}
                onClick={() => setFilterCategory(cat.id)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Body */}
        <div className="atl-body">
          {error && (
            <div className="atl-error-banner" role="alert">
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {loading && logs.length === 0 ? (
            <div className="atl-loading-state">
              <RefreshCw size={24} className="atl-spinning" color="#8b5cf6" />
              <p>Loading chronological audit events from immutable ledger…</p>
            </div>
          ) : sortedLogs.length === 0 ? (
            <div className="atl-empty-state">
              <Clock size={32} color="#94a3b8" />
              <h4>No Audit Events Match Filter</h4>
              <p>{searchQuery ? `No logs found matching "${searchQuery}". Clear your search query to see all records.` : 'No events recorded in this category yet.'}</p>
            </div>
          ) : (
            <div className="atl-board-list">
              <div className="atl-subbar">
                <span className="atl-count-found">
                  We've found <strong>{sortedLogs.length}</strong> audit milestones
                </span>
                <button
                  type="button"
                  className="atl-sort-btn"
                  onClick={() => setSortOrder(o => o === 'newest' ? 'oldest' : 'newest')}
                >
                  Sort by: <strong>{sortOrder === 'newest' ? 'Date (Newest)' : 'Date (Oldest)'}</strong> ▾
                </button>
              </div>

              {sortedLogs.map((log, index) => {
                const cfg = ACTION_CONFIG[log.action] || {
                  label: log.action.replaceAll('_', ' '),
                  icon: Clock,
                  color: '#8b5cf6',
                  bg: '#f5f3ff',
                  category: 'lifecycle'
                };
                const Icon = cfg.icon;
                const details = log.details || {};
                const actorName = log.actor || details.actor || (log.actor_id === 1 ? 'Autonomous AI Agent' : `User #${log.actor_id}`);
                const formattedTime = log.log_time || (log.timestamp ? new Date(log.timestamp).toUTCString() : '—');
                const relativeTimeStr = formatLogRelativeTime(log.timestamp || log.log_time);
                const stageMeta = getStageMeta(log.action, cfg.category, details);

                const cardId = log.id || `${log.action}-${index}`;
                const isExpanded = expandedCardId === cardId;

                let displayMetric = stageMeta.title;
                if (details.total_price || details.stated_total || details.amount) {
                  const amt = Number(details.total_price || details.stated_total || details.amount);
                  displayMetric = new Intl.NumberFormat('en-IN', { style: 'currency', currency: details.currency || 'INR', maximumFractionDigits: 0 }).format(amt);
                } else if (details.po_number) {
                  displayMetric = `PO #${details.po_number}`;
                } else if (details.invoice_number) {
                  displayMetric = `INV #${details.invoice_number}`;
                } else if (details.score != null) {
                  displayMetric = `${(details.score * 100).toFixed(0)}% Score`;
                }

                return (
                  <div
                    key={cardId}
                    className={`atl-board-card ${isExpanded ? 'active-highlight' : ''}`}
                    onClick={() => setExpandedCardId(isExpanded ? null : cardId)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpandedCardId(isExpanded ? null : cardId); } }}
                  >
                    <div className="atl-card-main-row">
                      <div className="atl-card-left">
                        <div
                          className="atl-card-brand-box"
                          style={{ background: cfg.bg, color: cfg.color }}
                        >
                          <Icon size={24} strokeWidth={2.3} />
                        </div>
                        <div className="atl-card-center-col">
                          <div className="atl-card-title-row">
                            <h4 className="atl-card-title">{cfg.label}</h4>
                            <span className="atl-pill-category">{cfg.category}</span>
                            {details.automatic && <span className="atl-pill-auto">Autonomous AI</span>}
                            {details.vendor && <span className="atl-pill-vendor">{details.vendor}</span>}
                          </div>
                          <div className="atl-card-sub-row">
                            <span className="atl-actor-txt">{actorName}</span>
                            <span className="atl-sub-dot">—</span>
                            <span className="atl-stage-txt">{stageMeta.title}</span>
                            {details.po_number && (
                              <>
                                <span className="atl-sub-dot">•</span>
                                <span className="atl-po-txt">PO #{details.po_number}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="atl-card-right">
                        <div className="atl-card-metric">
                          {displayMetric}
                        </div>
                        <div className="atl-card-timeago">
                          {relativeTimeStr}
                        </div>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="atl-card-drawer" onClick={e => e.stopPropagation()}>
                        <div className="atl-drawer-grid">
                          <div className="atl-drawer-cell">
                            <small>Exact UTC Timestamp</small>
                            <strong>{formattedTime}</strong>
                          </div>
                          <div className="atl-drawer-cell">
                            <small>Action Code</small>
                            <code>{log.action}</code>
                          </div>
                          {details.vendor && (
                            <div className="atl-drawer-cell">
                              <small>Supplier</small>
                              <strong>{details.vendor}</strong>
                            </div>
                          )}
                          {details.email && (
                            <div className="atl-drawer-cell">
                              <small>Email Dispatch</small>
                              <strong>{details.email}</strong>
                            </div>
                          )}
                          {(details.total_price || details.stated_total || details.amount) && (
                            <div className="atl-drawer-cell">
                              <small>Recorded Total</small>
                              <strong style={{ color: '#ff5722' }}>
                                {details.currency || 'INR'} {Number(details.total_price || details.stated_total || details.amount).toLocaleString()}
                              </strong>
                            </div>
                          )}
                          {details.score != null && (
                            <div className="atl-drawer-cell">
                              <small>ML Anomaly Score</small>
                              <strong style={{ color: details.is_fraud ? '#f87171' : '#10b981' }}>
                                {(details.score * 100).toFixed(1)}% ({details.fraud_decision || (details.is_fraud ? 'FLAGGED' : 'CLEAN')})
                              </strong>
                            </div>
                          )}
                        </div>

                        {(details.note || details.reasoning || details.recommendation || details.error) && (
                          <p className={`atl-note ${details.error ? 'is-error' : ''}`}>
                            {details.error ? `Error: ${details.error}` : (details.note || details.reasoning || details.recommendation)}
                          </p>
                        )}

                        <details className="atl-raw-details">
                          <summary>View Cryptographic Payload</summary>
                          <pre>{JSON.stringify(details, null, 2)}</pre>
                        </details>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="atl-footer">
          <div className="atl-footer-note">
            <ShieldCheck size={14} color="#ef9976" />
            <span>Immutable Ledger · All events append-only with microsecond UTC resolution and tamper-evident audit keys.</span>
          </div>
          <button type="button" className="atl-btn atl-btn-primary" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}

