from html import escape
from textwrap import dedent
from urllib.parse import urlparse
import time

from openai import OpenAI
import pandas as pd
import streamlit as st

from modules.claim_finder import extract_claims
from modules.pdf_extractor import extract_text
from modules.verdict_engine import get_verdict
from modules.web_verifier import search_claim

APP_VERSION = "0.0.2"

def html_block(markup: str) -> str:
    return "\n".join(line.strip() for line in dedent(markup).strip().splitlines())


# Fitness-themed SVG icons
SVG_HERO = html_block("""
<svg class="hero-mark-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M12 18l24 12M12 30l24-12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="24" cy="24" r="9" fill="none" stroke="currentColor" stroke-width="2.5"/>
    <path d="M24 15v18M15 24h18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
</svg>
""")

SVG_DOCUMENT = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M13 6h16l8 8v28H13z" fill="#1a1a1a" stroke="#00ff87" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M29 6v9h8" fill="none" stroke="#00ff87" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M19 23h12M19 29h12M19 35h8" fill="none" stroke="#00ff87" stroke-width="2.4" stroke-linecap="round"/>
</svg>
""")

SVG_CLAIMS = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <circle cx="21" cy="21" r="10" fill="#1a1a1a" stroke="#00ff87" stroke-width="2.6"/>
    <path d="M29 29l9 9" fill="none" stroke="#00ff87" stroke-width="3" stroke-linecap="round"/>
    <path d="M16 21h10M21 16v10" fill="none" stroke="#00ff87" stroke-width="2.4" stroke-linecap="round"/>
</svg>
""")

SVG_SEARCH = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <circle cx="24" cy="24" r="16" fill="#1a1a1a" stroke="#00ff87" stroke-width="2.5"/>
    <path d="M8 24h32M24 8c4 4.4 6 9.7 6 16s-2 11.6-6 16M24 8c-4 4.4-6 9.7-6 16s2 11.6 6 16" fill="none" stroke="#00ff87" stroke-width="2.2" stroke-linecap="round"/>
</svg>
""")

SVG_VERDICT = html_block("""
<svg class="process-icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M24 7v7M14 14h20M17 14l-7 15h14zM31 14l-7 15h14z" fill="none" stroke="#00ff87" stroke-width="2.5" stroke-linejoin="round"/>
    <path d="M18 39h12M24 29v10" fill="none" stroke="#00ff87" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M18 30c1.5 2 3.5 3 6 3s4.5-1 6-3" fill="none" stroke="#00ff87" stroke-width="2.5" stroke-linecap="round"/>
</svg>
""")

SVG_CHECK = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M4.5 10.2l3.3 3.3 7.7-8.2" fill="none" stroke="#00ff87" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
""")

SVG_ALERT = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M10 3l7 13H3z" fill="none" stroke="#ff4444" stroke-width="1.9" stroke-linejoin="round"/>
    <path d="M10 7.3v4.4M10 14.6h.01" fill="none" stroke="#ff4444" stroke-width="2.1" stroke-linecap="round"/>
</svg>
""")

SVG_X = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M5.5 5.5l9 9M14.5 5.5l-9 9" fill="none" stroke="#ff4444" stroke-width="2.2" stroke-linecap="round"/>
</svg>
""")

SVG_HELP = html_block("""
<svg class="badge-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <circle cx="10" cy="10" r="7" fill="none" stroke="#ffa500" stroke-width="1.9"/>
    <path d="M7.8 7.8a2.4 2.4 0 0 1 4.6 1c0 1.9-2.4 2-2.4 3.7M10 15h.01" fill="none" stroke="#ffa500" stroke-width="1.9" stroke-linecap="round"/>
</svg>
""")

SVG_LINK = html_block("""
<svg class="inline-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M8.2 11.8a3.2 3.2 0 0 1 0-4.5l1.7-1.7a3.2 3.2 0 0 1 4.5 4.5l-.9.9" fill="none" stroke="#00ff87" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M11.8 8.2a3.2 3.2 0 0 1 0 4.5l-1.7 1.7a3.2 3.2 0 0 1-4.5-4.5l.9-.9" fill="none" stroke="#00ff87" stroke-width="1.8" stroke-linecap="round"/>
</svg>
""")

