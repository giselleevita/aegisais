"""Build PDF summaries of alerts for a time range (admin reports)."""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.api.validators import validate_mmsi
from app.modules.alerts.models import Alert
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter
_MAX_RANGE = timedelta(days=366)
_TOP_MMSI = 20


def _base_query(
    db: Session,
    user: User,
    *,
    start_time: datetime,
    end_time: datetime,
    mmsi: Optional[list[str]],
    zone_substring: Optional[str],
):
    q = db.query(Alert)
    q = apply_org_filter(q, Alert, user)
    q = q.filter(
        Alert.timestamp >= start_time,
        Alert.timestamp <= end_time,
    )
    if mmsi:
        for m in mmsi:
            validate_mmsi(m)
        q = q.filter(Alert.mmsi.in_(mmsi))
    if zone_substring and zone_substring.strip():
        z = zone_substring.strip()
        ev = cast(Alert.evidence, String)
        q = q.filter(or_(Alert.summary.contains(z), ev.contains(z)))
    return q


def validate_report_window(start_time: datetime, end_time: datetime) -> None:
    if end_time - start_time > _MAX_RANGE:
        raise ValueError(f"Time range must not exceed {_MAX_RANGE.days} days")


def build_alerts_pdf(
    db: Session,
    user: User,
    *,
    start_time: datetime,
    end_time: datetime,
    mmsi: Optional[list[str]] = None,
    zone_substring: Optional[str] = None,
) -> BytesIO:
    validate_report_window(start_time, end_time)

    from reportlab.lib import colors  # type: ignore[import-untyped]
    from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
    from reportlab.platypus import (  # type: ignore[import-untyped]
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    def q():
        return _base_query(
            db,
            user,
            start_time=start_time,
            end_time=end_time,
            mmsi=mmsi,
            zone_substring=zone_substring,
        )

    total = q().count()

    by_type_rows = (
        q()
        .with_entities(Alert.type, func.count(Alert.id).label("c"))
        .group_by(Alert.type)
        .order_by(func.count(Alert.id).desc())
        .all()
    )

    high = q().filter(Alert.severity >= 70).count()
    medium = q().filter(Alert.severity >= 30, Alert.severity < 70).count()
    low = q().filter(Alert.severity < 30).count()

    top_mmsi_rows = (
        q()
        .with_entities(Alert.mmsi, func.count(Alert.id).label("c"))
        .group_by(Alert.mmsi)
        .order_by(func.count(Alert.id).desc())
        .limit(_TOP_MMSI)
        .all()
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="AegisAIS alerts report")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AegisAIS — Alerts summary report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            f"<b>Period:</b> {start_time.isoformat()} — {end_time.isoformat()}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Total alerts:</b> {total}",
            styles["Normal"],
        )
    )
    if mmsi:
        story.append(
            Paragraph(
                f"<b>MMSI filter:</b> {', '.join(mmsi)}",
                styles["Normal"],
            )
        )
    if zone_substring and zone_substring.strip():
        story.append(
            Paragraph(
                f"<b>Zone / summary substring:</b> {zone_substring.strip()}",
                styles["Normal"],
            )
        )
    story.append(Spacer(1, 18))

    story.append(Paragraph("Counts by alert type", styles["Heading2"]))
    type_data = [["Type", "Count"]]
    for t, c in by_type_rows:
        type_data.append([str(t), str(c)])
    if len(type_data) == 1:
        type_data.append(["(none)", "0"])
    t1 = Table(type_data, colWidths=[320, 80])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Counts by severity band", styles["Heading2"]))
    sev_data = [
        ["Band", "Rule", "Count"],
        ["High", "severity 70–100", str(high)],
        ["Medium", "severity 30–69", str(medium)],
        ["Low", "severity 0–29", str(low)],
    ]
    t2 = Table(sev_data, colWidths=[80, 200, 80])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 18))

    story.append(Paragraph(f"Top {_TOP_MMSI} MMSIs by alert count", styles["Heading2"]))
    mms_data = [["MMSI", "Alerts"]]
    for m, c in top_mmsi_rows:
        mms_data.append([str(m), str(c)])
    if len(mms_data) == 1:
        mms_data.append(["(none)", "0"])
    t3 = Table(mms_data, colWidths=[120, 80])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t3)

    doc.build(story)
    buf.seek(0)
    return buf
