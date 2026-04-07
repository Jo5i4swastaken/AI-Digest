from __future__ import annotations

import json
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests as _requests

from omniagents import function_tool


_AGENT_DIR = Path(__file__).resolve().parents[1]
_DATA_DIR = _AGENT_DIR / "data"
_OUTPUT_DIR = _AGENT_DIR / "output"
_STATE_PATH = _DATA_DIR / "state.json"
_ARCHIVE_DIR = _OUTPUT_DIR / "archive"
_REPO_DIGESTS_DIR = _AGENT_DIR.parent / "digests" / "archive"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(dt: str) -> Optional[datetime]:
    if not isinstance(dt, str) or not dt.strip():
        return None
    normalized = dt.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _local_tz() -> ZoneInfo:
    tz_name = os.getenv("TIMEZONE") or "America/Chicago"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("America/Chicago")


def _date_key() -> str:
    tz = _local_tz()
    # Use current wall-clock time in the configured timezone, not the
    # agent's generated_at (which may be rounded or slightly off).
    local = datetime.now(tz)
    return local.date().isoformat()


# ---------------------------------------------------------------------------
# Search helpers: SerpAPI primary, Tavily fallback
# ---------------------------------------------------------------------------

def _serpapi_request(params: Dict[str, Any]) -> tuple:
    """Make a SerpAPI HTTP request. Returns (data_dict, None) or (None, error_str)."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return None, "SERPAPI_API_KEY not set"
    params["api_key"] = api_key
    try:
        resp = _requests.get("https://serpapi.com/search", params=params, timeout=30)
        if resp.status_code != 200:
            return None, f"SerpAPI HTTP {resp.status_code}"
        return resp.json(), None
    except Exception as exc:
        return None, str(exc)


def _tavily_request(query: str, max_results: int = 10) -> tuple:
    """Tavily search fallback. Returns (data_dict, None) or (None, error_str)."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None, "TAVILY_API_KEY not set"
    try:
        resp = _requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None, f"Tavily HTTP {resp.status_code}"
        return resp.json(), None
    except Exception as exc:
        return None, str(exc)


@function_tool
def web_search(
    query: str,
    num_results: Optional[int] = None,
    include_news: Optional[bool] = None,
    time_period: Optional[str] = None,
) -> str:
    """Search the web using Google via SerpAPI with automatic Tavily fallback.

    Args:
        query: Search query string.
        num_results: Number of results to return (max 100). Recommend 10 for most queries.
        include_news: Whether to include news results (true or false).
        time_period: Time filter: null, "past_day", "past_week", "past_month", or "past_year".

    Returns:
        JSON string with search results.
    """
    n = min(num_results or 10, 100)
    news = include_news or False

    # --- SerpAPI attempt ---
    params: Dict[str, Any] = {"q": query, "num": n, "safe": "active", "gl": "us", "hl": "en"}
    if time_period:
        time_map = {"past_day": "d", "past_week": "w", "past_month": "m", "past_year": "y"}
        if time_period in time_map:
            params["tbs"] = f"qdr:{time_map[time_period]}"

    data, serp_err = _serpapi_request(params)
    if data:
        result: Dict[str, Any] = {"status": "success", "query": query, "source": "serpapi", "organic_results": []}
        for item in (data.get("organic_results") or [])[:n]:
            result["organic_results"].append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0),
                "displayed_link": item.get("displayed_link", ""),
            })
        if "answer_box" in data:
            result["answer_box"] = data["answer_box"]
        if "knowledge_graph" in data:
            result["knowledge_graph"] = data["knowledge_graph"]
        if news and "news_results" in data:
            result["news"] = data["news_results"][:n]
        return json.dumps(result, ensure_ascii=False)[:5000]

    # --- Tavily fallback ---
    tavily_data, tavily_err = _tavily_request(query, max_results=n)
    if tavily_data:
        result = {"status": "success", "query": query, "source": "tavily_fallback", "organic_results": []}
        for i, item in enumerate((tavily_data.get("results") or [])[:n], 1):
            result["organic_results"].append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": (item.get("content") or "")[:300],
                "position": i,
                "displayed_link": item.get("url", ""),
            })
        return json.dumps(result, ensure_ascii=False)[:5000]

    return json.dumps({"status": "error", "query": query, "error": f"SerpAPI: {serp_err}; Tavily: {tavily_err}"})