SVG_PIN = html_block("""
<svg class="inline-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
    <path d="M10 2.8l4.4 4.4-2.2 2.2 2.4 4.8-.8.8L9 12.6 6 15.6 4.4 14l3-3-2.4-4.8.8-.8 4.2 2z" fill="none" stroke="#00ff87" stroke-width="1.7" stroke-linejoin="round"/>
</svg>
""")


PROCESS_STEPS = [
    ("01", SVG_DOCUMENT, "UPLOAD PDF", "Document parsed into clean text for analysis"),
    ("02", SVG_CLAIMS, "EXTRACT CLAIMS", "AI isolates verifiable facts and figures"),
    ("03", SVG_SEARCH, "SEARCH EVIDENCE", "Claims checked against current web evidence"),
    ("04", SVG_VERDICT, "GENERATE VERDICT", "Claim scored with confidence and sources"),
]


def source_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "")
    return host or url[:48]


def verdict_icon(verdict: str) -> str:
    return {
        "VERIFIED": SVG_CHECK,
        "INACCURATE": SVG_ALERT,
        "FALSE": SVG_X,
        "ERROR": SVG_HELP,
    }.get(verdict, SVG_HELP)


def verdict_classes(verdict: str) -> tuple[str, str]:
    return {
        "VERIFIED": ("verdict-verified", "badge-verified"),
        "INACCURATE": ("verdict-inaccurate", "badge-inaccurate"),
        "FALSE": ("verdict-false", "badge-false"),
        "ERROR": ("verdict-error", "badge-error"),
    }.get(verdict, ("verdict-error", "badge-error"))


def render_process_visual() -> str:
    cards = []
    for number, icon, title, body in PROCESS_STEPS:
        cards.append(
            html_block(f"""
            <div class="process-card">
                <div class="process-topline">
                    <span class="process-number">{number}</span>
                    {icon}
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
            </div>
            """)
        )

    return html_block(f"""
    <div class="workflow-section" role="region" aria-label="Verification workflow">
        <div class="section-kicker">VERIFICATION WORKFLOW</div>
        <h2 class="workflow-title">FROM DOCUMENT TO EVIDENCE-BACKED VERDICT</h2>
        <div class="process-grid">
            {''.join(cards)}
        </div>
    </div>
    """)


def render_sources(sources) -> str:
    if not sources:
        return ""

    if isinstance(sources, str):
        source_list = [sources]
    else:
        source_list = list(sources)

    links = []
    for source in source_list[:2]:
        if not source:
            continue
        source_url = escape(str(source), quote=True)
        label = escape(source_label(str(source)))
        links.append(f'<a class="source-link" href="{source_url}" target="_blank" rel="noopener noreferrer">{label}</a>')

    if not links:
        return ""

    return html_block(f"""
    <div class="sources-row">
        {SVG_LINK}
        <span>SOURCES</span>
        {' '.join(links)}
    </div>
    """)


def render_correction(correct_fact) -> str:
    if not correct_fact or correct_fact == "null":
        return ""

    return html_block(f"""
    <div class="correction-text">
        {SVG_PIN}
        <span>CORRECT FACT: {escape(str(correct_fact))}</span>
    </div>
    """)



STAGE_LABELS = ["UPLOAD", "EXTRACTING", "FINDING CLAIMS", "CHECKING EVIDENCE", "REPORT READY"]


