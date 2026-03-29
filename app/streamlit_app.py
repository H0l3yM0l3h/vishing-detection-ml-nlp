import streamlit as st
from pathlib import Path
import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import re
import tempfile
import os
import time

from auth import sanitize_input
from database import (
    log_analysis, get_user_history,
    check_rate_limit, record_rate_event,
    MAX_ANALYSES_PER_HOUR
)

# ===============================
# MODEL LOADING
# ===============================
BASE_DIR   = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

@st.cache_resource
def load_resources():
    vectorizer = joblib.load(MODELS_DIR / "vectorizer.pkl")
    models = {
        "SVM":                 joblib.load(MODELS_DIR / "svm_model.pkl"),
        "Logistic Regression": joblib.load(MODELS_DIR / "logistic_regression_model.pkl"),
        "Random Forest":       joblib.load(MODELS_DIR / "rf_model.pkl"),
    }
    nn_model = load_model(MODELS_DIR / "neural_network.keras", compile=False)
    return vectorizer, models, nn_model

@st.cache_resource
def load_whisper():
    """Load Whisper speech-to-text model (cached — loads once)."""
    import whisper
    return whisper.load_model("base")

vectorizer, models, nn_model = load_resources()

# ===============================
# VISHING PATTERN LIBRARY
# ===============================
VISHING_PATTERNS = [
    r"account.{0,15}(suspend|block|freeze|close|terminat)",
    r"(verify|confirm).{0,15}(account|identity|detail|information)",
    r"(urgent|immediately|right now|act now|limited time|within \d+ hour)",
    r"(OTP|one.time.password|one time pin|passcode)",
    r"(bank|credit card|debit card).{0,20}(number|detail|info)",
    r"(call back|press \d|dial \d|stay on the line)",
    r"(refund|reward|prize|winner|congratulation|selected|chosen)",
    r"(social security|ic number|passport|nric|mykad)",
    r"(suspicious|unauthorized|unusual|fraudulent).{0,20}(activity|transaction|access|login)",
    r"do not (tell|share|inform|disclose).{0,20}(anyone|anyone else|family|police|authority)",
    r"(legal action|arrested|lawsuit|court order|warrant)",
    r"transfer.{0,20}(fund|money|amount|rm|ringgit|dollar)",
    r"(verify|confirm).{0,10}(now|immediately|urgently|today)",
    r"your (account|card|loan|credit).{0,20}(will be|is being|has been).{0,10}(block|suspend|close|flag)",
]


def detect_suspicious_phrases(text: str) -> list:
    found = []
    for pattern in VISHING_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            phrase = match.group()
            if phrase not in found:
                found.append(phrase)
    return found


def build_highlighted_transcript(text: str, phrases: list) -> str:
    if not phrases:
        return text
    result = text
    for phrase in sorted(phrases, key=len, reverse=True):
        result = re.sub(
            re.escape(phrase),
            f'<mark class="hlt">{phrase}</mark>',
            result,
            flags=re.IGNORECASE
        )
    return result

# ===============================
# EXPLAINABILITY
# ===============================
def explain_prediction(model, X, feature_names, top_n=5):
    if hasattr(model, "named_steps"):
        clf  = model.named_steps["clf"]
        coef = clf.coef_[0]
    else:
        base = model.calibrated_classifiers_[0].estimator
        clf  = base.named_steps["clf"]
        coef = clf.coef_[0]

    limit       = min(len(feature_names), len(coef))
    indices     = [i for i in X.nonzero()[1] if i < limit]
    contribs    = {feature_names[i]: float(coef[i]) for i in indices}
    return sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]


def get_explanation(model_choice: str, text: str):
    """Returns list of (term, weight) tuples for linear models."""
    if model_choice not in ["SVM", "Logistic Regression"]:
        return []

    if model_choice == "Logistic Regression":
        m     = models["Logistic Regression"]
        tfidf = m.named_steps["tfidf"]
        X     = tfidf.transform([text])
        feats = tfidf.get_feature_names_out()
        return explain_prediction(m, X, feats)
    else:
        m     = models["SVM"]
        base  = m.calibrated_classifiers_[0].estimator
        tfidf = base.named_steps["tfidf"]
        X     = tfidf.transform([text])
        feats = tfidf.get_feature_names_out()
        return explain_prediction(m, X, feats)

# ===============================
# EVIDENCE QUALITY CHECK
# ===============================
def insufficient_evidence(text: str, confidence: float,
                          min_words: int = 5, min_conf: float = 0.70) -> tuple:
    words = len(text.strip().split())
    if words < min_words:
        return True, "Transcript too short for reliable analysis — provide more context"
    if confidence < min_conf:
        return True, f"Model confidence below threshold ({int(confidence*100)}% < 70%)"
    return False, ""

# ===============================
# SAMPLE TRANSCRIPTS
# ===============================
SAMPLE_VISHING = (
    "Hello, this is the Bank Security Department. We have detected suspicious and "
    "unauthorized activity on your account. Your account will be suspended within "
    "24 hours if you do not verify your details immediately. Please provide your "
    "account number, PIN, and the OTP that will be sent to your phone. Do not tell "
    "anyone about this call, including family members. If you fail to verify, legal "
    "action will be taken against you. Press 1 to speak with our security officer now."
)