@function_tool
def youtube_search(
    query: str,
    num_results: Optional[int] = None,
    sort_by: Optional[str] = None,
    upload_date: Optional[str] = None,
    duration: Optional[str] = None,
) -> str:
    """Search YouTube for videos. Uses SerpAPI with automatic Tavily fallback.

    Args:
        query: Search query string.
        num_results: Number of results to return (max 100).
        sort_by: Sort order: "relevance", "upload_date", "view_count", "rating".
        upload_date: Filter by: "last_hour", "today", "this_week", "this_month", "this_year".
        duration: Filter by: "short" (<4min), "medium" (4-20min), "long" (>20min).

    Returns:
        JSON string with YouTube search results.
    """
    n = min(num_results or 10, 100)

    # --- SerpAPI YouTube engine ---
    params: Dict[str, Any] = {
        "search_query": query,
        "engine": "youtube",
        "num": n,
        "gl": "us",
        "hl": "en",
        "safe": "active",
    }

    sort_params = {"upload_date": "CAI%253D", "view_count": "CAM%253D", "rating": "CAE%253D"}
    sp_parts: List[str] = []
    if sort_by and sort_by in sort_params:
        sp_parts.append(sort_params[sort_by])

    date_filters = {
        "last_hour": "EgIIAQ%253D%253D",
        "today": "EgQIAhAB",
        "this_week": "EgQIAxAB",
        "this_month": "EgQIBBAB",
        "this_year": "EgQIBRAB",
    }
    if upload_date and upload_date in date_filters:
        sp_parts.append(date_filters[upload_date])

    duration_filters = {"short": "EgQQARgB", "medium": "EgQQARgC", "long": "EgQQARgD"}
    if duration and duration in duration_filters:
        sp_parts.append(duration_filters[duration])

    if sp_parts:
        params["sp"] = ",".join(sp_parts)

    data, serp_err = _serpapi_request(params)
    if data:
        result: Dict[str, Any] = {"status": "success", "query": query, "source": "serpapi", "videos": []}
        for item in (data.get("video_results") or [])[:n]:
            video: Dict[str, Any] = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "channel": {
                    "name": (item.get("channel") or {}).get("name", ""),
                    "link": (item.get("channel") or {}).get("link", ""),
                },
                "published_date": item.get("published_date", ""),
                "views": item.get("views", ""),
                "duration": item.get("duration_text", ""),
                "description": item.get("description", ""),
            }
            if "link" in item and "v=" in str(item["link"]):
                video["video_id"] = str(item["link"]).split("v=")[1].split("&")[0]
            result["videos"].append(video)
        return json.dumps(result, ensure_ascii=False)[:5000]

    # --- Tavily fallback: search YouTube via web ---
    yt_query = f"site:youtube.com {query}"
    tavily_data, tavily_err = _tavily_request(yt_query, max_results=n)
    if tavily_data:
        result = {"status": "success", "query": query, "source": "tavily_fallback", "videos": []}
        for item in (tavily_data.get("results") or [])[:n]:
            url = item.get("url", "")
            video = {
                "title": item.get("title", ""),
                "link": url,
                "channel": {"name": "", "link": ""},
                "published_date": item.get("published_date", ""),
                "views": "",
                "duration": "",
                "description": (item.get("content") or "")[:300],
            }
            if "v=" in url:
                video["video_id"] = url.split("v=")[1].split("&")[0]
            result["videos"].append(video)
        return json.dumps(result, ensure_ascii=False)[:5000]

    return json.dumps({"status": "error", "query": query, "error": f"SerpAPI: {serp_err}; Tavily: {tavily_err}"})


# ---------------------------------------------------------------------------

@dataclass
class DigestState:
    seen: Dict[str, str]


def _read_state() -> DigestState:
    if not _STATE_PATH.exists():
        return DigestState(seen={})

    try:
        payload = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return DigestState(seen={})

    seen = payload.get("seen", {})
    if not isinstance(seen, dict):
        seen = {}

    normalized: Dict[str, str] = {}
    for key, value in seen.items():
        if isinstance(key, str) and isinstance(value, str):
            normalized[key] = value

    return DigestState(seen=normalized)


def _write_state(state: DigestState) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": _utc_now_iso(),
        "seen": state.seen,
    }
    _STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