def init_session_state() -> None:
    defaults = {
        "upload_key": 0,
        "stage": "UPLOAD",
        "results": [],
        "word_count": 0,
        "claim_count": 0,
        "active_file_name": None,
        "active_file_size": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_upload_state() -> None:
    st.session_state.upload_key += 1
    st.session_state.stage = "UPLOAD"
    st.session_state.results = []
    st.session_state.word_count = 0
    st.session_state.claim_count = 0
    st.session_state.active_file_name = None
    st.session_state.active_file_size = 0


def set_stage(stage: str, placeholder=None) -> None:
    st.session_state.stage = stage
    if placeholder is not None:
        placeholder.markdown(render_stage_bar(stage), unsafe_allow_html=True)


def render_stage_bar(current_stage: str) -> str:
    try:
        current_index = STAGE_LABELS.index(current_stage)
    except ValueError:
        current_index = 0

    items = []
    for index, label in enumerate(STAGE_LABELS):
        if index < current_index:
            state_class = "is-done"
        elif index == current_index:
            state_class = "is-current"
        else:
            state_class = "is-next"

        items.append(
            html_block(f"""
            <div class="stage-item {state_class}">
                <span class="stage-dot">{index + 1}</span>
                <span>{label}</span>
            </div>
            """)
        )

    return html_block(f"""
    <div class="stage-shell">
        <div class="stage-label">CURRENT STAGE</div>
        <div class="stage-row">{''.join(items)}</div>
    </div>
    """)


def render_stats(results: list[dict]) -> str:
    verified_count = sum(1 for result in results if result.get("verdict") == "VERIFIED")
    inaccurate_count = sum(1 for result in results if result.get("verdict") == "INACCURATE")
    false_count = sum(1 for result in results if result.get("verdict") == "FALSE")
    error_count = sum(1 for result in results if result.get("verdict") == "ERROR")

    return html_block(f"""
    <div class="stats-container">
        <div class="stat-card stat-total">
            <div class="stat-number">{len(results)}</div>
            <div class="stat-label">CLAIMS</div>
        </div>
        <div class="stat-card stat-verified">
            <div class="stat-number">{verified_count}</div>
            <div class="stat-label">VERIFIED</div>
        </div>
        <div class="stat-card stat-inaccurate">
            <div class="stat-number">{inaccurate_count}</div>
            <div class="stat-label">INACCURATE</div>
        </div>
        <div class="stat-card stat-false">
            <div class="stat-number">{false_count}</div>
            <div class="stat-label">FALSE</div>
        </div>
        <div class="stat-card stat-error">
            <div class="stat-number">{error_count}</div>
            <div class="stat-label">ERRORS</div>
        </div>
    </div>
    """)


st.set_page_config(
    page_title="FACT-CHECK AGENT | AI-Powered Verification",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()

st.markdown(
    html_block("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

    :root {
        --primary: #00ff87;
        --primary-dark: #00cc6a;
        --primary-glow: rgba(0, 255, 135, 0.3);
        --bg-dark: #0a0a0a;
        --bg-card: #1a1a1a;
        --bg-surface: #141414;
        --ink: #ffffff;
        --muted: #888888;
        --line: #2a2a2a;
        --surface: #1e1e1e;
        --surface-alt: #161616;
        --teal: #00ff87;
        --green: #00ff87;
        --amber: #ffa500;
        --red: #ff4444;
        --slate: #666666;
        --shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        --neon-glow: 0 0 20px rgba(0, 255, 135, 0.3);
    }

    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #0d0d0d 50%, #0a0a0a 100%);
        color: var(--ink);
        font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
    }

    /* Hide default Streamlit elements */
    #MainMenu, header, footer, .stDeployButton, div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }

    /* Hero Section */
    .hero-container {
        text-align: center;
        padding: 2rem 1rem;
        margin-bottom: 1rem;
        background: linear-gradient(180deg, rgba(0, 255, 135, 0.05) 0%, transparent 100%);
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        border: 1px solid var(--primary);
        border-radius: 50px;
        padding: 8px 20px;
        color: var(--primary);
        background: rgba(0, 255, 135, 0.1);
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 25px;
        backdrop-filter: blur(10px);
    }

    .hero-mark-icon {
        width: 22px;
        height: 22px;
        color: var(--primary);
    }

    .hero-title {
        margin: 0;
        color: var(--ink);
        font-size: 4rem;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #ffffff 0%, var(--primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-title span {
        background: linear-gradient(135deg, var(--primary) 0%, #00ffcc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        max-width: 700px;
        margin: 20px auto 0;
        color: var(--muted);
        font-size: 1.1rem;
        line-height: 1.6;
    }

    /* Workflow Section */
    .workflow-section {
        margin: 2rem 0 2rem;
        padding: 2rem 0 1rem;
        border-top: 1px solid rgba(0, 255, 135, 0.15);
    }

    .section-kicker {
        color: var(--primary);
        font-size: 0.8rem;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        text-align: center;
    }

    .workflow-title {
        margin: 12px 0 30px;
        color: var(--ink);
        text-align: center;
        font-size: 1.6rem;
        line-height: 1.3;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .process-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 20px;
    }

    .process-card {
        position: relative;
        padding: 24px 20px;
        border: 1px solid rgba(0, 255, 135, 0.2);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.9), rgba(20, 20, 20, 0.95));
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
    }

    .process-card:hover {
        transform: translateY(-5px);
        border-color: var(--primary);
        box-shadow: var(--neon-glow);
    }

    .process-card:not(:last-child)::after {
        content: "→";
        position: absolute;
        top: 50%;
        right: -18px;
        transform: translateY(-50%);
        color: var(--primary);
        font-size: 1.5rem;
        font-weight: bold;
    }

    .process-topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 20px;
    }

    .process-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 32px;
        border-radius: 8px;
        color: var(--bg-dark);
        background: var(--primary);
        font-size: 0.85rem;
        font-weight: 800;
    }

    .process-icon {
        width: 52px;
        height: 52px;
        color: var(--primary);
        filter: drop-shadow(0 0 5px var(--primary-glow));
    }

    .process-card h3 {
        margin: 0 0 12px;
        color: var(--primary);
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: 1px;
    }

    .process-card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* File Uploader */
    div[data-testid="stFileUploader"] {
        margin: 1rem 0;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        position: relative;
        min-height: 200px;
        border: 2px dashed rgba(0, 255, 135, 0.3);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(0, 255, 135, 0.05), rgba(0, 0, 0, 0.2));
        transition: all 0.3s ease;
        cursor: pointer;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--primary);
        background: rgba(0, 255, 135, 0.08);
        transform: translateY(-2px);
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::before {
        content: "💪";
        font-size: 48px;
        display: block;
        text-align: center;
        margin-bottom: 10px;
    }

    div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]::after {
        content: "DROP PDF HERE OR CLICK TO UPLOAD";
        color: var(--primary);
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 1px;
    }

    /* Uploaded File Display */
    .uploaded-file {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin: 0 0 16px;
        padding: 14px 18px;
        border: 1px solid rgba(0, 255, 135, 0.3);
        border-radius: 12px;
        background: rgba(0, 255, 135, 0.1);
        color: var(--primary);
        font-size: 0.9rem;
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        min-height: 48px;
        border: 2px solid var(--primary);
        border-radius: 12px;
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: var(--bg-dark);
        font-weight: 800;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: var(--neon-glow);
        border-color: var(--primary);
    }

    /* Stats Container */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(5, minmax(100px, 1fr));
        gap: 15px;
        margin: 1.5rem 0;
    }

    .stat-card {
        padding: 18px;
        border: 1px solid rgba(0, 255, 135, 0.2);
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.8), rgba(20, 20, 20, 0.9));
        text-align: center;
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        border-color: var(--primary);
        transform: translateY(-2px);
    }

    .stat-number {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--primary);
    }

    .stat-label {
        margin-top: 8px;
        color: var(--muted);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 1px;
    }

    /* Verdict Cards */
    .verdict-card {
        border: 1px solid var(--line);
        border-left: 5px solid;
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.9), rgba(20, 20, 20, 0.95));
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }

    .verdict-card:hover {
        transform: translateX(5px);
        box-shadow: var(--shadow);
    }

    .verdict-verified { border-left-color: var(--green); }
    .verdict-inaccurate { border-left-color: var(--amber); }
    .verdict-false { border-left-color: var(--red); }
    .verdict-error { border-left-color: var(--slate); }

    .verdict-header {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 12px;
    }

    .verdict-badge, .confidence-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .badge-verified { color: var(--green); background: rgba(0, 255, 135, 0.15); border: 1px solid rgba(0, 255, 135, 0.3); }
    .badge-inaccurate { color: var(--amber); background: rgba(255, 165, 0, 0.15); border: 1px solid rgba(255, 165, 0, 0.3); }
    .badge-false { color: var(--red); background: rgba(255, 68, 68, 0.15); border: 1px solid rgba(255, 68, 68, 0.3); }
    .badge-error { color: var(--slate); background: rgba(102, 102, 102, 0.15); border: 1px solid rgba(102, 102, 102, 0.3); }

    .confidence-badge {
        color: var(--primary);
        background: rgba(0, 255, 135, 0.1);
    }

    .claim-meta {
        margin-left: auto;
        color: var(--muted);
        font-size: 0.7rem;
        font-weight: 600;
    }

    .claim-text {
        margin: 12px 0 10px;
        color: var(--ink);
        font-size: 1rem;
        font-weight: 600;
        line-height: 1.5;
    }

    .explanation-text {
        color: var(--muted);
        font-size: 0.85rem;
        line-height: 1.6;
    }

    .correction-text, .sources-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 12px;
        padding: 10px 14px;
        background: rgba(0, 255, 135, 0.05);
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .source-link {
        color: var(--primary);
        text-decoration: none;
        border-bottom: 1px solid var(--primary);
    }

    .source-link:hover {
        color: var(--primary-dark);
    }

    /* Stage Bar */
    .stage-shell {
        position: sticky;
        top: 0.75rem;
        z-index: 10;
        padding: 1rem;
        border: 1px solid rgba(0, 255, 135, 0.2);
        border-radius: 12px;
        background: rgba(20, 20, 20, 0.95);
        backdrop-filter: blur(12px);
        margin-bottom: 1rem;
    }

    .stage-label {
        color: var(--primary);
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }

    .stage-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
    }

    .stage-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px;
        border: 1px solid rgba(0, 255, 135, 0.2);
        border-radius: 8px;
        background: var(--bg-surface);
        font-size: 0.7rem;
        font-weight: 700;
    }

    .stage-item.is-current {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: var(--bg-dark);
        border-color: var(--primary);
    }

    .stage-item.is-done {
        border-color: var(--primary);
        color: var(--primary);
    }

    /* Control Panel */
    .control-panel, .result-panel, .empty-panel {
        border: 1px solid rgba(0, 255, 135, 0.15);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.8), rgba(20, 20, 20, 0.9));
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .app-kicker {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: var(--primary);
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 15px;
    }

    .control-title {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0.5rem 0;
    }

    .control-title span {
        color: var(--primary);
    }

    .control-copy {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* Responsive */
    @media (max-width: 920px) {
        .process-grid, .stats-container {
            grid-template-columns: repeat(2, 1fr);
        }
        .process-card:not(:last-child)::after {
            display: none;
        }
        .hero-title {
            font-size: 2.5rem;
        }
    }

    @media (max-width: 640px) {
        .process-grid, .stats-container, .stage-row {
            grid-template-columns: 1fr;
        }
        .control-title {
            font-size: 1.8rem;
        }
    }

    /* Progress Bar */
    div[data-testid="stProgressBar"] > div > div > div {
        background-color: var(--primary);
        box-shadow: var(--neon-glow);
    }

    /* Select Box */
    div[data-baseweb="select"] > div {
        background: var(--bg-surface);
        border-color: rgba(0, 255, 135, 0.3);
        border-radius: 8px;
    }

    /* Version indicator */
    .version-tag {
        position: fixed;
        bottom: 15px;
        left: 15px;
        font-size: 0.7rem;
        color: var(--muted);
        font-family: monospace;
        z-index: 9999;
    }
</style>
"""),
    unsafe_allow_html=True,
)

st.markdown(
    html_block(f"""
    <div class="hero-container">
        <div class="hero-badge">
            {SVG_HERO}
            AI-POWERED VERIFICATION
        </div>
        <h1 class="hero-title">FACT-CHECK <span>AGENT</span></h1>
        <p class="hero-subtitle">Upload a PDF, run verification, and review evidence-backed verdicts with our AI-powered fact-checking system.</p>
    </div>
    """),
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([0.35, 0.65], gap="large")

with left_col:
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    st.markdown('<div class="app-kicker">📄 DOCUMENT</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload PDF",
        type="pdf",
        help="Upload a PDF document containing claims you want to verify.",
        label_visibility="collapsed",
        key=f"pdf_upload_{st.session_state.upload_key}",
    )

    if uploaded:
        is_new_file = (
            st.session_state.active_file_name != uploaded.name
            or st.session_state.active_file_size != uploaded.size
        )
        if is_new_file:
            st.session_state.active_file_name = uploaded.name
            st.session_state.active_file_size = uploaded.size
            st.session_state.stage = "UPLOAD"
            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0

        uploaded_name = escape(uploaded.name)
        uploaded_size = round(uploaded.size / 1024, 1)
        file_info_col, remove_col = st.columns([0.82, 0.18], gap="small")

        with file_info_col:
            st.markdown(
                html_block(f"""
                <div class="uploaded-file">
                    <span>📄</span>
                    <span class="uploaded-filename">{uploaded_name}</span>
                    <span class="uploaded-size">{uploaded_size} KB</span>
                </div>
                """),
                unsafe_allow_html=True,
            )

        with remove_col:
            remove_pdf = st.button("✕", key="remove_pdf", help="Remove PDF", use_container_width=True)

        if remove_pdf:
            reset_upload_state()
            st.rerun()

        run_check = st.button("▶ RUN FACT-CHECK", type="primary", use_container_width=True)
    else:
        if st.session_state.active_file_name is not None:
            st.session_state.stage = "UPLOAD"
            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0
            st.session_state.active_file_name = None
            st.session_state.active_file_size = 0
        run_check = False

    st.markdown(
        html_block(f"""
        <div style="margin-top: 1.5rem;">
            <div class="stat-card" style="text-align: left;">
                <div class="stat-number" style="font-size: 1.5rem;">{st.session_state.word_count:,}</div>
                <div class="stat-label">WORDS ANALYZED</div>
            </div>
            <div class="stat-card" style="text-align: left; margin-top: 0.5rem;">
                <div class="stat-number" style="font-size: 1.5rem;">{st.session_state.claim_count}</div>
                <div class="stat-label">CLAIMS FOUND</div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    stage_placeholder = st.empty()
    set_stage(st.session_state.stage, stage_placeholder)
    status_placeholder = st.empty()

    if uploaded and run_check:
        try:
            OPENROUTER_KEY = st.secrets["OPENROUTER_API_KEY"]
            TAVILY_KEY = st.secrets["TAVILY_API_KEY"]
        except Exception:
            st.session_state.results = []
            status_placeholder.error("⚠️ API keys missing. Add OpenRouter and Tavily keys in Streamlit secrets.")
        else:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_KEY,
                timeout=15.0,
                default_headers={
                    "HTTP-Referer": "https://github.com/Ravi-108/GEO-FACTCHECK",
                    "X-Title": "GEO Fact-Check Agent",
                }
            )

            st.session_state.results = []
            st.session_state.word_count = 0
            st.session_state.claim_count = 0

            set_stage("EXTRACTING", stage_placeholder)
            status_placeholder.markdown(
                '<div class="run-status">📄 Extracting text from PDF...</div>',
                unsafe_allow_html=True,
            )
            text = extract_text(uploaded)

            if not text.strip():
                set_stage("UPLOAD", stage_placeholder)
                status_placeholder.error("❌ Could not read text from this PDF. It may be scanned or image-based.")
            else:
                st.session_state.word_count = len(text.split())

                set_stage("FINDING CLAIMS", stage_placeholder)
                status_placeholder.markdown(
                    '<div class="run-status">🔍 Finding verifiable claims...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    claims = extract_claims(text, OPENROUTER_KEY)
                except Exception as exc:
                    error_msg = str(exc)
                    import re
                    match = re.search(r"'message':\s*'([^']+)'", error_msg)
                    if match:
                        clean_msg = match.group(1)
                        status_placeholder.error(f"🚨 API Error: {clean_msg}")
                    else:
                        status_placeholder.error(f"🚨 Claim extraction failed: {error_msg}")
                    set_stage("UPLOAD", stage_placeholder)
                else:
                    st.session_state.claim_count = len(claims)

                    if not claims:
                        set_stage("UPLOAD", stage_placeholder)
                        status_placeholder.warning("⚠️ No verifiable claims found in this PDF.")
                    else:
                        max_claims_to_check = min(len(claims), 10)
                        results = []

                        set_stage("CHECKING EVIDENCE", stage_placeholder)
                        progress_bar = st.progress(0)
                        progress_text = st.empty()

                        for index, claim in enumerate(claims[:max_claims_to_check]):
                            claim_text = claim.get("claim", str(claim))
                            progress_text.markdown(
                                f'<div class="run-status">🔎 Checking claim {index + 1} of {max_claims_to_check}</div>',
                                unsafe_allow_html=True,
                            )

                            evidence = search_claim(claim_text, TAVILY_KEY)
                            verdict = get_verdict(claim_text, evidence, client)

                            results.append(
                                {
                                    "claim": claim_text,
                                    "type": claim.get("type", "unknown"),
                                    **verdict,
                                }
                            )

                            progress_bar.progress((index + 1) / max_claims_to_check)
                            time.sleep(0.2)

                        progress_text.empty()
                        progress_bar.empty()
                        st.session_state.results = results
                        set_stage("REPORT READY", stage_placeholder)
                        status_placeholder.markdown(
                            '<div class="run-status">✅ Report ready! Download your results below.</div>',
                            unsafe_allow_html=True,
                        )

    results = st.session_state.results

    if results:
        st.markdown('<div class="result-panel">', unsafe_allow_html=True)
        st.markdown('<div class="app-kicker">📊 ANALYSIS RESULTS</div>', unsafe_allow_html=True)
        st.markdown(render_stats(results), unsafe_allow_html=True)

        filter_col, download_col = st.columns([0.58, 0.42], gap="small")
        with filter_col:
            verdict_filter = st.selectbox(
                "Filter by verdict",
                ["All", "VERIFIED", "INACCURATE", "FALSE", "ERROR"],
                label_visibility="collapsed",
            )

        df = pd.DataFrame(results)
        display_cols = ["claim", "type", "verdict", "confidence", "explanation", "correct_fact"]
        available_cols = [column for column in display_cols if column in df.columns]
        df_export = df[available_cols]

        with download_col:
            st.download_button(
                "📥 DOWNLOAD CSV",
                df_export.to_csv(index=False),
                file_name="factcheck_report.csv",
                mime="text/csv",
                use_container_width=True,
            )

        filtered_results = (
            results
            if verdict_filter == "All"
            else [result for result in results if result.get("verdict") == verdict_filter]
        )

        for index, result in enumerate(filtered_results):
            verdict = result.get("verdict", "ERROR").upper()
            confidence = escape(str(result.get("confidence", "LOW")))
            card_class, badge_class = verdict_classes(verdict)
            claim_type = escape(str(result.get("type", "unknown")))
            claim_text = escape(str(result.get("claim", "N/A")))
            explanation = escape(str(result.get("explanation", "No explanation available.")))
            correction_html = render_correction(result.get("correct_fact"))
            sources_html = render_sources(result.get("sources"))

            st.markdown(
                html_block(f"""
                <div class="verdict-card {card_class}">
                    <div class="verdict-header">
                        <span class="verdict-badge {badge_class}">{verdict_icon(verdict)} {escape(verdict)}</span>
                        <span class="confidence-badge">🎯 {confidence}</span>
                        <span class="claim-meta">#{index + 1} - {claim_type}</span>
                    </div>
                    <div class="claim-text">"{claim_text}"</div>
                    <div class="explanation-text">{explanation}</div>
                    {correction_html}
                    {sources_html}
                </div>
                """),
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)
    elif uploaded:
        st.markdown(
            html_block("""
            <div class="empty-panel" style="text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
                <div class="empty-title">Ready to Verify</div>
                <p class="empty-copy">Click the "Run Fact-Check" button to start the verification process.</p>
            </div>
            """),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            html_block("""
            <div class="empty-panel" style="text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
                <div class="empty-title">Upload a PDF to Begin</div>
                <p class="empty-copy">Results, progress, and the final CSV report will appear here.</p>
            </div>
            """),
            unsafe_allow_html=True,
        )

# Version indicator
st.markdown(
    f'<div class="version-tag">v{APP_VERSION} | AI-Powered Fact Verification</div>',
    unsafe_allow_html=True
)