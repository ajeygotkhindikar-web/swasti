"""PDF wellness reports (individual and coach) using ReportLab."""
from __future__ import annotations

import io
import uuid
from datetime import date

from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Circle, Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import InterviewRecord, ProfessionalObservation, User, UserWellnessPlan, WellnessRecommendation
from .dashboard import build_dashboard

TEAL = colors.HexColor("#8C460A")          # deep saffron-brown accent text
FILL = colors.HexColor("#FDE6C4")          # very light saffron fill
ON_FILL = colors.HexColor("#5C2D06")       # brown text on saffron fill
INK = colors.HexColor("#3D2B1F")
SAFFRON = colors.HexColor("#EB6834")
CURRENT = colors.HexColor("#2A78D6")
GREEN = colors.HexColor("#4C9A2A")
IVORY = colors.HexColor("#FFF6EA")
LEVEL_COLORS = {
    "Needs Attention": colors.HexColor("#C0392B"), "Developing": colors.HexColor("#B9770E"),
    "Balanced": colors.HexColor("#2E6DB4"), "Good": colors.HexColor("#2E8B57"),
    "Thriving": colors.HexColor("#7D3C98"),
}


def _fmt(v):
    return "—" if v is None else f"{v:.0f}"


def _radar(data: dict) -> Drawing:
    d = Drawing(170 * mm, 110 * mm)
    sc = SpiderChart()
    sc.x, sc.y, sc.width, sc.height = 35 * mm, 8 * mm, 100 * mm, 95 * mm
    labels = [r["category"] for r in data["radar"]]
    sc.labels = labels
    series = [[r["current"] or 0 for r in data["radar"]], [r["target"] or 0 for r in data["radar"]]]
    if any(r["previous"] is not None for r in data["radar"]):
        series.insert(1, [r["previous"] or 0 for r in data["radar"]])
    sc.data = series
    sc.strands[0].strokeColor = CURRENT
    sc.strands[0].fillColor = colors.Color(0.165, 0.47, 0.84, alpha=0.18)
    sc.strands[0].strokeWidth = 1.5
    last = len(series) - 1
    sc.strands[last].strokeColor = SAFFRON
    sc.strands[last].fillColor = None
    sc.strands[last].strokeDashArray = (3, 2)
    if len(series) == 3:
        sc.strands[1].strokeColor = colors.HexColor("#8395A7")
        sc.strands[1].fillColor = None
    sc.strandLabels.fontSize = 6
    sc.spokeLabels.fontSize = 7
    sc.spokeLabels.fontName = "Helvetica"
    d.add(sc)
    legend = [("Current", CURRENT)] + ([("Previous", colors.HexColor("#8395A7"))] if len(series) == 3 else []) + [("Target", SAFFRON)]
    for i, (label, col) in enumerate(legend):
        d.add(Circle(140 * mm, (100 - i * 6) * mm, 1.5 * mm, fillColor=col, strokeColor=col))
        d.add(String(143 * mm, (99 - i * 6) * mm, label, fontSize=8))
    return d


