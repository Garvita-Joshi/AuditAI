"""
Script to generate high-resolution PNG and vector SVG workflow diagrams for AuditAI.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os
import shutil

def create_diagram(output_png_path, output_svg_path):
    # Dimensions
    fig, ax = plt.subplots(figsize=(18, 14), dpi=300)
    fig.patch.set_facecolor('#0B0F19')
    ax.set_facecolor('#0B0F19')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title & Subtitle
    plt.text(50, 97.5, "AuditAI — End-to-End System Workflow & ML Architecture", 
             fontsize=20, fontweight='bold', color='#FFFFFF', ha='center', va='center', fontfamily='sans-serif')
    plt.text(50, 95.2, "Two-Stage Anomaly Detection (Autoencoder + Isolation Forest) · SHAP Explainability · Gemini LLM · Maker-Checker Governance", 
             fontsize=10.5, color='#94A3B8', ha='center', va='center', fontfamily='sans-serif')

    def draw_card(x, y, w, h, bg_color, border_color, radius=1.2, alpha=0.95):
        box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.3,rounding_size={radius}",
                             facecolor=bg_color, edgecolor=border_color, linewidth=1.5, alpha=alpha)
        ax.add_patch(box)

    def draw_arrow(x1, y1, x2, y2, color='#64748B', style='->', lw=1.5, connectionstyle=None):
        arrow = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', color=color,
                                mutation_scale=14, linewidth=lw, connectionstyle=connectionstyle)
        ax.add_patch(arrow)

    # -------------------------------------------------------------
    # 1. INGESTION STAGE (Top row: y=77 to 92)
    # -------------------------------------------------------------
    draw_card(4, 76, 92, 16.5, '#111827', '#374151', radius=1.5)
    plt.text(7, 90.5, "STAGE 1: MULTI-MODAL DATA INGESTION & EXTRACTION", fontsize=11, fontweight='bold', color='#38BDF8')

    # Receipt branch
    draw_card(7, 78.5, 23, 10, '#1E293B', '#3B82F6')
    plt.text(18.5, 85.5, "Receipt Image / PDF", fontsize=10, fontweight='bold', color='#FFFFFF', ha='center')
    plt.text(18.5, 82.5, "Invoices, Cab & Meal slips", fontsize=8.5, color='#94A3B8', ha='center')
    plt.text(18.5, 80.2, "PNG, JPG, TIFF, PDF format", fontsize=7.5, color='#64748B', ha='center')

    draw_arrow(30, 83.5, 34, 83.5, color='#3B82F6')

    # OpenCV + OCR
    draw_card(34, 78.5, 27, 10, '#1E293B', '#3B82F6')
    plt.text(47.5, 86, "Computer Vision & OCR Engine", fontsize=10, fontweight='bold', color='#60A5FA', ha='center')
    plt.text(47.5, 83.5, "• OpenCV: Grayscale, Bilateral, Deskew", fontsize=8, color='#E2E8F0', ha='center')
    plt.text(47.5, 81.3, "• Tesseract OCR: Regex field extraction", fontsize=8, color='#E2E8F0', ha='center')
    plt.text(47.5, 79.5, "• Gemini Vision: Fallback structured JSON", fontsize=7.5, color='#F59E0B', ha='center')

    # Claim CSV branch
    draw_card(66, 78.5, 27, 10, '#1E293B', '#10B981')
    plt.text(79.5, 86, "Claim Records & Fuzzy Matching", fontsize=10, fontweight='bold', color='#34D399', ha='center')
    plt.text(79.5, 83.5, "• Claim CSV: Amount, Date, Vendor, Employee", fontsize=8, color='#E2E8F0', ha='center')
    plt.text(79.5, 81.3, "• FuzzyWuzzy: Levenshtein distance matching", fontsize=8, color='#E2E8F0', ha='center')
    plt.text(79.5, 79.5, "• Typosquat Detection (e.g. Amazn vs Amazon)", fontsize=7.5, color='#F43F5E', ha='center')

    draw_arrow(61, 83.5, 66, 83.5, color='#38BDF8')

    # Arrow from Stage 1 to Stage 2
    draw_arrow(50, 76, 50, 72, color='#38BDF8', lw=2)

    # -------------------------------------------------------------
    # 2. FEATURE ENGINEERING (Middle: y=57 to 72)
    # -------------------------------------------------------------
    draw_card(4, 57.5, 92, 14, '#111827', '#4F46E5', radius=1.5)
    plt.text(7, 69.2, "STAGE 2: FEATURE ENGINEERING (15 High-Signal Deterministic Metrics)", fontsize=11, fontweight='bold', color='#818CF8')

    f_cols = [
        ["1. Amount Mismatch Ratio", "2. Has Amount Mismatch", "3. Duplicate Score", "4. Is Likely Duplicate"],
        ["5. Vendor Anomaly Score", "6. Is Known Vendor", "7. Amount Z-Score", "8. 7-Day Frequency"],
        ["9. 30-Day Velocity", "10. Is Weekend Spend", "11. Is Holiday Spend", "12. Is Round Amount"],
        ["13. Amount Log-Scale", "14. Split Transaction Flag", "15. Category Risk Weight", "Normalized Feature Matrix"]
    ]
    xs = [7, 30, 53, 76]
    for col_idx, col_items in enumerate(f_cols):
        for row_idx, item in enumerate(col_items):
            y_pos = 66 - row_idx * 2.3
            txt_color = '#A5B4FC' if col_idx < 3 else '#C7D2FE'
            if "Normalized" in item:
                txt_color = '#34D399'
            plt.text(xs[col_idx], y_pos, f"• {item}", fontsize=8.2, color=txt_color, fontfamily='monospace')

    # Arrow from Stage 2 to Stage 3
    draw_arrow(50, 57.5, 50, 53.5, color='#818CF8', lw=2)

    # -------------------------------------------------------------
    # 3. TWO-STAGE MACHINE LEARNING CORE (Middle-Low: y=31 to 53)
    # -------------------------------------------------------------
    draw_card(4, 30.5, 92, 22.5, '#111827', '#9333EA', radius=1.5)
    plt.text(7, 50.8, "STAGE 3: TWO-STAGE HYBRID MACHINE LEARNING ANOMALY PIPELINE", fontsize=11, fontweight='bold', color='#C084FC')

    # Stage 3A: Autoencoder
    draw_card(7, 33, 26, 15.5, '#1F1535', '#A855F7')
    plt.text(20, 46.5, "Stage 3A: Deep Autoencoder", fontsize=10, fontweight='bold', color='#E9D5FF', ha='center')
    plt.text(20, 44, "(PyTorch Neural Network)", fontsize=8, color='#A855F7', ha='center')
    plt.text(20, 41.5, "Architecture: 15 → 10 → 6 → 10 → 15", fontsize=7.8, color='#E2E8F0', ha='center')
    plt.text(20, 39.5, "Trained on normal expense claims", fontsize=7.8, color='#94A3B8', ha='center')
    plt.text(20, 36.5, "Signal: Reconstruction Error (MSE)", fontsize=8.5, fontweight='bold', color='#F472B6', ha='center')
    plt.text(20, 34.5, "Detects complex non-linear distortions", fontsize=7.5, color='#94A3B8', ha='center')

    # Latent connection arrow
    draw_arrow(33, 40.5, 38, 40.5, color='#A855F7', lw=2)
    plt.text(35.5, 42, "Reconstructed\nFeatures", fontsize=7, color='#C084FC', ha='center')

    # Stage 3B: Isolation Forest
    draw_card(38, 33, 26, 15.5, '#1F1535', '#A855F7')
    plt.text(51, 46.5, "Stage 3B: Isolation Forest", fontsize=10, fontweight='bold', color='#E9D5FF', ha='center')
    plt.text(51, 44, "(Scikit-Learn Tree Ensemble)", fontsize=8, color='#A855F7', ha='center')
    plt.text(51, 41.5, "Builds randomized isolation trees", fontsize=7.8, color='#E2E8F0', ha='center')
    plt.text(51, 39.5, "Operates in reconstructed space", fontsize=7.8, color='#94A3B8', ha='center')
    plt.text(51, 36.5, "Signal: Tree Isolation Depth Score", fontsize=8.5, fontweight='bold', color='#F472B6', ha='center')
    plt.text(51, 34.5, "Anomalies isolate in fewer splits", fontsize=7.5, color='#94A3B8', ha='center')

    # Arrows to Fusion
    draw_arrow(28, 33, 68, 36.5, color='#F472B6', lw=1.5, connectionstyle="arc3,rad=-0.1")
    draw_arrow(59, 36.5, 68, 39.5, color='#F472B6', lw=1.5)

    # Score Fusion Box
    draw_card(68, 33, 25, 15.5, '#1F1535', '#EC4899')
    plt.text(80.5, 46.5, "Score Fusion Algorithm", fontsize=10, fontweight='bold', color='#FBCFE8', ha='center')
    plt.text(80.5, 43.5, "Final Score = α·Recon + (1-α)·IF", fontsize=8.5, fontweight='bold', color='#F472B6', ha='center')
    plt.text(80.5, 41, "(Default α = 0.40)", fontsize=8, color='#F9A8D4', ha='center')
    plt.text(80.5, 37.5, "• Score ≥ 0.70 → FLAGGED CLAIM", fontsize=8, fontweight='bold', color='#EF4444', ha='center')
    plt.text(80.5, 34.5, "• Score < 0.70 → Auto-Approved", fontsize=8, color='#10B981', ha='center')

    # Arrow from Stage 3 to Stage 4 & 5
    draw_arrow(80.5, 30.5, 80.5, 27.5, color='#EC4899', lw=2)

    # -------------------------------------------------------------
    # 4. EXPLAINABILITY & GENERATIVE AI (Bottom: y=3 to 27)
    # -------------------------------------------------------------
    draw_card(4, 2.5, 92, 24.5, '#111827', '#059669', radius=1.5)
    plt.text(7, 24.8, "STAGE 4 & 5: EXPLAINABLE AI (XAI), GENERATIVE AI & MAKER-CHECKER GOVERNANCE", fontsize=11, fontweight='bold', color='#34D399')

    # SHAP TreeExplainer
    draw_card(7, 4.5, 21, 18, '#064E3B', '#10B981')
    plt.text(17.5, 20.5, "SHAP Explainability", fontsize=10, fontweight='bold', color='#A7F3D0', ha='center')
    plt.text(17.5, 18.5, "shap.TreeExplainer", fontsize=8.5, color='#34D399', ha='center')
    plt.text(17.5, 15.5, "• Applied to Isolation Forest", fontsize=7.8, color='#D1FAE5', ha='center')
    plt.text(17.5, 13.5, "• Computes top 5 feature impacts", fontsize=7.8, color='#D1FAE5', ha='center')
    plt.text(17.5, 11, "Red: Pushes toward fraud", fontsize=7.5, fontweight='bold', color='#F87171', ha='center')
    plt.text(17.5, 9, "Green: Pushes toward normal", fontsize=7.5, fontweight='bold', color='#4ADE80', ha='center')
    plt.text(17.5, 6.5, "Rendered in UI Waterfall Chart", fontsize=7.5, color='#6EE7B7', ha='center')

    draw_arrow(28, 13.5, 31, 13.5, color='#10B981', lw=1.8)

    # Gemini LLM Report
    draw_card(31, 4.5, 21, 18, '#0F372E', '#059669')
    plt.text(41.5, 20.5, "Gemini Generative AI", fontsize=10, fontweight='bold', color='#A7F3D0', ha='center')
    plt.text(41.5, 18.5, "Natural Language Report", fontsize=8.5, color='#34D399', ha='center')
    plt.text(41.5, 15.5, "Inputs to prompt:", fontsize=7.8, color='#D1FAE5', ha='center')
    plt.text(41.5, 13.5, "1. Claim Metadata", fontsize=7.5, color='#E2E8F0', ha='center')
    plt.text(41.5, 11.5, "2. Top SHAP Risk Drivers", fontsize=7.5, color='#E2E8F0', ha='center')
    plt.text(41.5, 9.5, "3. OCR Receipt Discrepancy", fontsize=7.5, color='#E2E8F0', ha='center')
    plt.text(41.5, 6.5, "Outputs concise audit note", fontsize=7.8, fontweight='bold', color='#FDE047', ha='center')

    draw_arrow(52, 13.5, 55, 13.5, color='#34D399', lw=1.8)

    # Governance: Maker & Checker
    draw_card(55, 4.5, 38, 18, '#1E293B', '#F59E0B')
    plt.text(74, 20.5, "Human-in-the-Loop Maker-Checker Governance", fontsize=10, fontweight='bold', color='#FDE68A', ha='center')

    # Maker sub-box
    draw_card(57, 11.5, 34, 7, '#0F172A', '#F59E0B')
    plt.text(74, 16.5, "LEVEL 1: MAKER (Auditor)", fontsize=9, fontweight='bold', color='#FBBF24', ha='center')
    plt.text(74, 14.5, "Investigates SHAP chart, gauges, receipt & notes", fontsize=7.5, color='#CBD5E1', ha='center')
    plt.text(74, 12.7, "Action: 'Recommend Approve' or 'Recommend Reject'", fontsize=7.5, color='#38BDF8', ha='center')

    draw_arrow(74, 11.5, 74, 9.5, color='#F59E0B', lw=1.5)

    # Checker sub-box
    draw_card(57, 5.5, 34, 4.8, '#0F172A', '#EF4444')
    plt.text(74, 8.5, "LEVEL 2: CHECKER (Manager) — Segregation of Duties", fontsize=8.5, fontweight='bold', color='#F87171', ha='center')
    plt.text(74, 6.6, "Strict check: Checker != Maker. Action: Final Sign-off (Approved / Rejected)", fontsize=7.2, color='#E2E8F0', ha='center')

    plt.tight_layout()
    plt.savefig(output_png_path, format='png', dpi=300, facecolor='#0B0F19', bbox_inches='tight')
    plt.savefig(output_svg_path, format='svg', facecolor='#0B0F19', bbox_inches='tight')
    plt.close()
    print(f"Diagram successfully generated:\n- PNG: {output_png_path}\n- SVG: {output_svg_path}")

if __name__ == "__main__":
    os.makedirs("scripts/artifacts", exist_ok=True)
    out_png = os.path.abspath("scripts/artifacts/AuditAI_System_Workflow.png")
    out_svg = os.path.abspath("scripts/artifacts/AuditAI_System_Workflow.svg")
    create_diagram(out_png, out_svg)