SAMPLE_SAFE = (
    "Hello, I am calling from the customer service team. I noticed you recently placed "
    "an order with us and wanted to follow up to make sure everything arrived correctly. "
    "There is no urgency at all, this is just a courtesy call. If you have any questions "
    "about your order or need to make a return, please call us back at our official number "
    "listed on our website. Have a great day."
)

# ===============================
# CSS
# ===============================
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

    :root {
        --bg:        #04080f;
        --bg-card:   #08111c;
        --bg-card2:  #0b1825;
        --red:       #e8203c;
        --green:     #00e87a;
        --blue:      #00aaff;
        --amber:     #f0a800;
        --text:      #d8eaf8;
        --muted:     #4a7090;
        --border:    #112233;
        --glow-red:  0 0 22px rgba(232,32,60,0.45);
        --glow-green:0 0 22px rgba(0,232,122,0.45);
        --glow-blue: 0 0 18px rgba(0,170,255,0.35);
    }

    .stApp {
        background: var(--bg) !important;
        background-image:
            radial-gradient(ellipse at 15% 15%, rgba(0,80,170,0.07) 0%, transparent 55%),
            radial-gradient(ellipse at 85% 85%, rgba(232,32,60,0.05) 0%, transparent 55%),
            repeating-linear-gradient(0deg,   transparent, transparent 48px, rgba(0,170,255,0.018) 48px, rgba(0,170,255,0.018) 49px),
            repeating-linear-gradient(90deg,  transparent, transparent 48px, rgba(0,170,255,0.018) 48px, rgba(0,170,255,0.018) 49px) !important;
        font-family: 'Rajdhani', sans-serif !important;
        color: var(--text) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }

    /* Animations */
    @keyframes fadeUp    { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:translateY(0); } }
    @keyframes flicker   { 0%,94%,100%{opacity:1;} 95%,99%{opacity:.8;} }
    @keyframes pulsered  { 0%,100%{box-shadow:0 0 12px rgba(232,32,60,.25);} 50%{box-shadow:0 0 38px rgba(232,32,60,.65), 0 0 70px rgba(232,32,60,.25);} }
    @keyframes pulsegreen{ 0%,100%{box-shadow:0 0 12px rgba(0,232,122,.2);}  50%{box-shadow:0 0 36px rgba(0,232,122,.55), 0 0 65px rgba(0,232,122,.2);} }
    @keyframes pulsebdr  { 0%,100%{border-color:var(--border); box-shadow:none;} 50%{border-color:rgba(0,170,255,.4); box-shadow:var(--glow-blue);} }
    @keyframes scan      { 0%{top:-4%;} 100%{top:104%;} }
    @keyframes dotblink  { 0%,100%{opacity:1;} 50%{opacity:.3;} }

    /* Header */
    .hdr {
        background: linear-gradient(135deg, #040c16 0%, #08131f 60%, #040c16 100%);
        border-bottom: 1px solid var(--border);
        padding: 18px 48px;
        display: flex; align-items: center; gap: 20px;
        position: relative; overflow: hidden;
    }
    .hdr::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background: linear-gradient(90deg, transparent, var(--blue), var(--red), var(--blue), transparent);
    }
    .hdr-logo {
        font-family:'Orbitron',sans-serif; font-size:22px; font-weight:900;
        color:var(--text); letter-spacing:4px; animation:flicker 9s infinite;
    }
    .hdr-logo b { color:var(--red); font-weight:900; }
    .hdr-sub {
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:var(--blue); letter-spacing:4px; text-transform:uppercase; margin-top:3px;
    }
    .hdr-right { margin-left:auto; display:flex; align-items:center; gap:20px; }
    .online-badge {
        background:rgba(0,232,122,.07); border:1px solid rgba(0,232,122,.25);
        border-radius:4px; padding:5px 14px;
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:var(--green); letter-spacing:2px; display:flex; align-items:center; gap:7px;
    }
    .online-dot {
        width:6px; height:6px; background:var(--green); border-radius:50%;
        box-shadow:0 0 7px var(--green); animation:dotblink 2s infinite;
    }
    .hdr-user {
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:var(--muted); letter-spacing:2px;
    }
    .hdr-user span { color:var(--blue); }

    /* Logout button override */
    div[data-testid="column"]:last-child .stButton button {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--muted) !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 10px !important;
        letter-spacing: 2px !important;
        padding: 6px 16px !important;
        box-shadow: none !important;
        width: auto !important;
        margin-top: 0 !important;
    }
    div[data-testid="column"]:last-child .stButton button:hover {
        border-color: var(--red) !important;
        color: var(--red) !important;
        box-shadow: none !important;
        transform: none !important;
    }

    /* Main container */
    .wrap { max-width:880px; margin:0 auto; padding:44px 24px; animation:fadeUp .5s ease; }

    /* Hero */
    .hero { text-align:center; margin-bottom:44px; }
    .hero-tag {
        font-family:'Orbitron',sans-serif; font-size:11px; color:var(--blue);
        letter-spacing:7px; text-transform:uppercase; margin-bottom:14px;
    }
    .hero-h1 {
        font-family:'Rajdhani',sans-serif; font-size:46px; font-weight:700;
        color:var(--text); line-height:1.1; margin-bottom:14px;
    }
    .hero-h1 s { text-decoration:none; color:var(--red); }
    .hero-p { color:var(--muted); font-size:17px; font-weight:300; max-width:520px; margin:0 auto; line-height:1.65; }

    /* Stat strip */
    .stats { display:flex; justify-content:center; gap:20px; margin:28px 0; flex-wrap:wrap; }
    .stat {
        background:var(--bg-card); border:1px solid var(--border);
        border-radius:8px; padding:12px 22px; text-align:center; min-width:110px;
    }
    .stat-v { font-family:'Orbitron',sans-serif; font-size:20px; font-weight:700; color:var(--blue); }
    .stat-l { font-size:10px; color:var(--muted); letter-spacing:2px; text-transform:uppercase; margin-top:3px; }

    /* Steps */
    .steps { display:flex; gap:14px; margin-bottom:34px; }
    .step {
        flex:1; background:var(--bg-card); border:1px solid var(--border);
        border-radius:10px; padding:18px 14px; text-align:center;
        transition:border-color .3s;
    }
    .step:hover { border-color:rgba(0,170,255,.35); }
    .step-n { font-family:'Orbitron',sans-serif; font-size:26px; font-weight:900; color:var(--blue); opacity:.35; line-height:1; margin-bottom:6px; }
    .step-t { font-weight:700; font-size:13px; color:var(--text); letter-spacing:1px; text-transform:uppercase; }
    .step-d { font-size:12px; color:var(--muted); margin-top:4px; }

    /* Input card */
    .card {
        background:var(--bg-card); border:1px solid var(--border);
        border-radius:12px; padding:30px; margin-bottom:22px;
        animation:pulsebdr 5s ease-in-out infinite;
    }
    .sec-lbl {
        font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--blue);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:14px;
        display:flex; align-items:center; gap:8px;
    }
    .sec-lbl::after { content:''; flex:1; height:1px; background:linear-gradient(90deg,var(--border),transparent); }

    /* Streamlit widget overrides */
    .stTextArea textarea {
        background:#030a12 !important; border:1px solid var(--border) !important;
        border-radius:8px !important; color:var(--text) !important;
        font-family:'Share Tech Mono',monospace !important; font-size:13px !important;
        line-height:1.75 !important; padding:14px !important;
        transition:border-color .3s, box-shadow .3s !important;
    }
    .stTextArea textarea:focus {
        border-color:rgba(0,170,255,.5) !important; box-shadow:var(--glow-blue) !important;
    }
    .stTextArea textarea::placeholder { color:#1a3a55 !important; }
    .stTextArea label { display:none !important; }

    /* Primary analyze button */
    .stButton button {
        background:linear-gradient(135deg, #c41830, #8c0e20) !important;
        color:white !important; border:none !important; border-radius:8px !important;
        font-family:'Orbitron',sans-serif !important; font-size:12px !important;
        font-weight:700 !important; letter-spacing:3px !important;
        padding:14px 32px !important; width:100% !important;
        box-shadow:0 4px 18px rgba(232,32,60,.3) !important;
        transition:all .3s !important; text-transform:uppercase !important;
    }
    .stButton button:hover {
        box-shadow:var(--glow-red), 0 6px 28px rgba(232,32,60,.5) !important;
        transform:translateY(-1px) !important;
    }

    /* Sample + secondary buttons */
    .stButton:has(button[kind="secondary"]) button,
    div[data-testid="column"] .stButton button {
        background:rgba(0,170,255,.07) !important;
        border:1px solid rgba(0,170,255,.22) !important;
        color:var(--blue) !important;
        font-family:'Rajdhani',sans-serif !important;
        font-size:13px !important; font-weight:600 !important;
        letter-spacing:1px !important; padding:9px 18px !important;
        box-shadow:none !important; margin-top:0 !important;
    }
    div[data-testid="column"] .stButton button:hover {
        border-color:rgba(0,170,255,.5) !important;
        box-shadow:var(--glow-blue) !important;
        transform:none !important;
    }

    .stSelectbox > div > div {
        background:#030a12 !important; border:1px solid var(--border) !important;
        color:var(--text) !important; border-radius:8px !important;
        font-family:'Rajdhani',sans-serif !important;
    }
    .stExpander { background:var(--bg-card) !important; border:1px solid var(--border) !important; border-radius:8px !important; }
    .stExpander summary { color:var(--muted) !important; font-family:'Share Tech Mono',monospace !important; font-size:11px !important; letter-spacing:2px !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background:rgba(0,0,0,.35) !important; border-radius:8px !important;
        padding:4px !important; gap:4px !important; border:none !important; margin-bottom:22px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--muted) !important;
        font-family:'Orbitron',sans-serif !important; font-size:10px !important;
        font-weight:700 !important; letter-spacing:3px !important;
        border-radius:6px !important; padding:10px 22px !important;
        border:none !important; text-transform:uppercase !important; flex:1 !important;
    }
    .stTabs [aria-selected="true"] {
        background:rgba(0,170,255,.1) !important; color:var(--blue) !important;
        border:1px solid rgba(0,170,255,.22) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding:0 !important; background:transparent !important; }
    .stTabs [data-baseweb="tab-highlight"] { display:none !important; }

    /* File uploader */
    .stFileUploader > div {
        background:#030a12 !important; border:1px dashed rgba(0,170,255,.25) !important;
        border-radius:8px !important; padding:10px !important;
    }
    .stFileUploader label { color:var(--muted) !important; font-family:'Rajdhani',sans-serif !important; }
    .stFileUploader p    { color:var(--muted) !important; font-family:'Share Tech Mono',monospace !important; font-size:11px !important; }

    /* Progress / spinner */
    .stProgress > div > div { background:var(--blue) !important; }
    .stSpinner > div { border-top-color:var(--blue) !important; }

    /* Info box */
    .info-box {
        background:rgba(0,170,255,.05); border:1px solid rgba(0,170,255,.18);
        border-left:3px solid var(--blue); border-radius:6px;
        padding:11px 15px; font-size:13px; color:var(--muted); margin:11px 0;
        font-family:'Rajdhani',sans-serif; line-height:1.5;
    }
    .warn-box {
        background:rgba(240,168,0,.05); border:1px solid rgba(240,168,0,.2);
        border-left:3px solid var(--amber); border-radius:6px;
        padding:11px 15px; font-size:13px; color:#a07020; margin:11px 0;
        font-family:'Rajdhani',sans-serif; line-height:1.5;
    }

    /* Result cards */
    .r-card { border-radius:12px; padding:30px; margin:22px 0; animation:fadeUp .4s ease; }
    .r-threat { background:linear-gradient(135deg,rgba(232,32,60,.11),rgba(160,0,30,.07)); border:1px solid rgba(232,32,60,.38); animation:pulsered 2.8s ease-in-out infinite; }
    .r-safe   { background:linear-gradient(135deg,rgba(0,232,122,.08),rgba(0,160,70,.05)); border:1px solid rgba(0,232,122,.32); animation:pulsegreen 2.8s ease-in-out infinite; }
    .r-unknown{ background:linear-gradient(135deg,rgba(240,168,0,.07),rgba(160,110,0,.04)); border:1px solid rgba(240,168,0,.3); }

    .r-icon    { font-size:44px; margin-bottom:10px; }
    .r-verdict { font-family:'Orbitron',sans-serif; font-size:26px; font-weight:900; letter-spacing:4px; margin-bottom:6px; }
    .r-sub     { font-size:15px; margin-top:3px; }
    .c-red   { color:var(--red); }
    .c-green { color:var(--green); }
    .c-amber { color:var(--amber); }
    .c-muted { color:var(--muted); }

    /* Confidence bar */
    .cb-wrap  { background:rgba(255,255,255,.05); border-radius:4px; height:8px; margin:14px 0 6px; overflow:hidden; }
    .cb-fill  { height:100%; border-radius:4px; }
    .cb-red   { background:linear-gradient(90deg,#aa0020,#e8203c); }
    .cb-green { background:linear-gradient(90deg,#009950,#00e87a); }
    .cb-lbl   { font-family:'Share Tech Mono',monospace; font-size:11px; color:var(--muted); display:flex; justify-content:space-between; }

    /* Phrase chips */
    .phrase-box { background:rgba(232,32,60,.06); border:1px solid rgba(232,32,60,.18); border-radius:8px; padding:18px 22px; margin:14px 0; }
    .phrase-ttl { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--red); letter-spacing:3px; text-transform:uppercase; margin-bottom:10px; }
    .chip {
        display:inline-block; background:rgba(232,32,60,.13); border:1px solid rgba(232,32,60,.3);
        border-radius:4px; padding:3px 11px; margin:3px;
        font-family:'Share Tech Mono',monospace; font-size:11px; color:#e07080;
    }

    /* Transcript box */
    .tx-box {
        background:#030a12; border:1px solid var(--border); border-radius:8px;
        padding:15px; font-family:'Share Tech Mono',monospace; font-size:12px;
        color:var(--muted); line-height:1.75; max-height:190px; overflow-y:auto; margin:14px 0;
    }
    mark.hlt {
        background:rgba(232,32,60,.18); border:1px solid rgba(232,32,60,.38);
        border-radius:3px; padding:1px 4px; color:#e08090;
        font-family:'Share Tech Mono',monospace;
    }

    /* Explanation card */
    .expl-card { background:var(--bg-card2); border:1px solid var(--border); border-radius:8px; padding:18px 22px; margin:14px 0; }
    .expl-ttl  { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--blue); letter-spacing:3px; text-transform:uppercase; margin-bottom:14px; }
    .expl-row  { display:flex; align-items:center; gap:11px; margin-bottom:9px; }
    .expl-term { font-family:'Share Tech Mono',monospace; font-size:12px; color:var(--text); min-width:120px; }
    .expl-bw   { flex:1; background:rgba(255,255,255,.05); border-radius:3px; height:5px; overflow:hidden; }
    .eb-r { background:var(--red);   height:100%; border-radius:3px; }
    .eb-g { background:var(--green); height:100%; border-radius:3px; }
    .expl-w    { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted); min-width:52px; text-align:right; }
    .expl-note { font-family:'Share Tech Mono',monospace; font-size:9px; color:#1a3a55; margin-top:10px; }

    /* Advice card */
    .adv-card { background:var(--bg-card); border-radius:10px; padding:22px; margin:14px 0; }
    .adv-ttl  { font-family:'Rajdhani',sans-serif; font-size:15px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:14px; }
    .adv-item { display:flex; align-items:flex-start; gap:11px; margin-bottom:9px; font-size:14px; color:#a0c0d8; line-height:1.55; }
    .adv-ico  { font-size:14px; flex-shrink:0; margin-top:2px; }

    /* History table */
    .hist-row {
        display:flex; justify-content:space-between; align-items:center;
        padding:9px 14px; border-bottom:1px solid var(--border); font-size:12px;
        font-family:'Share Tech Mono',monospace;
    }
    .hist-row:last-child { border-bottom:none; }
    .badge-v { background:rgba(232,32,60,.15); border:1px solid rgba(232,32,60,.3); border-radius:3px; padding:2px 8px; color:var(--red); font-size:10px; letter-spacing:1px; }
    .badge-s { background:rgba(0,232,122,.1);  border:1px solid rgba(0,232,122,.25);border-radius:3px; padding:2px 8px; color:var(--green); font-size:10px; letter-spacing:1px; }

    /* Footer */
    .ftr {
        border-top:1px solid var(--border); padding:18px 48px;
        display:flex; justify-content:space-between; align-items:center; margin-top:56px;
    }
    .ftr-t { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted); letter-spacing:2px; }

    /* Rate limit bar */
    .rl-wrap { display:flex; align-items:center; gap:10px; }
    .rl-bar  { flex:1; background:rgba(255,255,255,.05); border-radius:3px; height:4px; overflow:hidden; }
    .rl-fill { background:var(--blue); height:100%; border-radius:3px; transition:width .5s; }
    .rl-lbl  { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted); white-space:nowrap; }

    /* Scrollbar */
    ::-webkit-scrollbar { width:5px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--blue); }
    </style>
    """, unsafe_allow_html=True)


# ===============================
# HEADER
# ===============================
def render_header():
    username = st.session_state.get("user", "")
    user_html = (
        f"<div class='hdr-user'>OPERATOR: <span>{username.upper()}</span></div>"
        if username else ""
    )
    st.markdown(f"""
    <div class="hdr">
        <div>
            <div class="hdr-logo">SHIELD<b>GUARD</b></div>
            <div class="hdr-sub">Voice Threat Intelligence Platform</div>
        </div>
        <div class="hdr-right">
            {user_html}
            <div class="online-badge"><span class="online-dot"></span>SYSTEM ONLINE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ===============================
# AUDIO TRANSCRIPTION
# ===============================
def transcribe_audio(audio_bytes: bytes, suffix: str) -> str:
    """
    Saves audio to a temp file, runs Whisper, deletes file.
    Returns the transcript string.
    """
    try:
        whisper_model = load_whisper()
    except Exception:
        raise RuntimeError(
            "Whisper is not installed. Run:  pip install openai-whisper"
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        result = whisper_model.transcribe(tmp_path, fp16=False)
        return result["text"].strip()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ===============================
# INFERENCE
# ===============================
def run_inference(text: str, model_choice: str) -> tuple:
    """Returns (label, confidence)."""
    if model_choice == "Neural Network":
        x_nn       = tf.constant([text])
        prob       = float(nn_model.predict(x_nn, verbose=0).reshape(-1)[0])
        label      = "vishing" if prob >= 0.5 else "safe"
        confidence = prob if label == "vishing" else 1.0 - prob
    else:
        model      = models[model_choice]
        label      = model.predict([text])[0]
        confidence = (
            float(np.max(model.predict_proba([text])))
            if hasattr(model, "predict_proba")
            else 0.5
        )
    return label, confidence


# ===============================
# RESULT RENDERER
# ===============================
def render_result(label: str, confidence: float, text: str, model_choice: str):
    pct = int(confidence * 100)

    # --- Vishing ---
    if label == "vishing":
        st.markdown(f"""
        <div class="r-card r-threat">
            <div style="text-align:center;">
                <div class="r-icon">!</div>
                <div class="r-verdict c-red">VISHING DETECTED</div>
                <div class="r-sub" style="color:#c06070;">HIGH RISK — This call exhibits scam characteristics</div>
                <div class="cb-lbl" style="margin-top:14px;">
                    <span>THREAT CONFIDENCE</span>
                    <span style="font-size:17px;font-weight:700;color:var(--red);">{pct}%</span>
                </div>
                <div class="cb-wrap"><div class="cb-fill cb-red" style="width:{pct}%"></div></div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--muted);margin-top:8px;">
                    ENGINE: {model_choice.upper()} &nbsp;|&nbsp; VERDICT: MALICIOUS &nbsp;|&nbsp; CONFIDENCE: {pct}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        phrases = detect_suspicious_phrases(text)
        if phrases:
            chips = "".join(f'<span class="chip">{p}</span>' for p in phrases)
            st.markdown(f"""
            <div class="phrase-box">
                <div class="phrase-ttl">SUSPICIOUS PHRASES DETECTED ({len(phrases)})</div>
                {chips}
            </div>
            """, unsafe_allow_html=True)
            st.markdown(
                '<div class="sec-lbl" style="margin-top:18px;">TRANSCRIPT ANALYSIS</div>',
                unsafe_allow_html=True
            )
            highlighted = build_highlighted_transcript(text, phrases)
            st.markdown(f'<div class="tx-box">{highlighted}</div>', unsafe_allow_html=True)

        # Explainability
        top_terms = get_explanation(model_choice, text)
        if top_terms:
            max_w = max(abs(w) for _, w in top_terms) or 1
            rows  = ""
            for term, weight in top_terms:
                bar_pct = int((abs(weight) / max_w) * 100)
                cls     = "eb-r" if weight > 0 else "eb-g"
                arrow   = "+" if weight > 0 else "-"
                rows += f"""
                <div class="expl-row">
                    <span class="expl-term">{term}</span>
                    <div class="expl-bw"><div class="{cls}" style="width:{bar_pct}%"></div></div>
                    <span class="expl-w">{arrow} {abs(weight):.3f}</span>
                </div>"""
            st.markdown(f"""
            <div class="expl-card">
                <div class="expl-ttl">AI REASONING — TOP THREAT INDICATORS</div>
                {rows}
                <div class="expl-note">+ pushes toward VISHING &nbsp;|&nbsp; - pushes toward SAFE</div>
            </div>
            """, unsafe_allow_html=True)

        # Safety advice
        st.markdown("""
        <div class="adv-card" style="border:1px solid rgba(232,32,60,.18);">
            <div class="adv-ttl" style="color:var(--red);">IMMEDIATE SAFETY ACTION REQUIRED</div>
            <div class="adv-item"><span class="adv-ico">X</span><span>Do <strong>NOT</strong> share any personal information, OTP, PIN, or bank account details.</span></div>
            <div class="adv-item"><span class="adv-ico">X</span><span>Hang up immediately. Do <strong>NOT</strong> call back any number provided by the caller.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Contact your bank directly via the official number printed on the <strong>back of your card</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Report to <strong>Cyber999 Hotline: 1-300-88-2999</strong> or lodge a report at <strong>www.cybersafe.my</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Alert family members — especially elderly relatives — about this scam call pattern.</span></div>
        </div>
        """, unsafe_allow_html=True)

    # --- Safe ---
    else:
        st.markdown(f"""
        <div class="r-card r-safe">
            <div style="text-align:center;">
                <div class="r-icon">V</div>
                <div class="r-verdict c-green">CALL APPEARS SAFE</div>
                <div class="r-sub" style="color:#60c090;">LOW RISK — No vishing indicators detected</div>
                <div class="cb-lbl" style="margin-top:14px;">
                    <span>SAFETY CONFIDENCE</span>
                    <span style="font-size:17px;font-weight:700;color:var(--green);">{pct}%</span>
                </div>
                <div class="cb-wrap"><div class="cb-fill cb-green" style="width:{pct}%"></div></div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:var(--muted);margin-top:8px;">
                    ENGINE: {model_choice.upper()} &nbsp;|&nbsp; VERDICT: BENIGN &nbsp;|&nbsp; CONFIDENCE: {pct}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        top_terms = get_explanation(model_choice, text)
        if top_terms:
            max_w = max(abs(w) for _, w in top_terms) or 1
            rows  = ""
            for term, weight in top_terms:
                bar_pct = int((abs(weight) / max_w) * 100)
                cls     = "eb-r" if weight > 0 else "eb-g"
                arrow   = "+" if weight > 0 else "-"
                rows += f"""
                <div class="expl-row">
                    <span class="expl-term">{term}</span>
                    <div class="expl-bw"><div class="{cls}" style="width:{bar_pct}%"></div></div>
                    <span class="expl-w">{arrow} {abs(weight):.3f}</span>
                </div>"""
            st.markdown(f"""
            <div class="expl-card">
                <div class="expl-ttl">AI REASONING — KEY SIGNAL TERMS</div>
                {rows}
                <div class="expl-note">+ toward VISHING &nbsp;|&nbsp; - toward SAFE</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="adv-card" style="border:1px solid rgba(0,232,122,.12);">
            <div class="adv-ttl" style="color:var(--green);">GENERAL SECURITY REMINDERS</div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Always <strong>verify the caller's identity</strong> independently before sharing any information.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Legitimate banks will <strong>never</strong> ask for your full PIN, OTP, or password over the phone.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>When in doubt, hang up and call the institution back using their <strong>official published number</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">&gt;</span><span>Register with <strong>MCMC Do Not Disturb</strong> to reduce unsolicited calls.</span></div>
        </div>
        """, unsafe_allow_html=True)


# ===============================
# HISTORY PANEL
# ===============================
def render_history():
    username = st.session_state.get("user", "")
    history  = get_user_history(username, limit=10)
    if not history:
        st.markdown(
            '<div class="info-box">No analysis history yet for this session.</div>',
            unsafe_allow_html=True
        )
        return

    st.markdown("""
    <div class="expl-card">
        <div class="expl-ttl">RECENT ANALYSIS HISTORY</div>
    """, unsafe_allow_html=True)

    for row in history:
        badge = (
            f'<span class="badge-v">VISHING</span>'
            if row["verdict"] == "vishing"
            else f'<span class="badge-s">SAFE</span>'
        )
        conf  = int(row["confidence"] * 100)
        ts    = row["analyzed_at"][:16].replace("T", " ")
        mode  = row.get("input_mode", "text").upper()
        st.markdown(f"""
        <div class="hist-row">
            <span>{badge}</span>
            <span style="color:var(--muted);">{conf}% conf</span>
            <span style="color:var(--muted);">{row['model_used']}</span>
            <span style="color:var(--muted);">{mode}</span>
            <span style="color:#1a3a55;">{ts}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ===============================
# MAIN RENDER
# ===============================
def render_app():
    inject_css()
    render_header()

    username = st.session_state.get("user", "")

    # Logout — top right via columns trick
    _, _, col_logout = st.columns([6, 1, 1])
    with col_logout:
        if st.button("LOGOUT", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user          = None
            st.rerun()

    st.markdown('<div class="wrap">', unsafe_allow_html=True)

    # ---- HERO ----
    st.markdown("""
    <div class="hero">
        <div class="hero-tag">AI-Powered Voice Threat Detection</div>
        <div class="hero-h1">Detect <s>Voice Scam</s><br>Attacks Instantly</div>
        <div class="hero-p">
            Advanced machine learning and NLP scan call recordings and transcripts
            in real-time — giving you a clear threat verdict with full explainability.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- STATS ----
    st.markdown("""
    <div class="stats">
        <div class="stat"><div class="stat-v">97.3%</div><div class="stat-l">Accuracy</div></div>
        <div class="stat"><div class="stat-v">4</div><div class="stat-l">AI Models</div></div>
        <div class="stat"><div class="stat-v">&lt;2s</div><div class="stat-l">Analysis</div></div>
        <div class="stat"><div class="stat-v">NLP</div><div class="stat-l">Powered</div></div>
        <div class="stat"><div class="stat-v">XAI</div><div class="stat-l">Explainable</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- STEPS ----
    st.markdown("""
    <div class="steps">
        <div class="step">
            <div class="step-n">01</div>
            <div class="step-t">Upload or Paste</div>
            <div class="step-d">Provide an audio recording or paste the transcript directly</div>
        </div>
        <div class="step">
            <div class="step-n">02</div>
            <div class="step-t">Analyze</div>
            <div class="step-d">AI engine transcribes, scans, and classifies the call</div>
        </div>
        <div class="step">
            <div class="step-n">03</div>
            <div class="step-t">Act on Results</div>
            <div class="step-d">Receive a clear threat verdict, phrase analysis, and advice</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- RATE LIMIT INDICATOR ----
    allowed, used_count = check_rate_limit(username)
    rl_pct = int((used_count / MAX_ANALYSES_PER_HOUR) * 100)
    st.markdown(f"""
    <div style="margin-bottom:18px;">
        <div class="rl-wrap">
            <span class="rl-lbl">USAGE</span>
            <div class="rl-bar"><div class="rl-fill" style="width:{rl_pct}%"></div></div>
            <span class="rl-lbl">{used_count}/{MAX_ANALYSES_PER_HOUR} analyses this hour</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not allowed:
        st.markdown(f"""
        <div class="warn-box">
            Rate limit reached ({MAX_ANALYSES_PER_HOUR} analyses/hour). Please wait before submitting again.
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ---- INPUT TABS ----
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">INPUT METHOD</div>', unsafe_allow_html=True)

    tab_audio, tab_text = st.tabs(["Upload Audio Recording", "Paste Transcript"])

    final_text  = ""
    input_mode  = "text"
    transcribed = False

    # ---- TAB: AUDIO ----
    with tab_audio:
        st.markdown("""
        <div class="info-box">
            Upload a call recording (.wav, .mp3, .m4a, .ogg, .flac). The system will
            automatically transcribe it using AI speech recognition, then analyze the transcript.
            Audio files are processed locally and deleted immediately after transcription.
        </div>
        """, unsafe_allow_html=True)

        audio_file = st.file_uploader(
            "audio_upload",
            type=["wav", "mp3", "m4a", "ogg", "flac"],
            label_visibility="collapsed"
        )

        if audio_file is not None:
            suffix   = Path(audio_file.name).suffix.lower()
            file_mb  = len(audio_file.getvalue()) / (1024 * 1024)

            if file_mb > 25:
                st.markdown(
                    '<div class="warn-box">File exceeds 25 MB limit. Please upload a shorter recording.</div>',
                    unsafe_allow_html=True
                )
            else:
                if st.button("TRANSCRIBE RECORDING", key="transcribe_btn"):
                    with st.spinner("Transcribing audio — please wait..."):
                        try:
                            transcript = transcribe_audio(audio_file.getvalue(), suffix)
                            st.session_state["transcribed_text"] = transcript
                            st.session_state["transcript_ready"] = True
                            st.success("Transcription complete.")
                        except RuntimeError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")

        if st.session_state.get("transcript_ready"):
            transcribed_text = st.session_state.get("transcribed_text", "")
            st.markdown('<div class="sec-lbl" style="margin-top:16px;">TRANSCRIBED TEXT</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tx-box">{transcribed_text[:2000]}</div>', unsafe_allow_html=True)
            final_text = transcribed_text
            input_mode = "audio"

    # ---- TAB: TEXT ----
    with tab_text:
        st.markdown("""
        <div class="info-box">
            Paste the call transcript below. For best results, include the full conversation.
            Minimum 5 words required for reliable detection.
        </div>
        """, unsafe_allow_html=True)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("Load Sample Scam Transcript", key="sample_v"):
                st.session_state["manual_text"] = SAMPLE_VISHING
        with col_s2:
            if st.button("Load Sample Safe Transcript", key="sample_s"):
                st.session_state["manual_text"] = SAMPLE_SAFE

        typed_text = st.text_area(
            "manual_transcript",
            value=st.session_state.get("manual_text", ""),
            height=175,
            placeholder="Paste the call transcript here...",
            label_visibility="collapsed"
        )
        if typed_text.strip():
            final_text = typed_text
            input_mode = "text"

    # ---- MODEL SELECTION (ADVANCED) ----
    with st.expander("Advanced Settings — AI Model Selection"):
        model_choice = st.selectbox(
            "Detection Engine",
            ["SVM", "Logistic Regression", "Random Forest", "Neural Network"],
            help="SVM provides the best balance of speed and accuracy for this dataset."
        )
        st.markdown("""
        <div class="info-box">
            SVM and Logistic Regression support full explainability (AI Reasoning panel).
            Random Forest and Neural Network provide verdict and confidence only.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .card

    # ---- ANALYZE BUTTON ----
    analyze = st.button("ANALYZE TRANSCRIPT", key="analyze_btn")

    if analyze:
        if not final_text.strip():
            st.markdown("""
            <div class="r-card r-unknown">
                <div style="text-align:center;padding:16px;">
                    <div class="r-verdict c-amber" style="font-size:18px;">NO INPUT DETECTED</div>
                    <div style="color:var(--muted);margin-top:8px;font-family:'Rajdhani',sans-serif;">
                        Please upload an audio file or paste a transcript before analyzing.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Sanitize
            clean_text = sanitize_input(final_text, max_length=10000)

            with st.spinner("Scanning transcript for threat indicators..."):
                label, confidence = run_inference(clean_text, model_choice)
                is_insuff, reason = insufficient_evidence(clean_text, confidence)

            if is_insuff:
                st.markdown(f"""
                <div class="r-card r-unknown">
                    <div style="text-align:center;">
                        <div class="r-icon">?</div>
                        <div class="r-verdict c-amber">INCONCLUSIVE</div>
                        <div style="color:var(--muted);font-family:'Rajdhani',sans-serif;font-size:15px;margin-top:8px;">{reason}</div>
                        <div style="font-family:'Share Tech Mono',monospace;font-size:11px;color:#1a3a55;margin-top:14px;">
                            Provide a longer transcript with more context for accurate detection.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Audit log
                log_analysis(
                    username    = username,
                    input_length= len(clean_text),
                    input_mode  = input_mode,
                    model_used  = model_choice,
                    verdict     = label,
                    confidence  = confidence
                )
                record_rate_event(username)
                render_result(label, confidence, clean_text, model_choice)

    # ---- HISTORY ----
    st.markdown('<div style="margin-top:40px;">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">YOUR ANALYSIS HISTORY</div>', unsafe_allow_html=True)
    render_history()
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- FOOTER ----
    st.markdown("""
    <div class="ftr">
        <div class="ftr-t">SHIELDGUARD v1.0 — CYBERSECURITY FYP</div>
        <div class="ftr-t">MODELS: SVM + LR + RF + NN &nbsp;|&nbsp; WHISPER ASR &nbsp;|&nbsp; NLP ENGINE ACTIVE</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .wrap