def build_pdf(db: Session, subject: User, kind: str = "individual", viewer: User | None = None) -> bytes:
    data = build_dashboard(db, subject.user_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="SWASTI Wellness Report", author="SWASTI")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=TEAL, fontSize=20, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=TEAL, spaceBefore=10)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13, textColor=INK)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#555555"))
    el = []
    el.append(Paragraph("SWASTI", h1))
    el.append(Paragraph("360° Human Wellness &amp; Life Balance — <i>Balance Within. Harmony Around. Well-being for All.</i>", small))
    el.append(Spacer(1, 6))
    title = "Coach Wellness Report" if kind == "coach" else "Personal Wellness Report"
    el.append(Paragraph(f"<b>{title}</b> · {subject.full_name}{' (synthetic demo data)' if subject.is_synthetic else ''} · generated {date.today().isoformat()}", body))
    ov = data["overview"]
    if not data["has_data"]:
        el.append(Paragraph("No completed assessment yet.", body))
        doc.build(el)
        return buf.getvalue()

    el.append(Paragraph("Overview", h2))
    overall = _fmt(ov["overall_indicator"]) if ov["overall_indicator"] is not None else "Not enough data"
    t = Table([
        ["Overall indicator", overall, "Dimensions assessed", f"{ov['dimensions_assessed']} / {ov['dimensions_total']}"],
        ["Needs attention", str(ov["needs_attention"]), "Improving", str(ov["improving"])],
        ["Last assessment", ov["last_assessment_date"], "Next review", ov["next_review_date"]],
    ], colWidths=[40 * mm, 45 * mm, 40 * mm, 45 * mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("BACKGROUND", (0, 0), (-1, -1), IVORY),
                           ("TEXTCOLOR", (0, 0), (0, -1), TEAL), ("TEXTCOLOR", (2, 0), (2, -1), TEAL),
                           ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#F1E2CE"))]))
    el.append(t)
    if data["attention_flags"]:
        el.append(Spacer(1, 4))
        el.append(Paragraph("<b>Needs attention (shown separately so it isn't hidden by the overall figure):</b> " +
                            ", ".join(f"{f['category_name']} ({_fmt(f['score'])})" for f in data["attention_flags"]), body))

    el.append(Paragraph("Wellness radar", h2))
    el.append(_radar(data))

    el.append(Paragraph("Fourteen dimensions", h2))
    rows = [["Dimension", "Baseline", "Previous", "Current", "Level", "Target", "Change"]]
    for c in data["cards"]:
        ch = c["change"]
        rows.append([c["category_name"], _fmt(c["baseline"]), _fmt(c["previous"]), _fmt(c["current"]), c["level"] or "—",
                     _fmt(c["achievable_target"] or c["target"]), "—" if ch is None else f"{ch:+.0f}"])
    t = Table(rows, colWidths=[46 * mm, 18 * mm, 18 * mm, 18 * mm, 30 * mm, 18 * mm, 18 * mm], repeatRows=1)
    style = [("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), FILL), ("TEXTCOLOR", (0, 0), (-1, 0), ON_FILL), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#F1E2CE")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, IVORY])]
    for i, c in enumerate(data["cards"], start=1):
        if c["level"] in LEVEL_COLORS:
            style.append(("TEXTCOLOR", (4, i), (4, i), LEVEL_COLORS[c["level"]]))
    t.setStyle(TableStyle(style))
    el.append(t)

    strengths = [c for c in data["cards"] if c["current"] is not None and c["current"] >= 75]
    el.append(Paragraph("Key strengths", h2))
    el.append(Paragraph(", ".join(f"{c['category_name']} ({_fmt(c['current'])})" for c in strengths) or "Keep going — strengths will show here as scores grow.", body))

    el.append(Paragraph("Improvement opportunities &amp; recommendations", h2))
    for p in data["priorities"]:
        el.append(Paragraph(f"<b>{p['category_name']}</b> — {_fmt(p['current'])} → target {_fmt(p['target'])}", body))
        for a in p["actions"]:
            el.append(Paragraph(f"• {a['title']}: {a['action']} <font color='#777777'>[evidence: {a['evidence_reference']}]</font>", body))
    if data["insights"]:
        el.append(Paragraph("Cross-wellness observations", h2))
        for i in data["insights"]:
            el.append(Paragraph("• " + i["message"], body))

    el.append(Paragraph("Next-quarter wellness plan", h2))
    plans = db.execute(select(UserWellnessPlan, WellnessRecommendation)
                       .join(WellnessRecommendation, WellnessRecommendation.recommendation_id == UserWellnessPlan.recommendation_id)
                       .where(UserWellnessPlan.user_id == subject.user_id, UserWellnessPlan.completion_status == "active")).all()
    if plans:
        for plan, rec in plans:
            el.append(Paragraph(f"• {rec.recommendation_title} — {rec.micro_habit} ({rec.suggested_frequency})", body))
    else:
        for h in (data["daily_habits"][:3] + data["weekly_habits"][:3]):
            el.append(Paragraph(f"• {h['habit']} ({h['frequency']})", body))

    if kind == "coach":
        el.append(Paragraph("Interview observations &amp; follow-ups", h2))
        q = select(InterviewRecord).where(InterviewRecord.user_id == subject.user_id).order_by(InterviewRecord.interview_date.desc())
        if viewer is not None and viewer.user_role != "individual":
            q = q.where(InterviewRecord.interviewer_id == viewer.user_id) if viewer.user_role == "coach" else q
        for iv in db.scalars(q.limit(10)):
            el.append(Paragraph(f"<b>{iv.interview_date.date().isoformat()}</b> — {iv.interview_summary or 'No summary'}", body))
            if iv.follow_up_plan:
                el.append(Paragraph(f"Agreed actions: {iv.follow_up_plan} (follow-up {iv.follow_up_date or 'TBD'})", body))
        if viewer is not None and viewer.user_role == "counselor":
            obs = db.scalars(select(ProfessionalObservation).where(ProfessionalObservation.user_id == subject.user_id,
                                                                   ProfessionalObservation.counselor_id == viewer.user_id))
            for o in obs:
                el.append(Paragraph(f"Counsellor note: {o.observation}" + (" — referral recommended" if o.referral_recommended else ""), body))
        el.append(Paragraph("Progress trend", h2))
        for tr in data["trend"]:
            el.append(Paragraph(f"{tr['period']}: overall {_fmt(tr['overall'])}", body))

    el.append(Spacer(1, 10))
    el.append(Paragraph(data["disclaimer"] + " If you are in distress, call Tele-MANAS 14416 (free, 24x7) or emergency 112.", small))
    doc.build(el)
    return buf.getvalue()