@function_tool
def load_digest_state() -> str:
    """Load dedupe state for previously sent items.

    Returns JSON string: {"seen": {"url": "ISO"}}.
    """

    state = _read_state()
    return json.dumps({"seen": state.seen}, ensure_ascii=False)


@function_tool
def save_digest_state(seen_json: str) -> str:
    """Persist dedupe state.

    Args:
        seen_json: JSON string containing a map of url -> ISO timestamp.

    Returns:
        JSON status payload.
    """

    try:
        seen = json.loads(seen_json)
    except Exception as exc:
        raise ValueError("seen_json must be valid JSON") from exc

    if not isinstance(seen, dict):
        raise ValueError("seen_json must decode to an object")

    normalized: Dict[str, str] = {}
    for key, value in seen.items():
        if isinstance(key, str) and isinstance(value, str) and key.strip():
            normalized[key.strip()] = value

    _write_state(DigestState(seen=normalized))
    return json.dumps(
        {"ok": True, "count": len(normalized), "path": str(_STATE_PATH)},
        ensure_ascii=False,
    )


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _send_gmail_email(
    subject: str,
    html_body: str,
    to_email: Optional[str] = None,
    from_email: Optional[str] = None,
) -> str:
    """Send an email via Gmail SMTP (TLS).

    Required env vars:
    - GMAIL_ADDRESS
    - GMAIL_APP_PASSWORD

    Optional env vars:
    - EMAIL_TO (used if to_email not provided)

    Args:
        subject: Email subject line.
        html_body: HTML body.
        to_email: Recipient email; falls back to EMAIL_TO.
        from_email: Sender email; defaults to GMAIL_ADDRESS.

    Returns:
        Status payload.
    """

    gmail_address = _env("GMAIL_ADDRESS")
    app_password = _env("GMAIL_APP_PASSWORD")

    resolved_to = (to_email or os.getenv("EMAIL_TO") or "").strip()
    if not resolved_to:
        raise RuntimeError("Missing recipient: provide to_email or set EMAIL_TO")

    resolved_from = (from_email or gmail_address).strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = resolved_from
    msg["To"] = resolved_to

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(gmail_address, app_password)
        server.sendmail(resolved_from, [resolved_to], msg.as_string())

    return json.dumps({"ok": True, "to": resolved_to, "from": resolved_from}, ensure_ascii=False)


@function_tool
def send_digest_email(
    digest_json: str,
    to_email: Optional[str] = None,
    from_email: Optional[str] = None,
) -> str:
    """Send a styled digest email. The HTML is rendered automatically from the digest JSON.

    Args:
        digest_json: The same digest JSON string passed to write_dashboard_files.
        to_email: Recipient email; falls back to EMAIL_TO env var.
        from_email: Sender email; defaults to GMAIL_ADDRESS env var.

    Returns:
        Status payload.
    """

    try:
        digest_obj = json.loads(digest_json)
    except Exception as exc:
        raise ValueError("digest_json must be valid JSON") from exc

    slot = str(digest_obj.get("slot", "")).strip()
    normalized = slot.lower()
    subject_map = {
        "am": "Morning AI Digest",
        "pm": "Afternoon AI Digest",
        "evening": "Evening AI Digest",
    }
    subject = subject_map.get(normalized)
    if not subject:
        raise ValueError("slot must be one of: AM, PM, Evening")

    html_body = _render_email_html(digest_obj)

    return _send_gmail_email(
        subject=subject,
        html_body=html_body,
        to_email=to_email,
        from_email=from_email,
    )


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _category_style(category: str) -> tuple:
    """Return (label, bg_color, text_color) for a category badge."""
    styles = {
        "product": ("Product", "#EEF2FF", "#4338CA"),
        "open_source": ("Open Source", "#F0FDF4", "#166534"),
        "agent_tooling": ("Agent Tooling", "#FFF7ED", "#9A3412"),
        "hardware": ("Hardware", "#FDF2F8", "#9D174D"),
        "funding": ("Funding", "#FFFBEB", "#92400E"),
        "ways_to_use": ("Ways to Use", "#F0F9FF", "#075985"),
    }
    label, bg, fg = styles.get(category, (category.replace("_", " ").title(), "#F3F4F6", "#374151"))
    return label, bg, fg


