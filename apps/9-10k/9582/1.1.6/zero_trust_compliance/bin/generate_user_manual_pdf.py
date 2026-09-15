#!/usr/bin/env python3
"""
DoD Zero Trust Compliance & IMS — PDF User Manual Generator
Generates a comprehensive, publication-grade PDF operating guide
for non-agile and defense compliance personnel.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that adds running headers and dynamic 'Page X of Y' footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress headers/footers on cover page

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Running Header
        self.drawString(54, 750, "DoD Zero Trust Compliance & IMS — Official User Manual")
        self.drawRightString(558, 750, "SuhLabs Platform Operations")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 744, 558, 744)

        # Running Footer
        self.line(54, 45, 558, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "UNCLASSIFIED // FOR OFFICIAL USE ONLY // COMPLIANCE GUIDANCE")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    NAVY = colors.HexColor("#0B132B")
    BLUE = colors.HexColor("#1C3166")
    CYAN = colors.HexColor("#00A896")
    EMERALD = colors.HexColor("#028090")
    DARK_TEXT = colors.HexColor("#1A202C")
    MUTED_TEXT = colors.HexColor("#4A5568")
    LIGHT_BG = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=NAVY,
        alignment=1, # Center
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=MUTED_TEXT,
        alignment=1,
        spaceAfter=25
    )
    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=BLUE,
        alignment=1
    )
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT,
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=DARK_TEXT,
        leftIndent=12,
        spaceAfter=3
    )
    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=BLUE
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=DARK_TEXT
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=NAVY
    )

    story = []

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("DOD ZERO TRUST COMPLIANCE & IMS", title_style))
    story.append(Paragraph("Enterprise Agile Operations, Integrated Master Schedule (IMS), and Continuous ATO (cATO) Manual", subtitle_style))
    story.append(HRFlowable(width="80%", thickness=2, color=CYAN, spaceAfter=25))

    cover_table_data = [
        [Paragraph("<b>Document Version:</b>", table_cell_bold), Paragraph("v1.1.5 Production Release", table_cell)],
        [Paragraph("<b>Product Mandate:</b>", table_cell_bold), Paragraph("FY2027 DoD Target Level Zero Trust Mandate (COAs 1–3, v1.1)", table_cell)],
        [Paragraph("<b>Architecture Standard:</b>", table_cell_bold), Paragraph("NIST SP 800-207 Three-Plane Model (PEP, PIP, PDP, PE, PA, PAP)", table_cell)],
        [Paragraph("<b>Platform Scope:</b>", table_cell_bold), Paragraph("160 Total Activities (152 Roadmap Activities + 8 Sprint 0 Enablers)", table_cell)],
        [Paragraph("<b>Security & Cloud Status:</b>", table_cell_bold), Paragraph("Splunk Cloud Precertified (0 Errors, 0 Failures) | 100% Air-Gapped", table_cell)],
        [Paragraph("<b>Author & Maintainer:</b>", table_cell_bold), Paragraph("SuhLabs Open Source Platform Engineering", table_cell)],
        [Paragraph("<b>Effective Date:</b>", table_cell_bold), Paragraph("August 2026", table_cell)]
    ]
    t_cover = Table(cover_table_data, colWidths=[150, 280])
    t_cover.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_cover)
    story.append(Spacer(1, 30))

    callout_box = [
        [Paragraph("<b>EXECUTIVE NOTICE FOR DEFENSE & COMPLIANCE STAKEHOLDERS:</b><br/>This operational guide provides step-by-step instructions for Program Managers, Information System Security Officers (ISSOs), Information System Security Managers (ISSMs), and DevSecOps Engineers. It translates commercial Agile terminology into standardized DoD acquisition, WBS, and Continuous Authorization to Operate (cATO) workflows.", callout_style)]
    ]
    t_callout = Table(callout_box, colWidths=[430])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BEE3F8")),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_callout)

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: AGILE TRANSLATION FOR DEFENSE PERSONNEL
    # =========================================================================
    story.append(Paragraph("1. Agile Terminology Translated for Defense Personnel", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph("If you are accustomed to traditional Waterfall acquisition, Work Breakdown Structures (WBS), and eMASS/STIG checklists, use this cross-walk to understand the platform's agile concepts:", body_style))

    agile_crosswalk = [
        [Paragraph("Agile Term", table_cell_bold), Paragraph("DoD Defense Acquisition Meaning", table_cell_bold), Paragraph("How It Operates in This Platform", table_cell_bold)],
        [Paragraph("<b>Agile Story</b>", table_cell), Paragraph("<b>Roadmap Activity / WBS Task</b>", table_cell), Paragraph("A distinct compliance requirement (e.g. ZTA-1.1.1: Catalog Users & Non-Person Entities).", table_cell)],
        [Paragraph("<b>Story Points</b>", table_cell), Paragraph("<b>Level of Effort / Estimated Duration</b>", table_cell), Paragraph("Standard complexity metric (3 = rapid config, 5 = system integration, 8+ = enterprise rollout).", table_cell)],
        [Paragraph("<b>Sprint</b>", table_cell), Paragraph("<b>2-Week Milestone Window</b>", table_cell), Paragraph("Time-boxed cadence to execute and certify a prioritized batch of baseline capabilities.", table_cell)],
        [Paragraph("<b>Kanban Board</b>", table_cell), Paragraph("<b>Stage-Gate Execution Pipeline</b>", table_cell), Paragraph("Visual 5-column progression: Backlog -> To Do -> In Progress -> Testing/In Review -> Done.", table_cell)],
        [Paragraph("<b>WIP Limits</b>", table_cell), Paragraph("<b>Anti-Bottleneck Gate</b>", table_cell), Paragraph("Limits concurrent open tasks per column to prevent resource fragmentation and stalls.", table_cell)],
        [Paragraph("<b>Definition of Done</b>", table_cell), Paragraph("<b>ISSO Acceptance Criteria</b>", table_cell), Paragraph("Mandatory conditions (telemetry query + SHA-256 hash + CAC sign-off) required for closure.", table_cell)]
    ]
    t_agile = Table(agile_crosswalk, colWidths=[90, 160, 254])
    t_agile.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_agile)
    story.append(Spacer(1, 10))

    # =========================================================================
    # CHAPTER 2: AGILE SPRINT BOARD & KANBAN GOVERNANCE
    # =========================================================================
    story.append(Paragraph("2. Agile Sprint Board & Kanban Governance (zt_kanban)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph("The primary operational landing view is the <b>Agile Sprint Board</b> (<code>zt_kanban</code>), providing real-time visibility into all 160 activities.", body_style))
    story.append(Paragraph("<b>Workflow Columns:</b>", h2_style))
    story.append(Paragraph("• <b>Backlog (Commitment Boundary):</b> Unscheduled future activities prioritized by DoD Course of Action (COA 1 Target vs. COA 3 Advanced).", bullet_style))
    story.append(Paragraph("• <b>To Do:</b> Committed activities assigned to current sprint with predecessor enablers ready.", bullet_style))
    story.append(Paragraph("• <b>In Progress:</b> Active engineering, configuration, and telemetry data-wiring.", bullet_style))
    story.append(Paragraph("• <b>Testing / In Review (Delivery Boundary):</b> Engineering complete; awaiting ISSO/ISSM verification.", bullet_style))
    story.append(Paragraph("• <b>Done / Certified:</b> Cryptographically signed off via CAC authentication and locked against automated regressions.", bullet_style))
    
    story.append(Paragraph("<b>Sprint 0 Enabler Dependencies:</b>", h2_style))
    story.append(Paragraph("Activities cannot move to <code>In Progress</code> until their linked Sprint 0 data-wiring enablers (ACAS, IdP, EDR, VRAM, SOAR) are complete. Tech Leads hold override authority in exceptional operational circumstances.", body_style))
    story.append(Spacer(1, 10))

    # =========================================================================
    # CHAPTER 3: PROOF OF DELIVERY (PoD) & CAC STAGE-GATE
    # =========================================================================
    story.append(Paragraph("3. Proof of Delivery (PoD) Vault & CAC Stage-Gate", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph("To satisfy federal auditability, clicking any Kanban card opens the <b>5-Tab Governance Modal</b>:", body_style))

    story.append(Paragraph("<b>Step-by-Step Delivery Acceptance:</b>", h2_style))
    story.append(Paragraph("1. <b>Tab 1 (Details):</b> Review DoD activity description, official outcomes, and implementation scope (Enterprise vs. Component).", bullet_style))
    story.append(Paragraph("2. <b>Tab 2 (PoD Evidence):</b> Select <i>Method A (Live Splunk Telemetry Query)</i> to test live index feeds or <i>Method B (Artifact Upload)</i> for STIG/DFD reports. The platform computes an immutable 64-character <b>SHA-256 hash</b>.", bullet_style))
    story.append(Paragraph("3. <b>Tab 3 (CAC Stage-Gate Sign-Off):</b> Authorized <b>ISSO</b> or <b>ISSM</b> enters their 10-digit DoD EDIPI. Clicking <i>'Certify with CAC Smart Card'</i> applies a cryptographic audit stamp.", bullet_style))
    story.append(Paragraph("4. <b>Tab 4 (Predecessors):</b> Confirm that upstream telemetry pipelines are operational.", bullet_style))
    story.append(Paragraph("5. <b>Tab 5 (NIST SP 800-207 Mapping):</b> Cross-walk the activity to its architectural plane and logical component (PEP, PIP, PDP, PE, PA, PAP).", bullet_style))
    
    story.append(Paragraph("<b>Tamper-Resistant Override Locks:</b>", h2_style))
    story.append(Paragraph("When an ISSO certifies an activity, <code>override_lock: true</code> is engaged. The card renders a <b>🛡️ ISSO LOCKED / 🛡️ CERTIFIED</b> badge, guaranteeing that automated background discovery scans will never mutate or regress human-vetted compliance states.", body_style))
    story.append(Spacer(1, 10))

    # =========================================================================
    # CHAPTER 4: IMS GANTT & CRITICAL PATH ENGINE
    # =========================================================================
    story.append(Paragraph("4. Integrated Master Schedule (IMS) & Critical Path Engine (zt_ims_gantt)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph("The platform includes a pure-Python Custom Search Command (<code>| getcriticalpath</code>) implementing Kahn's Directed Acyclic Graph (DAG) Critical Path Method (CPM):", body_style))
    story.append(Paragraph("• <b>US Statutory Federal Holidays:</b> Programmatically evaluates all 11 Federal / DoD statutory holidays with weekend observance rules (Saturday -> Friday, Sunday -> Monday).", bullet_style))
    story.append(Paragraph("• <b>Custom PTO Exclusions:</b> Excludes scheduled team leave and non-working maintenance periods.", bullet_style))
    story.append(Paragraph("• <b>Total Float / Slack Calculation:</b> Calculates early/late starts, project duration, and highlights the True Critical Path in high-contrast red.", bullet_style))
    story.append(Paragraph("• <b>Asynchronous Rollup:</b> Kanban story completions dual-write to <code>[zt_milestones_ims]</code>, automatically updating milestone completion percentages (0%, 50%, 80%, 100%).", bullet_style))
    story.append(Spacer(1, 10))

    # =========================================================================
    # CHAPTER 5: CONTINUOUS ATO (cATO) & TROUBLESHOOTING
    # =========================================================================
    story.append(Paragraph("5. Continuous ATO (cATO) & Troubleshooting Runbook", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph("<b>Scheduled Discovery:</b> Automated scans run nightly at <b>02:00 UTC</b> (<code>0 2 * * *</code> in <code>savedsearches.conf</code>) against accelerated CIM data models, updating the <code>[zt_discovery_cache]</code> lookup to eliminate search head load during core working hours.", body_style))

    trouble_table_data = [
        [Paragraph("Symptom / Error", table_cell_bold), Paragraph("Root Cause", table_cell_bold), Paragraph("Resolution Procedure", table_cell_bold)],
        [Paragraph("<b>Card Snaps Back (Rollback)</b>", table_cell), Paragraph("Predecessor feed incomplete or missing write role.", table_cell), Paragraph("Complete Sprint 0 blocker or have Tech Lead toggle override; verify 'admin' or 'power' role.", table_cell)],
        [Paragraph("<b>CAC Sign-off Denied (403)</b>", table_cell), Paragraph("User role is not authorized ISSO/ISSM.", table_cell), Paragraph("Switch role selector to ISSO/ISSM or log in with compliance administrator credentials.", table_cell)],
        [Paragraph("<b>Invalid EDIPI Error (400)</b>", table_cell), Paragraph("EDIPI is not exactly 10 digits.", table_cell), Paragraph("Enter valid 10-digit numeric DoD EDIPI (no spaces, dashes, or letters).", table_cell)],
        [Paragraph("<b>CIRCULAR_DEPENDENCY</b>", table_cell), Paragraph("Predecessor milestone loop in IMS.", table_cell), Paragraph("Run diagnostic search '| inputlookup zt_milestones_ims_lookup | getcriticalpath' to remove loop.", table_cell)],
        [Paragraph("<b>KV Store Starting / Failed</b>", table_cell), Paragraph("MongoDB disk threshold reached.", table_cell), Paragraph("Ensure >5 GB disk on $SPLUNK_DB; run '$SPLUNK_HOME/bin/splunk show kvstore-status'.", table_cell)]
    ]
    t_trouble = Table(trouble_table_data, colWidths=[110, 140, 254])
    t_trouble.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_trouble)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Immutable Audit Log:</b>", h2_style))
    story.append(Paragraph("Every stage-gate approval and override is logged permanently to <code>index=_internal sourcetype=zerotrust_audit</code> for Authorizing Official (AO) and Inspector General review.", body_style))

    # Build the document using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Successfully generated PDF User Manual at: {filename}")


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_pdf_appserver = os.path.join(base_dir, 'appserver', 'static', 'Zero_Trust_Compliance_User_Manual.pdf')

    os.makedirs(os.path.dirname(target_pdf_appserver), exist_ok=True)
    build_pdf(target_pdf_appserver)

