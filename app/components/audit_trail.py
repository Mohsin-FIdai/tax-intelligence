"""
Audit Trail Renderer Component
Displays formatted investigation audit trail with severity colors and expandable details.
"""
import streamlit as st


def render_audit_trail(audit_data: dict):
    """
    Render a formatted audit trail with checkmarks, severity colors, and expandable details.

    Args:
        audit_data: Dictionary with structure:
            {
                "citizen_id": str,
                "name": str,
                "cnic": str,
                "generated_at": str,
                "checks": [
                    {
                        "check": str,          # Check name
                        "status": str,         # "pass", "fail", "warning"
                        "severity": str,       # "low", "medium", "high"
                        "detail": str,         # Description
                        "value": str/number,   # Actual value found
                        "threshold": str/number # Expected threshold (optional)
                    }
                ],
                "risk_score": float,
                "risk_category": str,
                "recommendation": str
            }
    """
    if not audit_data:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <div class="empty-title">No Audit Data</div>
                <div class="empty-detail">No audit trail is available for this entity.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Header
    name = audit_data.get("name", "Unknown")
    cnic = audit_data.get("cnic", "N/A")
    generated_at = audit_data.get("generated_at", "N/A")
    risk_score = audit_data.get("risk_score", 0)
    risk_category = audit_data.get("risk_category", "A")
    recommendation = audit_data.get("recommendation", "")

    st.markdown(
        f"""
        <div class="section-header">
            <span class="section-icon">📋</span>
            <h3>Audit Trail — {name}</h3>
        </div>
        <div style="display:flex;gap:24px;margin-bottom:16px;flex-wrap:wrap;">
            <div style="color:#8888a0;font-size:0.82rem;">
                CNIC: <span style="color:#e8e8ed;font-weight:600;">{cnic}</span>
            </div>
            <div style="color:#8888a0;font-size:0.82rem;">
                Generated: <span style="color:#e8e8ed;font-weight:600;">{generated_at}</span>
            </div>
            <div style="color:#8888a0;font-size:0.82rem;">
                Risk Score: <span style="color:{_risk_color(risk_category)};font-weight:700;">{risk_score:.1f}</span>
            </div>
            <div>
                <span class="risk-badge risk-badge-{risk_category}">{_risk_label(risk_category)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render checks
    checks = audit_data.get("checks", [])
    if not checks:
        st.info("No audit checks found.")
        return

    html_items = []
    for check in checks:
        status = check.get("status", "pass")
        severity = check.get("severity", "low")
        check_name = check.get("check", "Unknown Check")
        detail = check.get("detail", "")
        value = check.get("value", "")
        threshold = check.get("threshold", "")

        # Status icon
        icon_map = {
            "pass": "✅",
            "fail": "❌",
            "warning": "⚠️",
        }
        icon = icon_map.get(status, "ℹ️")

        # Build value info
        value_html = ""
        if value:
            value_html = f'<span style="color:#e8e8ed;">Value: <b>{value}</b></span>'
            if threshold:
                value_html += f' <span style="color:#8888a0;">/ Threshold: <b>{threshold}</b></span>'

        html_items.append(
            f"""
            <div class="audit-item severity-{severity}" style="animation-delay:{len(html_items)*0.05}s;">
                <div class="audit-icon">{icon}</div>
                <div class="audit-content">
                    <div class="audit-title">{check_name}</div>
                    <div class="audit-detail">{detail}</div>
                    {f'<div class="audit-meta">{value_html}</div>' if value_html else ''}
                </div>
            </div>
            """
        )

    st.markdown(
        f'<div class="audit-trail">{"".join(html_items)}</div>',
        unsafe_allow_html=True,
    )

    # Recommendation
    if recommendation:
        st.markdown(
            f"""
            <div style="margin-top:16px;padding:12px 16px;background:rgba(0,212,170,0.06);
                        border:1px solid rgba(0,212,170,0.15);border-radius:8px;">
                <div style="color:#00d4aa;font-weight:700;font-size:0.82rem;margin-bottom:4px;
                            text-transform:uppercase;letter-spacing:0.05em;">
                    💡 Recommendation
                </div>
                <div style="color:#e8e8ed;font-size:0.88rem;line-height:1.6;">
                    {recommendation}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_audit_from_citizen(citizen_row: dict) -> dict:
    """
    Build an audit trail dictionary from a citizen data row.
    Automatically generates checks based on available data.

    Args:
        citizen_row: Dictionary of citizen data (from DataFrame row)

    Returns:
        Audit data dictionary
    """
    checks = []
    risk_score = citizen_row.get("risk_score", citizen_row.get("deviation_score", 0))
    category = citizen_row.get("risk_category", "A")

    # Filing status check
    filing_status = citizen_row.get("filing_status", "Unknown")
    checks.append({
        "check": "Tax Filing Status",
        "status": "pass" if filing_status == "Filer" else "fail",
        "severity": "low" if filing_status == "Filer" else "high",
        "detail": f"Citizen is registered as: {filing_status}",
        "value": filing_status,
    })

    # Income-Net Worth gap
    declared_income = citizen_row.get("declared_income", 0)
    net_worth = citizen_row.get("estimated_net_worth", citizen_row.get("net_worth", 0))
    if declared_income and net_worth:
        gap_ratio = net_worth / max(declared_income, 1)
        gap_status = "pass" if gap_ratio < 3 else ("warning" if gap_ratio < 6 else "fail")
        gap_severity = "low" if gap_ratio < 3 else ("medium" if gap_ratio < 6 else "high")
        checks.append({
            "check": "Income vs Net Worth Gap Analysis",
            "status": gap_status,
            "severity": gap_severity,
            "detail": f"Net worth is {gap_ratio:.1f}x declared income.",
            "value": f"PKR {net_worth:,.0f}",
            "threshold": f"< 3x income (PKR {declared_income:,.0f})",
        })

    # Vehicle ownership check
    num_vehicles = citizen_row.get("num_vehicles", 0)
    if num_vehicles:
        v_status = "pass" if num_vehicles <= 2 else "warning"
        checks.append({
            "check": "Vehicle Ownership Review",
            "status": v_status,
            "severity": "low" if num_vehicles <= 2 else "medium",
            "detail": f"Citizen owns {num_vehicles} registered vehicle(s).",
            "value": num_vehicles,
            "threshold": "≤ 2 typical",
        })

    # Property check
    num_properties = citizen_row.get("num_properties", 0)
    if num_properties:
        p_status = "pass" if num_properties <= 2 else "warning"
        checks.append({
            "check": "Property Holdings Review",
            "status": p_status,
            "severity": "low" if num_properties <= 2 else "medium",
            "detail": f"Citizen owns {num_properties} registered properties.",
            "value": num_properties,
        })

    # Risk score evaluation
    checks.append({
        "check": "Composite Risk Score Evaluation",
        "status": "pass" if risk_score < 40 else ("warning" if risk_score < 60 else "fail"),
        "severity": "low" if risk_score < 40 else ("medium" if risk_score < 60 else "high"),
        "detail": f"Composite deviation score is {risk_score:.1f}/100.",
        "value": f"{risk_score:.1f}",
        "threshold": "< 40 safe",
    })

    # Anomaly flag
    anomaly_flag = citizen_row.get("anomaly_flag", citizen_row.get("is_anomaly", 0))
    if anomaly_flag:
        checks.append({
            "check": "ML Anomaly Detection Flag",
            "status": "fail",
            "severity": "high",
            "detail": "Machine learning model has flagged this citizen as a statistical anomaly.",
            "value": "FLAGGED",
        })
    else:
        checks.append({
            "check": "ML Anomaly Detection Flag",
            "status": "pass",
            "severity": "low",
            "detail": "No anomaly detected by the ML model.",
            "value": "CLEAR",
        })

    # Build recommendation
    if risk_score >= 80:
        recommendation = "Immediate investigation recommended. Multiple high-severity flags detected. Escalate to senior tax officer for field verification."
    elif risk_score >= 60:
        recommendation = "Priority review required. Significant discrepancies found. Schedule audit within 30 days."
    elif risk_score >= 40:
        recommendation = "Moderate risk. Some inconsistencies detected. Include in next batch review cycle."
    else:
        recommendation = "Low risk profile. No immediate action required. Continue routine monitoring."

    return {
        "citizen_id": citizen_row.get("citizen_id", ""),
        "name": citizen_row.get("name", citizen_row.get("full_name", "Unknown")),
        "cnic": citizen_row.get("cnic", "N/A"),
        "generated_at": "Auto-generated",
        "checks": checks,
        "risk_score": risk_score,
        "risk_category": category,
        "recommendation": recommendation,
    }


def _risk_color(category: str) -> str:
    colors = {"A": "#00d4aa", "B": "#4a9eff", "C": "#ffd000", "D": "#ff8c00", "E": "#ff3355"}
    return colors.get(category, "#8888a0")


def _risk_label(category: str) -> str:
    labels = {
        "A": "Tax Compliant",
        "B": "Needs Review",
        "C": "Suspicious",
        "D": "Likely Tax Evader",
        "E": "Confirmed Tax Deviation",
    }
    return labels.get(category, "Unknown")
