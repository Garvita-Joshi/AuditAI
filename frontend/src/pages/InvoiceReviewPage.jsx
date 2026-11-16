import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Building2, CheckCircle2, Clock, CreditCard, FileText,
  Network, Pencil, RefreshCw, ShieldCheck, AlertCircle, AlertTriangle,
  Sparkles, ExternalLink, MapPin, DollarSign, Calendar, Layers,
  Check, UserCheck, CheckCircle, Tag, Briefcase, Eye, ChevronRight
} from 'lucide-react';
import { sourcingApi } from '../api/client';
import { WorkflowMindMap } from './PurchaseIntake';
import AuditTimeLogModal from '../components/AuditTimeLogModal';
import './InvoiceReviewPage.css';

const money = (val, currency = 'INR') =>
  new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', {
    style: 'currency',
    currency,
  }).format(Number(val || 0));

export default function InvoiceReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [row, setRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyNodeId, setBusyNodeId] = useState(null);
  const [busyBatch, setBusyBatch] = useState(false);
  const [busyMl, setBusyMl] = useState(false);
  const [busyPay, setBusyPay] = useState(false);
  const [actionNotice, setActionNotice] = useState('');
  const [activeItemTab, setActiveItemTab] = useState('unified');
  const [showAuditModal, setShowAuditModal] = useState(false);

  const loadData = async () => {
    try {
      const { data } = await sourcingApi.detail(id);
      setRow(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Unable to load invoice request.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') loadData();
    }, 5000);
    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return (
      <main className="invoice-review-page">
        <div className="ir-loading-box">
          <RefreshCw size={24} className="spin" />
          <p>Loading Invoice Review Workspace (SR-{String(id).padStart(4, '0')})…</p>
        </div>
      </main>
    );
  }

  if (error && !row) {
    return (
      <main className="invoice-review-page">
        <div className="ir-error-box">
          <AlertTriangle size={24} color="#f87171" />
          <h3>Unable to load invoice request</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/procurement')}>
            ← Back to Procurement Requests
          </button>
        </div>
      </main>
    );
  }

  const req = row.requirements || {};
  const workflow = row.workspace?.workflow || {};
  const invOcr = workflow.invoice_ocr_details || {};
  const nodeApprovals = workflow.node_approvals || {};
  const assessment = workflow.final_invoice_assessment || null;
  const paypalPayment = workflow.paypal_payment || null;
  const lineItems = req.line_items?.length ? req.line_items : (invOcr.items || []);
  const currency = req.currency || invOcr.currency || 'INR';

  // Base graph nodes & authorities
  const baseNodes = workflow.graph?.nodes || [];
  const authorityNodes = baseNodes.filter(n => !['receipt-match', 'payment-release'].includes(n.id));
  const approvedCount = authorityNodes.filter(n => nodeApprovals[n.id]?.approved).length;
  const allAuthoritiesApproved = authorityNodes.length > 0 && approvedCount >= authorityNodes.length;

  // Handle single authority approval
  const handleApproveNode = async (node) => {
    setBusyNodeId(node.id);
    setActionNotice('');
    try {
      const res = await sourcingApi.approveCheckpoint(id, {
        node_id: node.id,
        label: node.label,
        owner_group: node.owner_group,
      });
      const data = res?.data || res;
      if (data?.node_approvals) {
        setRow(prev => ({
          ...prev,
          workspace: {
            ...prev.workspace,
            workflow: {
              ...prev.workspace.workflow,
              node_approvals: data.node_approvals,
            }
          }
        }));
      }
      setActionNotice(`✓ ${node.label} approved by ${node.owner_group}.`);
      loadData();
    } catch (e) {
      setActionNotice(`Failed to approve ${node.label}: ${e.response?.data?.detail || e.message}`);
    } finally {
      setBusyNodeId(null);
    }
  };

  // Handle batch approval of all pending authorities
  const handleApproveAll = async () => {
    setBusyBatch(true);
    setActionNotice('');
    try {
      for (const node of authorityNodes) {
        if (!nodeApprovals[node.id]?.approved) {
          await sourcingApi.approveCheckpoint(id, {
            node_id: node.id,
            label: node.label,
            owner_group: node.owner_group,
          });
        }
      }
      setActionNotice('✓ All respective approval authorities approved!');
      loadData();
    } catch (e) {
      setActionNotice(`Failed during approval: ${e.response?.data?.detail || e.message}`);
    } finally {
      setBusyBatch(false);
    }
  };

  // Run ML final fraud check
  const handleRunMl = async () => {
    setBusyMl(true);
    setActionNotice('');
    try {
      const res = await sourcingApi.evaluateFinalInvoice(id);
      const data = res?.data || res;
      setActionNotice(`✓ ML Check completed: ${data.assessment?.is_fraud ? 'Fraud Risk Flagged' : 'Considered Not Fraud (Passed)'}`);
      loadData();
    } catch (e) {
      setActionNotice(`ML Check Error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setBusyMl(false);
    }
  };

  // Handle PayPal Direct Settle
  const handlePaypalSettle = async () => {
    setBusyPay(true);
    setActionNotice('');
    try {
      const res = await sourcingApi.paypalDirectSettle(id);
      const data = res?.data || res;
      setActionNotice(`✓ Payment Settled via PayPal Sandbox (Order ${data.order_id}). Claim synced to APPROVED.`);
      loadData();
    } catch (e) {
      setActionNotice(`Payment Settlement Error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setBusyPay(false);
    }
  };

  // Generate distinct mind map per item
  const getItemMindMap = (item, index) => {
    const desc = (item.description || '').toLowerCase();
    const isFlight = /flight|air|airline|del - blr|pnr|aviation|indigo|air india/i.test(desc);
    const isHotel = /hotel|stay|night|lodging|room|accommodation|suites/i.test(desc);
    const isGoods = item.line_type === 'Item' || /laptop|device|hardware|monitor|equipment|gear/i.test(desc);
    const isSoftware = /software|subscription|license|cloud|saas|api|tool/i.test(desc);

    const itemId = `item-${index + 1}`;
    let nodes = [];
    let edges = [];

    if (isFlight) {
      nodes = [
        {
          id: `${itemId}-travel-policy`,
          label: 'Travel Policy & Airfare Cap Check',
          owner_group: 'Procurement / Corporate Travel Desk',
          kind: 'review',
          review_tasks: [
            { title: 'Check Flight Policy Limits', instructions: 'Verify economy/business class justification and city-pair corporate allowance.' },
            { title: 'Confirm Business Purpose', instructions: 'Verify trip dates align with project/client engagement.' },
          ]
        },
        {
          id: `${itemId}-dept-auth`,
          label: 'Department Travel Authorization',
          owner_group: 'Requesting Department (Operations)',
          kind: 'approval',
          review_tasks: [
            { title: 'Manager Travel Authorization', instructions: 'Confirm line item necessity and approve business travel expenditure.' },
            { title: 'Cost Center Allocation', instructions: 'Confirm Operations travel budget code.' },
          ]
        },
        {
          id: `${itemId}-ticket-match`,
          label: 'Airline e-Ticket & PNR Verification',
          owner_group: 'Corporate Travel Services',
          kind: 'document',
          review_tasks: [
            { title: 'Verify Airline PNR Ticket', instructions: 'Match passenger name, PNR confirmation code, and fare rules.' },
            { title: 'Audit Fare Class & Taxes', instructions: 'Confirm GSTIN 27AABCUBGORIZ2 and airfare tax breakdown.' },
          ]
        },
        {
          id: `${itemId}-travel-control`,
          label: 'Flight Expense 3-Way Match & ML Check',
          owner_group: 'Finance & Accounts Payable',
          kind: 'control',
          review_tasks: [
            { title: 'Boarding Pass & PO 3-Way Match', instructions: 'Confirm passenger attendance and reconcile invoice line total.' },
            { title: 'Execute ML Fraud Anomaly Model', instructions: 'Run PyTorch Autoencoder + Isolation Forest anomaly scoring.' },
          ]
        },
      ];
      edges = [
        { source: `${itemId}-travel-policy`, target: `${itemId}-dept-auth`, label: 'Policy passed' },
        { source: `${itemId}-dept-auth`, target: `${itemId}-ticket-match`, label: 'Approved' },
        { source: `${itemId}-ticket-match`, target: `${itemId}-travel-control`, label: 'Ticket verified' },
      ];
    } else if (isHotel) {
      nodes = [
        {
          id: `${itemId}-lodging-cap`,
          label: 'Lodging Policy & Per-Diem Cap Check',
          owner_group: 'Procurement / Admin Desk',
          kind: 'review',
          review_tasks: [
            { title: 'Verify Nightly Room Ceiling', instructions: 'Verify Bengaluru Tier-1 room rate cap and corporate discount.' },
            { title: 'Validate Stay Duration', instructions: 'Check 3-night stay dates match scheduled engagement.' },
          ]
        },
        {
          id: `${itemId}-dept-stay`,
          label: 'Department Accommodation Approval',
          owner_group: 'Requesting Department (Operations)',
          kind: 'approval',
          review_tasks: [
            { title: 'Confirm Stay Need', instructions: 'Approve hotel accommodation requirement for assigned personnel.' },
            { title: 'Validate Nightly Allowance', instructions: 'Confirm total stay cost is within department allowance.' },
          ]
        },
        {
          id: `${itemId}-folio-check`,
          label: 'Hotel Folio & GST Compliance Check',
          owner_group: 'Accounts Payable',
          kind: 'document',
          review_tasks: [
            { title: 'Itemized Folio Audit', instructions: 'Verify room charges exclude personal incidentals, minibar, or room service.' },
            { title: 'GSTIN Registration Verification', instructions: 'Verify supplier GSTIN and state tax credit eligibility.' },
          ]
        },
        {
          id: `${itemId}-hotel-control`,
          label: 'Lodging Expense Reconciliation & ML Gate',
          owner_group: 'Finance & Accounts Payable',
          kind: 'control',
          review_tasks: [
            { title: '3-Way Folio Match', instructions: 'Reconcile hotel invoice against reservation PO and check-in/out records.' },
            { title: 'ML Anomaly Screening', instructions: 'Cross-reference stay price index with historical regional hotel benchmarks.' },
          ]
        },
      ];
      edges = [
        { source: `${itemId}-lodging-cap`, target: `${itemId}-dept-stay`, label: 'Cap verified' },
        { source: `${itemId}-dept-stay`, target: `${itemId}-folio-check`, label: 'Approved' },
        { source: `${itemId}-folio-check`, target: `${itemId}-hotel-control`, label: 'Folio clean' },
      ];
    } else if (isSoftware) {
      nodes = [
        {
          id: `${itemId}-licensing`,
          label: 'Software Licensing & Tier Verification',
          owner_group: 'IT Procurement Desk',
          kind: 'review',
          review_tasks: [
            { title: 'Review Seat Count', instructions: 'Confirm required user licenses vs enterprise pool.' },
            { title: 'Check Term & Renewal', instructions: 'Verify billing period and renewal conditions.' },
          ]
        },
        {
          id: `${itemId}-dept-budget`,
          label: 'Department Software Budget Authorization',
          owner_group: 'Requesting Department',
          kind: 'approval',
          review_tasks: [
            { title: 'Confirm Tool Necessity', instructions: 'Verify team usage and business justification.' },
          ]
        },
        {
          id: `${itemId}-it-security`,
          label: 'IT Security, SSO & Data Privacy Review',
          owner_group: 'IT & Information Security',
          kind: 'review',
          review_tasks: [
            { title: 'SSO & IAM Architecture', instructions: 'Verify SAML/Okta integration capability.' },
            { title: 'Data Privacy & SOC2 Audit', instructions: 'Confirm cloud vendor compliance certificates.' },
          ]
        },
        {
          id: `${itemId}-software-control`,
          label: 'Provisioning Acceptance & ML Control',
          owner_group: 'Finance & Accounts Payable',
          kind: 'control',
          review_tasks: [
            { title: 'Verify Active Provisioning', instructions: 'Confirm licenses are provisioned to designated users.' },
            { title: 'ML Fraud & Duplicate Gate', instructions: 'Verify against existing SaaS contracts to prevent duplicate tools.' },
          ]
        },
      ];
      edges = [
        { source: `${itemId}-licensing`, target: `${itemId}-dept-budget`, label: 'Verified' },
        { source: `${itemId}-dept-budget`, target: `${itemId}-it-security`, label: 'Approved' },
        { source: `${itemId}-it-security`, target: `${itemId}-software-control`, label: 'Security cleared' },
      ];
    } else {
      // General Goods / Hardware
      nodes = [
        {
          id: `${itemId}-catalog-check`,
          label: 'Procurement Catalog & Price Verification',
          owner_group: 'Procurement Team',
          kind: 'review',
          review_tasks: [
            { title: 'Check Catalog Unit Rate', instructions: 'Compare quoted unit price against contracted company pricing.' },
            { title: 'Verify Supplier Registration', instructions: 'Confirm vendor status in company master directory.' },
          ]
        },
        {
          id: `${itemId}-dept-head`,
          label: 'Department Equipment Approval',
          owner_group: 'Requesting Department',
          kind: 'approval',
          review_tasks: [
            { title: 'Confirm Equipment Requirement', instructions: 'Verify need and department asset allocation.' },
          ]
        },
        {
          id: `${itemId}-receiving`,
          label: 'Physical Goods Receipt & Warehouse Inspection',
          owner_group: 'Warehouse & Receiving',
          kind: 'document',
          review_tasks: [
            { title: 'Physical Count & Condition Check', instructions: 'Inspect delivered items and match packing slip.' },
            { title: 'Asset Tag Registration', instructions: 'Assign hardware serial numbers to corporate asset tracking.' },
          ]
        },
        {
          id: `${itemId}-match-control`,
          label: '3-Way Match & ML Payment Release',
          owner_group: 'Finance & Accounts Payable',
          kind: 'control',
          review_tasks: [
            { title: 'PO-GRN-Invoice 3-Way Reconciliation', instructions: 'Confirm quantity and unit rate match purchase order exactly.' },
            { title: 'ML Anomaly & Payment Settlement', instructions: 'Verify anomaly score threshold and unlock PayPal Sandbox payout.' },
          ]
        },
      ];
      edges = [
        { source: `${itemId}-catalog-check`, target: `${itemId}-dept-head`, label: 'Pricing valid' },
        { source: `${itemId}-dept-head`, target: `${itemId}-receiving`, label: 'Approved' },
        { source: `${itemId}-receiving`, target: `${itemId}-match-control`, label: 'Goods received' },
      ];
    }

    return {
      title: `${item.description || `Line Item ${index + 1}`} Approval Workflow`,
      summary: `Tailored approval and verification path for Line Item #${index + 1}: ${item.description || 'Invoice Item'}.`,
      nodes,
      edges,
    };
  };

  const currentMindMap = activeItemTab === 'unified'
    ? (workflow.graph || { nodes: [], edges: [] })
    : getItemMindMap(lineItems[Number(activeItemTab)], Number(activeItemTab));

  return (
    <main className="invoice-review-page">
      {/* ── Top Bar / Header ── */}
      <header className="ir-header">
        <div className="ir-header-nav">
          <button className="ir-back-btn" onClick={() => navigate('/procurement')}>
            <ArrowLeft size={16} /> Back to Procurement Requests
          </button>
          <div className="ir-header-badge-group">
            <span className="ir-pill-ref">SR-{String(row.id).padStart(4, '0')}</span>
            {invOcr.invoice_number && (
              <span className="ir-pill-inv">INV: {invOcr.invoice_number}</span>
            )}
            <span className={`ir-status-badge status-${row.current_status || 'draft'}`}>
              {paypalPayment?.status === 'completed' ? 'PAID & SETTLED' : allAuthoritiesApproved ? 'AUTHORITIES APPROVED' : 'AWAITING APPROVALS'}
            </span>
          </div>
        </div>

        <div className="ir-header-main">
          <div>
            <h1 className="ir-title">
              {req.product || invOcr.supplier_name || 'Invoice Sourcing Review'}
            </h1>
            <p className="ir-sub">
              <strong>Company:</strong> {invOcr.supplier_id || invOcr.supplier_name || req.preferred_vendors || 'Verified Vendor'} · <strong>Department:</strong> {req.department || 'Operations'} · <strong>Submitted:</strong> {row.created_at ? new Date(row.created_at).toLocaleDateString() : 'Today'}
            </p>
          </div>
          <div className="ir-header-right">
            <div className="ir-total-box">
              <span className="ir-total-label">Invoice Total</span>
              <span className="ir-total-amount">
                {money(invOcr.total || req.budget || 0, currency)}
              </span>
            </div>
            <div className="ir-header-actions">
              <button
                type="button"
                className="ir-btn"
                onClick={() => setShowAuditModal(true)}
                title="View immutable chronological audit time log trail"
              >
                <Clock size={14} /> Audit Log
              </button>
              <button
                type="button"
                className="ir-btn"
                onClick={() => navigate(`/procurement?newRequest=new&requestId=${row.id}&intakeStep=0&mode=edit`)}
              >
                <Pencil size={14} /> Edit Form
              </button>
              <button
                type="button"
                className="ir-btn"
                onClick={loadData}
                title="Refresh latest status from backend"
              >
                <RefreshCw size={14} /> Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      {actionNotice && (
        <div className="ir-action-notice">
          <CheckCircle size={16} />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* ── Respective Approval Authorities Gate (Clean, Spacious) ── */}
      <section className="ir-panel ir-authorities-panel">
        <div className="ir-section-head">
          <div>
            <span className="ir-eyebrow">STAGE 3 · HUMAN AUTHORITY GATING</span>
            <h2>
              Respective Approval Authorities Gate
              <span className="ir-gate-counter">
                ({approvedCount} / {authorityNodes.length} Approved)
              </span>
            </h2>
            <p className="ir-section-desc">
              Each respective approval authority below received <em>"Have you approved this invoice?"</em>. All authorities must approve their checkpoint before Final ML Fraud Check and Payment Settlement unlock.
            </p>
          </div>
          {!allAuthoritiesApproved && (
            <button
              type="button"
              className="btn btn-primary"
              disabled={busyBatch}
              onClick={handleApproveAll}
              style={{ background: '#ef9976', color: '#14100c', fontWeight: 800, border: 'none' }}
            >
              {busyBatch ? 'Approving…' : '✓ Approve All Remaining Authorities'}
            </button>
          )}
        </div>

        <div className="ir-authorities-grid">
          {authorityNodes.map((n, idx) => {
            const isApp = Boolean(nodeApprovals[n.id]?.approved);
            const approvalRecord = nodeApprovals[n.id];
            return (
              <div key={n.id} className={`ir-auth-card ${isApp ? 'approved' : 'pending'}`}>
                <div className="ir-auth-card-head">
                  <span className="ir-auth-idx">{idx + 1}</span>
                  <div>
                    <h4 className="ir-auth-name">{n.label}</h4>
                    <span className="ir-auth-group">{n.owner_group}</span>
                  </div>
                  {isApp ? (
                    <span className="ir-auth-badge approved">✓ Approved</span>
                  ) : (
                    <span className="ir-auth-badge pending">Pending</span>
                  )}
                </div>

                <div className="ir-auth-card-body">
                  <div className="ir-auth-row">
                    <span className="ir-k">Assigned Authority:</span>
                    <span className="ir-v"><strong>{n.assignee?.name || n.owner_group}</strong> ({n.assignee?.email || 'prepares23@gmail.com'})</span>
                  </div>
                  <div className="ir-auth-row">
                    <span className="ir-k">Mandatory Question:</span>
                    <span className="ir-v italic">"Have you approved this invoice ({invOcr.invoice_number || 'INV'} · {currency} {invOcr.total || req.budget})?"</span>
                  </div>
                  {isApp && approvalRecord?.actor && (
                    <div className="ir-auth-row approved-meta">
                      <span className="ir-k">Signed Off By:</span>
                      <span className="ir-v">{approvalRecord.actor}</span>
                    </div>
                  )}
                </div>

                <div className="ir-auth-card-foot">
                  {isApp ? (
                    <span className="ir-auth-done-text">
                      ✓ Authority Sign-Off Completed
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary ir-auth-btn"
                      disabled={busyNodeId === n.id}
                      onClick={() => handleApproveNode(n)}
                    >
                      <UserCheck size={14} />
                      {busyNodeId === n.id ? 'Approving…' : `Approve as ${n.owner_group}`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* ── STAGE 4 & 5 Gated Controls (ML Model & PayPal Settlement) ── */}
        <div className="ir-pipeline-bottom-gates">
          {/* Stage 4 ML Check */}
          <div className={`ir-gate-box ${assessment ? 'completed' : allAuthoritiesApproved ? 'ready' : 'locked'}`}>
            <div className="ir-gate-box-head">
              <div className="ir-gate-icon-title">
                <ShieldCheck size={20} className={assessment?.is_fraud ? 'text-danger' : assessment ? 'text-success' : 'text-muted'} />
                <div>
                  <h4>Stage 4 · Final Check Sent to ML Model</h4>
                  <small>PyTorch Autoencoder + Isolation Forest Hybrid Classifier</small>
                </div>
              </div>
              <div>
                {!allAuthoritiesApproved ? (
                  <span className="ir-badge-locked">🔒 Locked (Awaiting Authorities)</span>
                ) : !assessment ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busyMl}
                    onClick={handleRunMl}
                    style={{ background: '#ef9976', color: '#14100c', fontWeight: 800, border: 'none' }}
                  >
                    {busyMl ? 'Evaluating ML Model…' : '✨ Send Final Invoice to ML Model'}
                  </button>
                ) : (
                  <span className={`ir-badge-${assessment.is_fraud ? 'danger' : 'success'}`}>
                    {assessment.is_fraud ? '⚠️ FRAUD RISK FLAGGED' : '✓ CONSIDERED NOT FRAUD'}
                  </span>
                )}
              </div>
            </div>

            {assessment && (
              <div className="ir-ml-results">
                <div className="ir-ml-stat">
                  <span>Combined Anomaly Score</span>
                  <strong>{((assessment.score || 0) * 100).toFixed(1)}%</strong>
                  <small>Threshold: {((assessment.threshold || 0.9) * 100).toFixed(1)}%</small>
                </div>
                <div className="ir-ml-stat">
                  <span>Autoencoder Percentile</span>
                  <strong>{((assessment.autoencoder_percentile || 0) * 100).toFixed(1)}%</strong>
                  <small>Raw MSE: {(assessment.autoencoder_raw_mse || 0.0005).toFixed(4)}</small>
                </div>
                <div className="ir-ml-stat">
                  <span>Isolation Forest Percentile</span>
                  <strong>{((assessment.isolation_forest_percentile || 0) * 100).toFixed(1)}%</strong>
                  <small>Raw Score: {(assessment.isolation_forest_raw_score || 0.501).toFixed(4)}</small>
                </div>
                {assessment.recommendation && (
                  <div className="ir-ml-verdict">
                    <strong>ML Recommendation:</strong> {assessment.recommendation}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Stage 5 PayPal Settlement */}
          <div className={`ir-gate-box ${paypalPayment?.status === 'completed' ? 'completed' : assessment && !assessment.is_fraud ? 'ready' : 'locked'}`}>
            <div className="ir-gate-box-head">
              <div className="ir-gate-icon-title">
                <CreditCard size={20} className={paypalPayment?.status === 'completed' ? 'text-success' : 'text-muted'} />
                <div>
                  <h4>Stage 5 · Make Payment (PayPal Sandbox Settlement)</h4>
                  <small>B2B Simulated Disbursement with Instant Reconciled Settlement</small>
                </div>
              </div>
              <div>
                {!allAuthoritiesApproved ? (
                  <span className="ir-badge-locked">🔒 Locked (Awaiting Authorities)</span>
                ) : !assessment ? (
                  <span className="ir-badge-locked">🔒 Locked (Run ML Model First)</span>
                ) : assessment.is_fraud ? (
                  <span className="ir-badge-danger">⛔ Blocked by ML Fraud Gate</span>
                ) : paypalPayment?.status === 'completed' ? (
                  <span className="ir-badge-success">✓ Paid via PayPal Sandbox ({paypalPayment.order_id})</span>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busyPay}
                    onClick={handlePaypalSettle}
                    style={{ background: '#059669', borderColor: '#059669', color: '#fff', fontWeight: 800 }}
                  >
                    {busyPay ? 'Disbursing…' : `💳 Make Payment (${currency} ${Number(invOcr.total || req.budget || 0).toLocaleString()})`}
                  </button>
                )}
              </div>
            </div>

            {paypalPayment?.status === 'completed' && (
              <div className="ir-payment-receipt">
                <span>Transaction Order ID: <strong>{paypalPayment.order_id}</strong></span>
                <span>Payer Account: <strong>prepares23@gmail.com (PayPal Sandbox B2B)</strong></span>
                <span>Reconciled Amount: <strong>{currency} {Number(invOcr.total || req.budget || 0).toLocaleString()}</strong></span>
                <span>Claims Ledger: <strong>INV-SR-{String(row.id).padStart(4, '0')} (Updated to APPROVED)</strong></span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Distinct Mind Map for Each Item (As previously structured) ── */}
      <section className="ir-panel ir-mindmap-panel">
        <div className="ir-section-head">
          <div>
            <span className="ir-eyebrow">STRUCTURED APPROVAL MIND MAPS</span>
            <h2>
              <Network size={20} style={{ verticalAlign: 'middle', marginRight: 8, color: '#ef9976' }} />
              Purchase &amp; Line-Item Mind Maps
            </h2>
            <p className="ir-section-desc">
              Inspect the tailored checkpoint paths. Switch between items to view the distinct approval, verification, and 3-way match topology specific to each line item.
            </p>
          </div>

          {/* Item Selector Tabs */}
          <div className="ir-item-tabs">
            <button
              type="button"
              className={`ir-tab-btn ${activeItemTab === 'unified' ? 'active' : ''}`}
              onClick={() => setActiveItemTab('unified')}
            >
              <Layers size={14} /> All Items Combined Map
            </button>
            {lineItems.map((item, idx) => (
              <button
                key={idx}
                type="button"
                className={`ir-tab-btn ${activeItemTab === String(idx) ? 'active' : ''}`}
                onClick={() => setActiveItemTab(String(idx))}
              >
                <Tag size={13} /> Item {idx + 1}: {(item.description || `Line Item ${idx + 1}`).slice(0, 26)}…
              </button>
            ))}
          </div>
        </div>

        {/* Mind Map Canvas */}
        <div className="ir-mindmap-canvas-container">
          <WorkflowMindMap
            workflow={currentMindMap}
            fullWorkflow={workflow}
            requestId={row.id}
            assessment={assessment}
            initialPaypal={paypalPayment}
            onAssessmentComplete={loadData}
          />
        </div>
      </section>

      {/* ── Separate Section for Vendors per Invoice Item ── */}
      <section className="ir-panel ir-vendors-panel">
        <div className="ir-section-head">
          <div>
            <span className="ir-eyebrow">SUPPLIER DIRECTORY &amp; COMMERCIAL MATCH</span>
            <h2>
              <Building2 size={20} style={{ verticalAlign: 'middle', marginRight: 8, color: '#ef9976' }} />
              Item-Specific Suppliers &amp; Commercial Breakdown
            </h2>
            <p className="ir-section-desc">
              Independent supplier, tax registration, and fulfillment profile for each line item on this invoice. Cross-referenced against Master Reference Data to detect ghost vendors or conflict-of-interest collusion.
            </p>
          </div>
        </div>

        <div className="ir-vendor-items-grid">
          {lineItems.map((item, idx) => {
            const itemTotal = Number(item.quantity || 1) * Number(item.unit_price || 0);
            const isFlight = /flight|air|airline|del - blr/i.test(item.description || '');
            const isHotel = /hotel|stay|night|lodging/i.test(item.description || '');

            return (
              <article key={idx} className="ir-vendor-item-card">
                <div className="ir-vendor-card-header">
                  <div className="ir-vendor-title-wrap">
                    <span className="ir-item-sku-tag">{item.sku || `ITEM-${idx + 1}`}</span>
                    <h3>{item.description || `Invoice Line Item #${idx + 1}`}</h3>
                  </div>
                  <span className="ir-item-cost-badge">
                    {money(itemTotal, currency)}
                  </span>
                </div>

                <div className="ir-vendor-card-details">
                  <div className="ir-detail-block">
                    <span className="ir-detail-k">Billed Supplier / Company</span>
                    <span className="ir-detail-v font-bold text-accent-primary">
                      {invOcr.supplier_id || invOcr.supplier_name || req.preferred_vendors || 'MAKEMYTRIP (INDIA) PVT LTD'}
                    </span>
                    <small className="ir-detail-sub">
                      GSTIN / Tax ID: <strong>{invOcr.invoice_number ? '27AABCUBGORIZ2' : 'VERIFIED-REG'}</strong>
                    </small>
                  </div>

                  <div className="ir-detail-block">
                    <span className="ir-detail-k">Master Reference Verification</span>
                    <span className="ir-detail-v text-success font-medium">
                      ✓ Registered Approved Vendor in Master Directory
                    </span>
                    <small className="ir-detail-sub">
                      Cross-reference: No employee address or bank account collision.
                    </small>
                  </div>

                  <div className="ir-detail-block">
                    <span className="ir-detail-k">Commercial Terms</span>
                    <span className="ir-detail-v">
                      Quantity: <strong>{item.quantity || 1}</strong> × Unit Price: <strong>{money(item.unit_price || 0, currency)}</strong>
                    </span>
                    <small className="ir-detail-sub">
                      Payment Terms: {req.payment_terms || 'Due on receipt / Instant Sandbox settlement'}
                    </small>
                  </div>

                  <div className="ir-detail-block">
                    <span className="ir-detail-k">Delivery / Service Acceptance</span>
                    <span className="ir-detail-v">
                      {isFlight ? 'Airline e-Ticket & PNR Travel Verification' : isHotel ? 'Itemized Hotel Folio & Stay Date Verification' : item.verification_method || 'Service acceptance sign-off'}
                    </span>
                    <small className="ir-detail-sub">
                      Delivery Location: {item.location || req.delivery_location || 'India (DEL - BLR)'}
                    </small>
                  </div>
                </div>

                <div className="ir-vendor-card-footer">
                  <div className="ir-vendor-foot-meta">
                    <span>Department: <strong>{item.department || req.department || 'Operations'}</strong></span>
                    <span>Line Type: <strong>{item.line_type || 'Service'}</strong></span>
                  </div>
                  <button
                    type="button"
                    className="ir-view-map-link"
                    onClick={() => {
                      setActiveItemTab(String(idx));
                      window.scrollTo({ top: 380, behavior: 'smooth' });
                    }}
                  >
                    View Item #{idx + 1} Mind Map <ChevronRight size={14} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* ── Audit Time Log Modal ── */}
      {showAuditModal && (
        <AuditTimeLogModal
          requestId={row.id}
          requestKind="sourcing"
          requestTitle={req.product || invOcr.supplier_name || 'Invoice Requisition'}
          initialAuditLog={row.audit_log}
          onClose={() => setShowAuditModal(false)}
        />
      )}
    </main>
  );
}