def _slot_greeting(slot: str) -> str:
    greetings = {"AM": "Good morning", "PM": "Good afternoon", "Evening": "Good evening"}
    return greetings.get(slot, "Hello")


def _format_date(iso_str: str) -> str:
    """Convert ISO-8601 string to 'Month Day, Year' format."""
    dt = _parse_iso(iso_str)
    if dt is None:
        return iso_str
    return dt.strftime("%B %d, %Y").replace(" 0", " ")


def _render_email_html(digest: Dict[str, Any]) -> str:
    slot = _escape_html(str(digest.get("slot", "")))
    raw_generated = str(digest.get("generated_at", ""))
    formatted_date = _escape_html(_format_date(raw_generated))
    items = digest.get("items", [])
    if not isinstance(items, list):
        items = []

    greeting = _slot_greeting(slot)
    slot_labels = {"AM": "Morning", "PM": "Afternoon", "Evening": "Evening"}
    slot_label = slot_labels.get(slot, slot)

    item_rows: List[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        title = _escape_html(str(item.get("title", "")))
        url = _escape_html(str(item.get("url", "")))
        source = _escape_html(str(item.get("source", "")))
        why = _escape_html(str(item.get("why_it_matters", "")))
        brief = _escape_html(str(item.get("brief", "")))
        details = _escape_html(str(item.get("details", "")))
        category = str(item.get("category", ""))
        is_update = item.get("is_update", False)

        cat_label, cat_bg, cat_fg = _category_style(category)
        update_badge = (
            '<span style="display:inline-block;padding:2px 8px;border-radius:10px;'
            'font-size:11px;font-weight:600;background:#FEF3C7;color:#92400E;'
            'margin-left:6px;">Update</span>'
            if is_update else ""
        )

        border_top = 'border-top:1px solid #E5E7EB;' if i > 0 else ''

        item_rows.append(
            f'''<tr><td style="padding:20px 28px;{border_top}">
              <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td>
                <span style="display:inline-block;padding:3px 10px;border-radius:12px;
                  font-size:11px;font-weight:600;background:{cat_bg};color:{cat_fg};
                  letter-spacing:0.3px;">{_escape_html(cat_label)}</span>
                {update_badge}
              </td></tr></table>
              <h3 style="margin:10px 0 6px;font-size:16px;font-weight:700;color:#111827;line-height:1.3;">
                <a href="{url}" style="color:#111827;text-decoration:none;">{title}</a>
              </h3>
              <p style="margin:0 0 8px;font-size:14px;color:#374151;line-height:1.5;">{brief}</p>
              <p style="margin:0 0 10px;font-size:13px;color:#6B7280;line-height:1.5;">{details}</p>
              <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
                <td style="font-size:12px;color:#9CA3AF;">
                  <em>{why}</em>
                </td>
                <td align="right" style="font-size:12px;">
                  <a href="{url}" style="color:#6366F1;text-decoration:none;font-weight:600;">{source} &rarr;</a>
                </td>
              </tr></table>
            </td></tr>'''
        )

    item_count = len(item_rows)

    slot_colors = {
        "AM": {
            "header": "linear-gradient(135deg,#F59E0B 0%,#F97316 100%)",
            "summary_bg": "#FFFBEB",
            "summary_border": "#FDE68A",
            "summary_fg": "#92400E",
        },
        "PM": {
            "header": "linear-gradient(135deg,#0EA5E9 0%,#2563EB 100%)",
            "summary_bg": "#EFF6FF",
            "summary_border": "#BFDBFE",
            "summary_fg": "#1E40AF",
        },
        "Evening": {
            "header": "linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)",
            "summary_bg": "#EEF2FF",
            "summary_border": "#E0E7FF",
            "summary_fg": "#4338CA",
        },
    }
    colors = slot_colors.get(slot, slot_colors["Evening"])
    header_gradient = colors["header"]
    summary_bg = colors["summary_bg"]
    summary_border = colors["summary_border"]
    summary_fg = colors["summary_fg"]

    return f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F3F4F6;-webkit-font-smoothing:antialiased;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%"
    style="background:#F3F4F6;padding:24px 16px;">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0" border="0" width="600"
        style="max-width:600px;width:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">

        <!-- Header -->
        <tr><td style="padding:32px 28px 24px;background:{header_gradient};
          border-radius:16px 16px 0 0;">
          <h1 style="margin:0 0 4px;font-size:24px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;">
            AI Digest
          </h1>
          <p style="margin:0;font-size:14px;color:rgba(255,255,255,0.8);">
            {greeting} &mdash; your {slot_label.lower()} briefing
          </p>
        </td></tr>

        <!-- Summary bar -->
        <tr><td style="padding:14px 28px;background:{summary_bg};border-bottom:1px solid {summary_border};">
          <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
            <td style="font-size:13px;color:{summary_fg};font-weight:600;">
              {item_count} item{"s" if item_count != 1 else ""} today
            </td>
            <td align="right" style="font-size:12px;color:{summary_fg};">
              {formatted_date}
            </td>
          </tr></table>
        </td></tr>

        <!-- Items -->
        <tr><td style="background:#FFFFFF;">
          <table cellpadding="0" cellspacing="0" border="0" width="100%">
            {"".join(item_rows)}
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 28px;background:#F9FAFB;border-top:1px solid #E5E7EB;
          border-radius:0 0 16px 16px;text-align:center;">
          <p style="margin:0;font-size:12px;color:#9CA3AF;line-height:1.5;">
            Generated by AI Digest Agent &middot; Powered by OmniAgents
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>'''


def _render_dashboard_html(index: List[Dict[str, Any]], *, tz_name: str) -> str:
    font_css = """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,700&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
    """.strip()

    cards: List[str] = []
    for day in index:
        day_key = _escape_html(str(day.get("date", "")))
        slots = day.get("slots", [])
        slot_cards: List[str] = []
        for slot in slots:
            slot_name = _escape_html(str(slot.get("slot", "")))
            href = _escape_html(str(slot.get("href", "")))
            top = slot.get("top", [])
            top_html = "".join(
                f"<li>{_escape_html(str(t))}</li>" for t in top[:4] if isinstance(t, str) and t.strip()
            )
            slot_cards.append(
                f"""
                <a class=\"slot\" href=\"{href}\">
                  <div class=\"slotHead\">
                    <div class=\"slotTitle\">{slot_name}</div>
                    <div class=\"slotMeta\">Open digest</div>
                  </div>
                  <ul class=\"slotList\">{top_html}</ul>
                </a>
                """
            )

        cards.append(
            f"""
            <section class=\"day\">
              <div class=\"dayHeader\">
                <div class=\"dayTitle\">{day_key}</div>
                <div class=\"daySub\">Timezone: {tz_name}</div>
              </div>
              <div class=\"grid\">{''.join(slot_cards)}</div>
            </section>
            """
        )

    body = "".join(cards) if cards else "<div class=\"empty\">No digests yet.</div>"

    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>AI Digest Dashboard</title>
    {font_css}
    <style>
      :root{{
        --bg0:#07090d;
        --bg1:#0d1120;
        --ink:#e9eefc;
        --muted:#aab4d6;
        --card:#0d1224cc;
        --line:#1f2a4d;
        --glow:#7b61ff;
        --glow2:#00d1ff;
        --accent:#f6d365;
      }}
      *{{box-sizing:border-box}}
      html,body{{height:100%}}
      body{{
        margin:0;
        color:var(--ink);
        font-family:"IBM Plex Sans", ui-sans-serif, system-ui;
        background:
          radial-gradient(1000px 600px at 12% 18%, color-mix(in oklab, var(--glow) 35%, transparent) 0%, transparent 60%),
          radial-gradient(900px 520px at 78% 22%, color-mix(in oklab, var(--glow2) 28%, transparent) 0%, transparent 62%),
          radial-gradient(800px 500px at 40% 88%, color-mix(in oklab, var(--accent) 18%, transparent) 0%, transparent 62%),
          linear-gradient(180deg, var(--bg0), var(--bg1));
      }}
      .wrap{{max-width:1100px;margin:0 auto;padding:32px 18px 60px;}}
      .top{{display:flex;gap:18px;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;}}
      .brand{{
        font-family:"Fraunces", serif;
        font-size:34px;
        letter-spacing:-0.02em;
        line-height:1.05;
      }}
      .tag{{color:var(--muted);font-size:14px;max-width:640px;}}
      .pillRow{{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;}}
      .pill{{
        border:1px solid var(--line);
        background:linear-gradient(180deg, #0f1630cc, #0b1022cc);
        padding:8px 12px;
        border-radius:999px;
        color:var(--muted);
        font-size:13px;
      }}
      .day{{margin-top:26px;}}
      .dayHeader{{display:flex;align-items:baseline;justify-content:space-between;gap:14px;margin-bottom:12px;}}
      .dayTitle{{font-family:"Fraunces", serif;font-size:22px;}}
      .daySub{{color:var(--muted);font-size:13px;}}
      .grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}}
      @media (max-width:980px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr));}}}}
      @media (max-width:640px){{.grid{{grid-template-columns:1fr;}}}}
      .slot{{
        text-decoration:none;
        color:inherit;
        border:1px solid var(--line);
        border-radius:18px;
        background:linear-gradient(180deg, #0e1430cc, #0a0f1fcc);
        padding:14px 14px 12px;
        position:relative;
        overflow:hidden;
        transition:transform .18s ease, border-color .18s ease;
      }}
      .slot:before{{
        content:"";
        position:absolute;
        inset:-2px;
        background:radial-gradient(600px 160px at 30% 0%, color-mix(in oklab, var(--glow) 26%, transparent), transparent 60%);
        opacity:.55;
        pointer-events:none;
      }}
      .slot:hover{{transform:translateY(-2px);border-color:color-mix(in oklab, var(--glow) 60%, var(--line));}}
      .slotHead{{display:flex;justify-content:space-between;align-items:baseline;gap:10px;position:relative;}}
      .slotTitle{{font-weight:700;letter-spacing:.01em;}}
      .slotMeta{{color:var(--muted);font-size:12px;}}
      .slotList{{margin:10px 0 0;padding-left:18px;color:var(--ink);opacity:.92;font-size:13px;line-height:1.35;position:relative;}}
      .slotList li{{margin:6px 0;}}
      .empty{{
        margin-top:28px;
        border:1px dashed var(--line);
        border-radius:18px;
        padding:18px;
        color:var(--muted);
      }}
      .footer{{margin-top:28px;color:var(--muted);font-size:12px;}}
      .footer a{{color:var(--muted);}}
    </style>
  </head>
  <body>
    <div class=\"wrap\">
      <div class=\"top\">
        <div>
          <div class=\"brand\">AI Digest Dashboard</div>
          <div class=\"tag\">Three snapshots a day. Click a card to open the digest HTML.</div>
          <div class=\"pillRow\">
            <div class=\"pill\">Morning · 8:00</div>
            <div class=\"pill\">Afternoon · 14:00</div>
            <div class=\"pill\">Evening · 20:00</div>
          </div>
        </div>
      </div>
      {body}
      <div class=\"footer\">Generated locally · Archive: <code>output/archive</code></div>
    </div>
  </body>
</html>"""


@function_tool
def write_dashboard_files(digest_json: str) -> str:
    """Write dashboard files: output/latest.json and output/latest.html.

    Also writes repo-backed digest JSON under `digests/archive/YYYY-MM-DD/<slot>.json`
    and updates `digests/archive/index.json`.

    Args:
        digest_json: Digest JSON string.

    Returns:
        JSON status payload with written paths.
    """

    try:
        digest_obj = json.loads(digest_json)
    except Exception as exc:
        raise ValueError("digest_json must be valid JSON") from exc

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _REPO_DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = _OUTPUT_DIR / "latest.json"
    html_path = _OUTPUT_DIR / "latest.html"
    index_path = _OUTPUT_DIR / "index.html"

    repo_index_path = _REPO_DIGESTS_DIR / "index.json"

    json_path.write_text(json.dumps(digest_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    html = _render_email_html(digest_obj)
    html_path.write_text(html, encoding="utf-8")

    day_key = _date_key()
    slot = str(digest_obj.get("slot", "")).strip() or "Unknown"
    safe_slot = "".join(ch for ch in slot if ch.isalnum() or ch in {"_", "-"})
    if not safe_slot:
        safe_slot = "Unknown"

    archive_day_dir = _ARCHIVE_DIR / day_key
    archive_day_dir.mkdir(parents=True, exist_ok=True)

    archive_json = archive_day_dir / f"{safe_slot}.json"
    archive_html = archive_day_dir / f"{safe_slot}.html"
    archive_json.write_text(json.dumps(digest_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    archive_html.write_text(html, encoding="utf-8")

    repo_day_dir = _REPO_DIGESTS_DIR / day_key
    repo_day_dir.mkdir(parents=True, exist_ok=True)
    repo_slot_json = repo_day_dir / f"{safe_slot}.json"
    repo_slot_json.write_text(json.dumps(digest_obj, indent=2, ensure_ascii=False), encoding="utf-8")

    tz_name = os.getenv("TIMEZONE") or "America/Chicago"
    day_dirs = sorted([p for p in _ARCHIVE_DIR.glob("*") if p.is_dir()], reverse=True)
    dashboard_index: List[Dict[str, Any]] = []
    for day_dir in day_dirs[:30]:
        day = day_dir.name
        slots: List[Dict[str, Any]] = []
        for slot_file in sorted(day_dir.glob("*.json")):
            try:
                payload = json.loads(slot_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            items = payload.get("items", [])
            titles: List[str] = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        title = item.get("title")
                        if isinstance(title, str) and title.strip():
                            titles.append(title.strip())

            slot_name = payload.get("slot") or slot_file.stem
            href = f"archive/{day}/{slot_file.stem}.html"
            slots.append({"slot": slot_name, "href": href, "top": titles})

        if slots:
            dashboard_index.append({"date": day, "slots": slots})

    index_path.write_text(_render_dashboard_html(dashboard_index, tz_name=tz_name), encoding="utf-8")

    def load_repo_index() -> Dict[str, Any]:
        if not repo_index_path.exists():
            return {"timezone": tz_name, "days": []}
        try:
            existing = json.loads(repo_index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"timezone": tz_name, "days": []}
        if not isinstance(existing, dict):
            return {"timezone": tz_name, "days": []}
        if "days" not in existing or not isinstance(existing.get("days"), list):
            existing["days"] = []
        existing["timezone"] = tz_name
        return existing

    repo_index = load_repo_index()
    days: List[Dict[str, Any]] = repo_index.get("days", [])

    def slot_label(raw: str) -> str:
        v = (raw or "").strip().lower()
        if v == "am":
            return "Morning"
        if v == "pm":
            return "Afternoon"
        if v == "evening":
            return "Evening"
        return raw or "Unknown"

    def top_titles(payload: Dict[str, Any]) -> List[str]:
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        titles: List[str] = []
        for item in items:
            if isinstance(item, dict):
                t = item.get("title")
                if isinstance(t, str) and t.strip():
                    titles.append(t.strip())
        return titles[:6]

    entry = {
        "slot": slot,
        "label": slot_label(slot),
        "path": f"{day_key}/{safe_slot}.json",
        "generated_at": digest_obj.get("generated_at"),
        "top": top_titles(digest_obj),
        "counts": {
            "total": len(digest_obj.get("items", []) or []),
        },
    }

    day_record = next((d for d in days if isinstance(d, dict) and d.get("date") == day_key), None)
    if day_record is None:
        day_record = {"date": day_key, "slots": []}
        days.append(day_record)
    slots_list = day_record.get("slots")
    if not isinstance(slots_list, list):
        slots_list = []
        day_record["slots"] = slots_list

    replaced = False
    for i, existing in enumerate(slots_list):
        if isinstance(existing, dict) and str(existing.get("slot", "")).strip() == slot:
            slots_list[i] = entry
            replaced = True
            break
    if not replaced:
        slots_list.append(entry)

    days.sort(key=lambda d: str(d.get("date", "")), reverse=True)
    for d in days:
        if isinstance(d, dict) and isinstance(d.get("slots"), list):
            d["slots"].sort(key=lambda s: {"AM": 0, "PM": 1, "Evening": 2}.get(str(s.get("slot")), 99))

    repo_index_path.write_text(json.dumps(repo_index, indent=2, ensure_ascii=False), encoding="utf-8")

    return json.dumps(
        {
            "ok": True,
            "json_path": str(json_path),
            "html_path": str(html_path),
            "index_path": str(index_path),
            "archive_json": str(archive_json),
            "archive_html": str(archive_html),
            "repo_slot_json": str(repo_slot_json),
            "repo_index_json": str(repo_index_path),
        },
        ensure_ascii=False,
    )
