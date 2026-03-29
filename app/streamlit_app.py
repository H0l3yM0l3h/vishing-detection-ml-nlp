import streamlit as st
from pathlib import Path
import joblib
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import re
import tempfile
import os
import io

from auth import sanitize_input
from database import (
    log_analysis, get_user_history,
    check_rate_limit, record_rate_event,
    MAX_ANALYSES_PER_HOUR,
)

# ═══════════════════════════════════════════════
# MODEL LOADING
# ═══════════════════════════════════════════════
BASE_DIR   = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

@st.cache_resource
def load_resources():
    vectorizer = joblib.load(MODELS_DIR / "vectorizer.pkl")
    ml_models  = {
        "SVM":                 joblib.load(MODELS_DIR / "svm_model.pkl"),
        "Logistic Regression": joblib.load(MODELS_DIR / "logistic_regression_model.pkl"),
        "Random Forest":       joblib.load(MODELS_DIR / "rf_model.pkl"),
    }
    nn = load_model(MODELS_DIR / "neural_network.keras", compile=False)
    return vectorizer, ml_models, nn

@st.cache_resource
def load_whisper_model():
    import whisper
    return whisper.load_model("base")

vectorizer, models, nn_model = load_resources()

# ═══════════════════════════════════════════════
# VISHING PATTERNS
# ═══════════════════════════════════════════════
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
    for pat in VISHING_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group() not in found:
                found.append(m.group())
    return found

def build_highlighted_transcript(text: str, phrases: list) -> str:
    result = text
    for p in sorted(phrases, key=len, reverse=True):
        result = re.sub(re.escape(p),
                        f'<mark class="hlt">{p}</mark>',
                        result, flags=re.IGNORECASE)
    return result

# ═══════════════════════════════════════════════
# EXPLAINABILITY
# ═══════════════════════════════════════════════
def explain_prediction(model, X, feature_names, top_n=5):
    if hasattr(model, "named_steps"):
        coef = model.named_steps["clf"].coef_[0]
    else:
        coef = model.calibrated_classifiers_[0].estimator.named_steps["clf"].coef_[0]
    limit    = min(len(feature_names), len(coef))
    indices  = [i for i in X.nonzero()[1] if i < limit]
    contribs = {feature_names[i]: float(coef[i]) for i in indices}
    return sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]

def get_explanation(model_choice: str, text: str):
    if model_choice not in ["SVM", "Logistic Regression"]:
        return []
    if model_choice == "Logistic Regression":
        m     = models["Logistic Regression"]
        tfidf = m.named_steps["tfidf"]
    else:
        m     = models["SVM"]
        tfidf = m.calibrated_classifiers_[0].estimator.named_steps["tfidf"]
    X     = tfidf.transform([text])
    feats = tfidf.get_feature_names_out()
    return explain_prediction(m, X, feats)

# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def insufficient_evidence(text: str, confidence: float,
                           min_words: int = 5, min_conf: float = 0.70):
    if len(text.strip().split()) < min_words:
        return True, "Transcript too short — provide more context for reliable analysis"
    if confidence < min_conf:
        return True, f"Confidence below threshold ({int(confidence*100)}% < 70%)"
    return False, ""

def run_inference(text: str, model_choice: str):
    if model_choice == "Neural Network":
        prob  = float(nn_model.predict(tf.constant([text]), verbose=0).reshape(-1)[0])
        label = "vishing" if prob >= 0.5 else "safe"
        conf  = prob if label == "vishing" else 1.0 - prob
    else:
        m     = models[model_choice]
        label = m.predict([text])[0]
        conf  = float(np.max(m.predict_proba([text]))) if hasattr(m, "predict_proba") else 0.5
    return label, conf

def transcribe_audio(audio_bytes: bytes, suffix: str) -> str:
    try:
        wmodel = load_whisper_model()
    except Exception:
        raise RuntimeError("Whisper not installed. Run: pip install openai-whisper")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(audio_bytes)
            tmp = f.name
        result = wmodel.transcribe(tmp, fp16=False)
        return result["text"].strip()
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

# ═══════════════════════════════════════════════
# SAMPLE TRANSCRIPTS
# ═══════════════════════════════════════════════
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

# ═══════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

    :root {
        --bg:       #04080f;
        --c1:       #08111c;
        --c2:       #0b1825;
        --red:      #e8203c;
        --green:    #00e87a;
        --blue:     #00aaff;
        --amber:    #f0a800;
        --text:     #d8eaf8;
        --muted:    #4a7090;
        --border:   #112233;
        --gr:       0 0 22px rgba(232,32,60,.45);
        --gg:       0 0 22px rgba(0,232,122,.45);
        --gb:       0 0 18px rgba(0,170,255,.35);
    }

    html, body, .stApp {
        background: var(--bg) !important;
        font-family: 'Rajdhani', sans-serif !important;
        color: var(--text) !important;
    }
    .stApp {
        background-image:
            radial-gradient(ellipse at 15% 15%, rgba(0,80,170,.07) 0%, transparent 55%),
            radial-gradient(ellipse at 85% 85%, rgba(232,32,60,.05) 0%, transparent 55%),
            repeating-linear-gradient(0deg,  transparent,transparent 48px,rgba(0,170,255,.016) 48px,rgba(0,170,255,.016) 49px),
            repeating-linear-gradient(90deg, transparent,transparent 48px,rgba(0,170,255,.016) 48px,rgba(0,170,255,.016) 49px) !important;
    }
    #MainMenu, footer, header { visibility:hidden; }
    .block-container { padding:0 !important; max-width:100% !important; }

    /* ── keyframes ── */
    @keyframes fadeUp    { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
    @keyframes flicker   { 0%,93%,100%{opacity:1} 94%,99%{opacity:.78} }
    @keyframes pulsered  { 0%,100%{box-shadow:0 0 10px rgba(232,32,60,.2)} 50%{box-shadow:0 0 36px rgba(232,32,60,.6),0 0 65px rgba(232,32,60,.2)} }
    @keyframes pulsegreen{ 0%,100%{box-shadow:0 0 10px rgba(0,232,122,.18)} 50%{box-shadow:0 0 34px rgba(0,232,122,.5),0 0 60px rgba(0,232,122,.18)} }
    @keyframes bdr       { 0%,100%{border-color:var(--border);box-shadow:none} 50%{border-color:rgba(0,170,255,.38);box-shadow:var(--gb)} }
    @keyframes blink     { 0%,100%{opacity:1} 50%{opacity:.25} }
    @keyframes recpulse  { 0%,100%{box-shadow:0 0 0 0 rgba(232,32,60,.5)} 70%{box-shadow:0 0 0 10px rgba(232,32,60,0)} }

    /* ══════════════════ HEADER ══════════════════ */
    .hdr {
        background:linear-gradient(135deg,#040c16,#08131f 60%,#040c16);
        border-bottom:1px solid var(--border);
        padding:16px 48px; display:flex; align-items:center; gap:20px;
        position:relative; overflow:hidden;
    }
    .hdr::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg,transparent,var(--blue),var(--red),var(--blue),transparent);
    }
    .hdr-logo {
        font-family:'Orbitron',sans-serif; font-size:20px; font-weight:900;
        color:var(--text); letter-spacing:5px; animation:flicker 9s infinite;
    }
    .hdr-logo b { color:var(--red); }
    .hdr-sub {
        font-family:'Share Tech Mono',monospace; font-size:9px;
        color:var(--blue); letter-spacing:4px; text-transform:uppercase; margin-top:3px;
    }
    .hdr-r { margin-left:auto; display:flex; align-items:center; gap:18px; }
    .online-badge {
        background:rgba(0,232,122,.06); border:1px solid rgba(0,232,122,.22);
        border-radius:4px; padding:5px 13px;
        font-family:'Share Tech Mono',monospace; font-size:9px;
        color:var(--green); letter-spacing:2px; display:flex; align-items:center; gap:6px;
    }
    .online-dot {
        width:5px; height:5px; background:var(--green); border-radius:50%;
        box-shadow:0 0 6px var(--green); animation:blink 2s infinite;
    }
    .hdr-user { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted); letter-spacing:2px; }
    .hdr-user b { color:var(--blue); font-weight:400; }

    /* logout col button */
    div[data-testid="column"]:last-child .stButton button {
        background:transparent !important; border:1px solid var(--border) !important;
        color:var(--muted) !important; font-family:'Share Tech Mono',monospace !important;
        font-size:9px !important; letter-spacing:2px !important;
        padding:5px 14px !important; box-shadow:none !important;
        width:auto !important; margin-top:0 !important;
    }
    div[data-testid="column"]:last-child .stButton button:hover {
        border-color:var(--red) !important; color:var(--red) !important;
        box-shadow:none !important; transform:none !important;
    }

    /* ══════════════════ LAYOUT ══════════════════ */
    .wrap { max-width:900px; margin:0 auto; padding:40px 24px; animation:fadeUp .5s ease; }

    /* hero */
    .hero { text-align:center; margin-bottom:40px; }
    .hero-tag {
        font-family:'Orbitron',sans-serif; font-size:10px; color:var(--blue);
        letter-spacing:7px; text-transform:uppercase; margin-bottom:12px;
    }
    .hero-h1 {
        font-family:'Rajdhani',sans-serif; font-size:44px; font-weight:700;
        color:var(--text); line-height:1.1; margin-bottom:12px;
    }
    .hero-h1 em { font-style:normal; color:var(--red); }
    .hero-p { color:var(--muted); font-size:16px; font-weight:300; max-width:500px; margin:0 auto; line-height:1.65; }

    /* stats */
    .stats { display:flex; justify-content:center; gap:16px; margin:24px 0; flex-wrap:wrap; }
    .stat {
        background:var(--c1); border:1px solid var(--border);
        border-radius:8px; padding:11px 20px; text-align:center; min-width:100px;
    }
    .stat-v { font-family:'Orbitron',sans-serif; font-size:18px; font-weight:700; color:var(--blue); }
    .stat-l { font-size:9px; color:var(--muted); letter-spacing:2px; text-transform:uppercase; margin-top:2px; }

    /* steps */
    .steps { display:flex; gap:12px; margin-bottom:30px; }
    .step {
        flex:1; background:var(--c1); border:1px solid var(--border);
        border-radius:10px; padding:16px 12px; text-align:center; transition:border-color .3s;
    }
    .step:hover { border-color:rgba(0,170,255,.3); }
    .step-n { font-family:'Orbitron',sans-serif; font-size:24px; font-weight:900; color:var(--blue); opacity:.3; line-height:1; margin-bottom:5px; }
    .step-t { font-weight:700; font-size:12px; color:var(--text); letter-spacing:1px; text-transform:uppercase; }
    .step-d { font-size:11px; color:var(--muted); margin-top:3px; line-height:1.4; }

    /* card */
    .card {
        background:var(--c1); border:1px solid var(--border);
        border-radius:12px; padding:28px; margin-bottom:20px;
        animation:bdr 5s ease-in-out infinite;
    }
    .sec-lbl {
        font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--blue);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:12px;
        display:flex; align-items:center; gap:8px;
    }
    .sec-lbl::after { content:''; flex:1; height:1px; background:linear-gradient(90deg,var(--border),transparent); }

    /* ── STREAMLIT WIDGETS ── */
    .stTextArea textarea {
        background:#030a12 !important; border:1px solid var(--border) !important;
        border-radius:8px !important; color:var(--text) !important;
        font-family:'Share Tech Mono',monospace !important; font-size:13px !important;
        line-height:1.75 !important; padding:13px !important;
        transition:border-color .3s,box-shadow .3s !important;
    }
    .stTextArea textarea:focus { border-color:rgba(0,170,255,.5) !important; box-shadow:var(--gb) !important; }
    .stTextArea textarea::placeholder { color:#1a3355 !important; }
    .stTextArea label { display:none !important; }

    /* primary button (analyze) */
    .stButton button {
        background:linear-gradient(135deg,#b81530,#801020) !important;
        color:white !important; border:none !important; border-radius:8px !important;
        font-family:'Orbitron',sans-serif !important; font-size:11px !important;
        font-weight:700 !important; letter-spacing:3px !important;
        padding:13px 28px !important; width:100% !important;
        box-shadow:0 4px 16px rgba(232,32,60,.28) !important;
        transition:all .3s !important; text-transform:uppercase !important;
    }
    .stButton button:hover {
        box-shadow:var(--gr),0 6px 26px rgba(232,32,60,.5) !important;
        transform:translateY(-1px) !important;
    }

    /* secondary / column buttons */
    div[data-testid="column"] .stButton button {
        background:rgba(0,170,255,.07) !important;
        border:1px solid rgba(0,170,255,.2) !important;
        color:var(--blue) !important; font-family:'Rajdhani',sans-serif !important;
        font-size:13px !important; font-weight:600 !important;
        letter-spacing:1px !important; padding:8px 16px !important;
        box-shadow:none !important; margin-top:0 !important;
    }
    div[data-testid="column"] .stButton button:hover {
        border-color:rgba(0,170,255,.45) !important;
        box-shadow:var(--gb) !important; transform:none !important;
    }

    .stSelectbox > div > div {
        background:#030a12 !important; border:1px solid var(--border) !important;
        color:var(--text) !important; border-radius:8px !important;
        font-family:'Rajdhani',sans-serif !important;
    }
    .stExpander { background:var(--c1) !important; border:1px solid var(--border) !important; border-radius:8px !important; }
    .stExpander summary { color:var(--muted) !important; font-family:'Share Tech Mono',monospace !important; font-size:10px !important; letter-spacing:2px !important; }

    /* tabs */
    .stTabs [data-baseweb="tab-list"] {
        background:rgba(0,0,0,.38) !important; border-radius:8px !important;
        padding:4px !important; gap:4px !important; border:none !important; margin-bottom:20px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--muted) !important;
        font-family:'Orbitron',sans-serif !important; font-size:9px !important;
        font-weight:700 !important; letter-spacing:2px !important;
        border-radius:6px !important; padding:10px 0 !important;
        border:none !important; flex:1 !important; text-align:center !important; text-transform:uppercase !important;
    }
    .stTabs [aria-selected="true"] {
        background:rgba(0,170,255,.1) !important; color:var(--blue) !important;
        border:1px solid rgba(0,170,255,.22) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding:0 !important; }
    .stTabs [data-baseweb="tab-highlight"] { display:none !important; }

    /* file uploader */
    .stFileUploader > div {
        background:#030a12 !important; border:1px dashed rgba(0,170,255,.22) !important;
        border-radius:8px !important; padding:8px !important;
    }
    .stFileUploader label, .stFileUploader p { color:var(--muted) !important; font-family:'Share Tech Mono',monospace !important; font-size:10px !important; }

    /* audio recorder component */
    .stAudioRecorder { filter:hue-rotate(200deg) saturate(0.6) brightness(1.2); }

    /* spinner */
    .stSpinner > div { border-top-color:var(--blue) !important; }

    /* boxes */
    .info-box {
        background:rgba(0,170,255,.05); border:1px solid rgba(0,170,255,.16);
        border-left:3px solid var(--blue); border-radius:6px;
        padding:10px 14px; font-size:13px; color:var(--muted); margin:10px 0;
        font-family:'Rajdhani',sans-serif; line-height:1.5;
    }
    .warn-box {
        background:rgba(240,168,0,.05); border:1px solid rgba(240,168,0,.18);
        border-left:3px solid var(--amber); border-radius:6px;
        padding:10px 14px; font-size:13px; color:#907020; margin:10px 0;
        font-family:'Rajdhani',sans-serif; line-height:1.5;
    }
    .success-box {
        background:rgba(0,232,122,.06); border:1px solid rgba(0,232,122,.2);
        border-left:3px solid var(--green); border-radius:6px;
        padding:10px 14px; font-size:13px; color:#306050; margin:10px 0;
        font-family:'Rajdhani',sans-serif; line-height:1.5;
    }

    /* ══════════════════ RECORDING WIDGET ══════════════════ */
    .rec-widget {
        background:linear-gradient(135deg,rgba(232,32,60,.08),rgba(100,0,20,.05));
        border:1px solid rgba(232,32,60,.25); border-radius:10px;
        padding:24px; text-align:center; margin:12px 0;
    }
    .rec-title {
        font-family:'Orbitron',sans-serif; font-size:12px; color:var(--red);
        letter-spacing:3px; text-transform:uppercase; margin-bottom:6px;
    }
    .rec-sub { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted); margin-bottom:16px; }
    .rec-dot {
        width:14px; height:14px; background:var(--red); border-radius:50%;
        display:inline-block; margin-right:8px;
        animation:recpulse 1.5s ease-in-out infinite, blink 1.5s ease-in-out infinite;
        box-shadow:0 0 8px var(--red);
    }
    .rec-status {
        font-family:'Share Tech Mono',monospace; font-size:11px; color:var(--red);
        display:flex; align-items:center; justify-content:center; margin-top:12px;
    }

    /* ══════════════════ RESULT CARDS ══════════════════ */
    .r-card { border-radius:12px; padding:28px; margin:20px 0; animation:fadeUp .4s ease; }
    .r-threat { background:linear-gradient(135deg,rgba(232,32,60,.1),rgba(150,0,25,.06)); border:1px solid rgba(232,32,60,.35); animation:pulsered 3s ease-in-out infinite; }
    .r-safe   { background:linear-gradient(135deg,rgba(0,232,122,.07),rgba(0,150,60,.04)); border:1px solid rgba(0,232,122,.3);  animation:pulsegreen 3s ease-in-out infinite; }
    .r-unknown{ background:linear-gradient(135deg,rgba(240,168,0,.06),rgba(150,100,0,.04)); border:1px solid rgba(240,168,0,.28); }

    .r-verdict { font-family:'Orbitron',sans-serif; font-size:24px; font-weight:900; letter-spacing:4px; margin-bottom:5px; }
    .r-sub     { font-size:14px; margin-top:2px; }
    .r-meta    { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted); margin-top:8px; }
    .c-red   { color:var(--red); }
    .c-green { color:var(--green); }
    .c-amber { color:var(--amber); }

    /* confidence bar */
    .cb-wrap { background:rgba(255,255,255,.05); border-radius:4px; height:7px; margin:12px 0 5px; overflow:hidden; }
    .cb-fill { height:100%; border-radius:4px; }
    .cb-red   { background:linear-gradient(90deg,#990018,#e8203c); }
    .cb-green { background:linear-gradient(90deg,#008840,#00e87a); }
    .cb-lbl   { font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted); display:flex; justify-content:space-between; }

    /* phrase chips */
    .phrase-box { background:rgba(232,32,60,.05); border:1px solid rgba(232,32,60,.16); border-radius:8px; padding:16px 20px; margin:12px 0; }
    .phrase-ttl { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--red); letter-spacing:3px; text-transform:uppercase; margin-bottom:10px; }
    .chip {
        display:inline-block; background:rgba(232,32,60,.12); border:1px solid rgba(232,32,60,.28);
        border-radius:4px; padding:3px 10px; margin:3px;
        font-family:'Share Tech Mono',monospace; font-size:11px; color:#e07080;
    }

    /* transcript box */
    .tx-box {
        background:#030a12; border:1px solid var(--border); border-radius:8px;
        padding:14px; font-family:'Share Tech Mono',monospace; font-size:12px;
        color:var(--muted); line-height:1.75; max-height:180px; overflow-y:auto; margin:12px 0;
    }
    mark.hlt {
        background:rgba(232,32,60,.18); border:1px solid rgba(232,32,60,.35);
        border-radius:3px; padding:1px 3px; color:#e08090;
        font-family:'Share Tech Mono',monospace;
    }

    /* explanation */
    .expl-card { background:var(--c2); border:1px solid var(--border); border-radius:8px; padding:16px 20px; margin:12px 0; }
    .expl-ttl  { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--blue); letter-spacing:3px; text-transform:uppercase; margin-bottom:12px; }
    .expl-row  { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
    .expl-term { font-family:'Share Tech Mono',monospace; font-size:11px; color:var(--text); min-width:115px; }
    .expl-bw   { flex:1; background:rgba(255,255,255,.05); border-radius:3px; height:5px; overflow:hidden; }
    .eb-r { background:var(--red);   height:100%; border-radius:3px; }
    .eb-g { background:var(--green); height:100%; border-radius:3px; }
    .expl-w    { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted); min-width:50px; text-align:right; }
    .expl-note { font-family:'Share Tech Mono',monospace; font-size:8px; color:#1a3355; margin-top:9px; }

    /* advice */
    .adv-card { background:var(--c1); border-radius:10px; padding:20px; margin:12px 0; }
    .adv-ttl  { font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:700; letter-spacing:2px; text-transform:uppercase; margin-bottom:12px; }
    .adv-item { display:flex; align-items:flex-start; gap:10px; margin-bottom:8px; font-size:14px; color:#90b0c8; line-height:1.5; }
    .adv-ico  { flex-shrink:0; margin-top:2px; font-family:'Share Tech Mono',monospace; font-size:12px; color:var(--muted); }

    /* history */
    .hist-row {
        display:flex; justify-content:space-between; align-items:center;
        padding:8px 12px; border-bottom:1px solid var(--border);
        font-family:'Share Tech Mono',monospace; font-size:11px;
    }
    .hist-row:last-child { border-bottom:none; }
    .badge-v { background:rgba(232,32,60,.14); border:1px solid rgba(232,32,60,.28); border-radius:3px; padding:2px 7px; color:var(--red);   font-size:9px; letter-spacing:1px; }
    .badge-s { background:rgba(0,232,122,.09);  border:1px solid rgba(0,232,122,.22); border-radius:3px; padding:2px 7px; color:var(--green); font-size:9px; letter-spacing:1px; }

    /* rate bar */
    .rl-wrap { display:flex; align-items:center; gap:10px; margin-bottom:16px; }
    .rl-bar  { flex:1; background:rgba(255,255,255,.05); border-radius:3px; height:3px; overflow:hidden; }
    .rl-fill { background:var(--blue); height:100%; border-radius:3px; }
    .rl-lbl  { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted); white-space:nowrap; }

    /* footer */
    .ftr {
        border-top:1px solid var(--border); padding:16px 48px;
        display:flex; justify-content:space-between; align-items:center; margin-top:52px;
    }
    .ftr-t { font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted); letter-spacing:2px; }

    /* scrollbar */
    ::-webkit-scrollbar { width:4px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--blue); }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════
def render_header():
    username  = st.session_state.get("user", "")
    user_html = f"<div class='hdr-user'>OPERATOR: <b>{username.upper()}</b></div>" if username else ""
    st.markdown(f"""
    <div class="hdr">
        <div>
            <div class="hdr-logo">SHIELD<b>GUARD</b></div>
            <div class="hdr-sub">Voice Threat Intelligence Platform</div>
        </div>
        <div class="hdr-r">
            {user_html}
            <div class="online-badge"><span class="online-dot"></span>SYSTEM ONLINE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# RESULT RENDERER
# ═══════════════════════════════════════════════
def render_result(label: str, confidence: float, text: str, model_choice: str):
    pct = int(confidence * 100)

    if label == "vishing":
        st.markdown(f"""
        <div class="r-card r-threat">
          <div style="text-align:center">
            <div class="r-verdict c-red">VISHING DETECTED</div>
            <div class="r-sub" style="color:#b05060">HIGH RISK — This call exhibits scam characteristics</div>
            <div class="cb-lbl" style="margin-top:13px">
                <span>THREAT CONFIDENCE</span>
                <span style="font-size:16px;font-weight:700;color:var(--red)">{pct}%</span>
            </div>
            <div class="cb-wrap"><div class="cb-fill cb-red" style="width:{pct}%"></div></div>
            <div class="r-meta">ENGINE: {model_choice.upper()} &nbsp;|&nbsp; VERDICT: MALICIOUS &nbsp;|&nbsp; CONFIDENCE: {pct}%</div>
          </div>
        </div>""", unsafe_allow_html=True)

        phrases = detect_suspicious_phrases(text)
        if phrases:
            chips = "".join(f'<span class="chip">{p}</span>' for p in phrases)
            st.markdown(f"""
            <div class="phrase-box">
                <div class="phrase-ttl">SUSPICIOUS PHRASES DETECTED — {len(phrases)} FOUND</div>
                {chips}
            </div>""", unsafe_allow_html=True)
            highlighted = build_highlighted_transcript(text, phrases)
            st.markdown('<div class="sec-lbl" style="margin-top:16px">ANNOTATED TRANSCRIPT</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tx-box">{highlighted}</div>', unsafe_allow_html=True)

        top_terms = get_explanation(model_choice, text)
        if top_terms:
            _render_explanation(top_terms, "AI REASONING — TOP THREAT INDICATORS")

        st.markdown("""
        <div class="adv-card" style="border:1px solid rgba(232,32,60,.16)">
            <div class="adv-ttl" style="color:var(--red)">IMMEDIATE ACTION REQUIRED</div>
            <div class="adv-item"><span class="adv-ico">[X]</span><span>Do <strong>NOT</strong> share any personal information, OTP, PIN, or bank account details.</span></div>
            <div class="adv-item"><span class="adv-ico">[X]</span><span>Hang up immediately. Do <strong>NOT</strong> call back any number given by the caller.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Call your bank directly using the number on the <strong>back of your card</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Report to <strong>Cyber999 Hotline: 1-300-88-2999</strong> or <strong>www.cybersafe.my</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Alert family members — especially elderly relatives — about this scam pattern.</span></div>
        </div>""", unsafe_allow_html=True)

    else:
        st.markdown(f"""
        <div class="r-card r-safe">
          <div style="text-align:center">
            <div class="r-verdict c-green">CALL APPEARS SAFE</div>
            <div class="r-sub" style="color:#50a870">LOW RISK — No vishing indicators detected</div>
            <div class="cb-lbl" style="margin-top:13px">
                <span>SAFETY CONFIDENCE</span>
                <span style="font-size:16px;font-weight:700;color:var(--green)">{pct}%</span>
            </div>
            <div class="cb-wrap"><div class="cb-fill cb-green" style="width:{pct}%"></div></div>
            <div class="r-meta">ENGINE: {model_choice.upper()} &nbsp;|&nbsp; VERDICT: BENIGN &nbsp;|&nbsp; CONFIDENCE: {pct}%</div>
          </div>
        </div>""", unsafe_allow_html=True)

        top_terms = get_explanation(model_choice, text)
        if top_terms:
            _render_explanation(top_terms, "AI REASONING — KEY SIGNAL TERMS")

        st.markdown("""
        <div class="adv-card" style="border:1px solid rgba(0,232,122,.1)">
            <div class="adv-ttl" style="color:var(--green)">GENERAL SECURITY REMINDERS</div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Always <strong>verify the caller's identity</strong> independently before sharing any information.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Legitimate banks will <strong>never</strong> ask for your full PIN, OTP, or password over the phone.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>When in doubt, hang up and call the institution via their <strong>official published number</strong>.</span></div>
            <div class="adv-item"><span class="adv-ico">[>]</span><span>Register with <strong>MCMC Do Not Disturb</strong> to reduce unsolicited calls.</span></div>
        </div>""", unsafe_allow_html=True)


def _render_explanation(top_terms, title):
    max_w = max(abs(w) for _, w in top_terms) or 1
    rows  = ""
    for term, weight in top_terms:
        bar_pct = int((abs(weight) / max_w) * 100)
        cls     = "eb-r" if weight > 0 else "eb-g"
        sign    = "+" if weight > 0 else "-"
        rows += f"""
        <div class="expl-row">
            <span class="expl-term">{term}</span>
            <div class="expl-bw"><div class="{cls}" style="width:{bar_pct}%"></div></div>
            <span class="expl-w">{sign} {abs(weight):.3f}</span>
        </div>"""
    st.markdown(f"""
    <div class="expl-card">
        <div class="expl-ttl">{title}</div>
        {rows}
        <div class="expl-note">+ pushes toward VISHING &nbsp;|&nbsp; - pushes toward SAFE</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════
def render_history():
    username = st.session_state.get("user", "")
    history  = get_user_history(username, limit=10)
    if not history:
        st.markdown('<div class="info-box">No analysis history yet. Run your first scan above.</div>', unsafe_allow_html=True)
        return
    st.markdown('<div class="expl-card"><div class="expl-ttl">RECENT SCAN HISTORY</div>', unsafe_allow_html=True)
    for row in history:
        badge = f'<span class="badge-v">VISHING</span>' if row["verdict"] == "vishing" else f'<span class="badge-s">SAFE</span>'
        conf  = int(float(row["confidence"]) * 100)
        ts    = row["analyzed_at"][:16].replace("T", " ")
        mode  = row.get("input_mode", "text").upper()
        st.markdown(f"""
        <div class="hist-row">
            <span>{badge}</span>
            <span style="color:var(--muted)">{conf}% conf</span>
            <span style="color:var(--muted)">{row['model_used']}</span>
            <span style="color:var(--muted)">{mode}</span>
            <span style="color:#1a3355">{ts}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════
def render_app():
    inject_css()
    render_header()

    username = st.session_state.get("user", "")

    # Logout button — far right
    _, _, col_lo = st.columns([7, 1, 1])
    with col_lo:
        if st.button("LOGOUT", key="logout_btn"):
            for k in ["authenticated", "user", "transcript_ready",
                      "transcribed_text", "manual_text", "recorded_audio"]:
                st.session_state[k] = False if k == "authenticated" else None if k == "user" else "" if isinstance(st.session_state[k], str) else None
            st.rerun()

    st.markdown('<div class="wrap">', unsafe_allow_html=True)

    # ── HERO ──
    st.markdown("""
    <div class="hero">
        <div class="hero-tag">AI-Powered Voice Threat Detection</div>
        <div class="hero-h1">Detect <em>Voice Scam</em><br>Attacks Instantly</div>
        <div class="hero-p">
            Record, upload, or paste a call transcript. Our machine learning engine
            analyzes it in seconds and gives you a clear, explainable verdict.
        </div>
    </div>""", unsafe_allow_html=True)

    # ── STATS ──
    st.markdown("""
    <div class="stats">
        <div class="stat"><div class="stat-v">97.3%</div><div class="stat-l">Accuracy</div></div>
        <div class="stat"><div class="stat-v">4</div><div class="stat-l">AI Models</div></div>
        <div class="stat"><div class="stat-v">&lt;2s</div><div class="stat-l">Analysis</div></div>
        <div class="stat"><div class="stat-v">NLP</div><div class="stat-l">Powered</div></div>
        <div class="stat"><div class="stat-v">XAI</div><div class="stat-l">Explainable</div></div>
    </div>""", unsafe_allow_html=True)

    # ── STEPS ──
    st.markdown("""
    <div class="steps">
        <div class="step">
            <div class="step-n">01</div>
            <div class="step-t">Record or Upload</div>
            <div class="step-d">Record live audio, upload a file, or paste a transcript</div>
        </div>
        <div class="step">
            <div class="step-n">02</div>
            <div class="step-t">Analyze</div>
            <div class="step-d">AI transcribes speech then classifies the call</div>
        </div>
        <div class="step">
            <div class="step-n">03</div>
            <div class="step-t">Act on Results</div>
            <div class="step-d">Get verdict, phrase highlights, AI reasoning, and advice</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── RATE LIMIT ──
    allowed, used_count = check_rate_limit(username)
    rl_pct = int((used_count / MAX_ANALYSES_PER_HOUR) * 100)
    st.markdown(f"""
    <div class="rl-wrap">
        <span class="rl-lbl">USAGE</span>
        <div class="rl-bar"><div class="rl-fill" style="width:{rl_pct}%"></div></div>
        <span class="rl-lbl">{used_count} / {MAX_ANALYSES_PER_HOUR} scans this hour</span>
    </div>""", unsafe_allow_html=True)

    if not allowed:
        st.markdown(f'<div class="warn-box">Rate limit reached ({MAX_ANALYSES_PER_HOUR} scans/hour). Please wait before scanning again.</div>', unsafe_allow_html=True)
        st.stop()

    # ══════════════════════════════════════════
    # INPUT CARD
    # ══════════════════════════════════════════
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">INPUT METHOD</div>', unsafe_allow_html=True)

    tab_rec, tab_upload, tab_text = st.tabs([
        "Record Audio",
        "Upload Recording",
        "Paste Transcript",
    ])

    final_text = ""
    input_mode = "text"

    # ── TAB 1: RECORD AUDIO ──────────────────
    with tab_rec:
        st.markdown("""
        <div class="rec-widget">
            <div class="rec-title">Live Audio Capture</div>
            <div class="rec-sub">Click the microphone below to start recording the call</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class="info-box">
            Press the microphone button to start recording. Press again to stop.
            Audio is processed locally — nothing is sent to external servers.
            Requires microphone permission in your browser.
        </div>""", unsafe_allow_html=True)

        try:
            from audiorecorder import audiorecorder
            audio = audiorecorder("  Start Recording", "  Stop Recording")

            if len(audio) > 0:
                # Export to wav bytes
                buf = io.BytesIO()
                audio.export(buf, format="wav")
                audio_bytes = buf.getvalue()

                st.markdown('<div class="success-box">Recording captured. Click Transcribe to convert to text.</div>', unsafe_allow_html=True)
                st.audio(audio_bytes, format="audio/wav")

                if st.button("TRANSCRIBE RECORDING", key="transcribe_rec"):
                    with st.spinner("Transcribing audio with Whisper AI..."):
                        try:
                            transcript = transcribe_audio(audio_bytes, ".wav")
                            st.session_state["transcribed_text"] = transcript
                            st.session_state["transcript_ready"] = True
                        except RuntimeError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")

        except ImportError:
            st.markdown("""
            <div class="warn-box">
                Audio recorder not installed. Run in terminal:<br>
                <strong>pip install streamlit-audiorecorder</strong><br>
                Then restart the app.
            </div>""", unsafe_allow_html=True)

        if st.session_state.get("transcript_ready") and st.session_state.get("transcribed_text"):
            t = st.session_state["transcribed_text"]
            st.markdown('<div class="sec-lbl" style="margin-top:14px">TRANSCRIBED TEXT</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tx-box">{t[:2000]}</div>', unsafe_allow_html=True)
            final_text = t
            input_mode = "audio_record"

    # ── TAB 2: UPLOAD FILE ───────────────────
    with tab_upload:
        st.markdown("""
        <div class="info-box">
            Upload a saved call recording. Supported formats: .wav .mp3 .m4a .ogg .flac
            Maximum file size: 25 MB. Audio is processed locally and deleted immediately.
        </div>""", unsafe_allow_html=True)

        audio_file = st.file_uploader(
            "upload_audio", type=["wav", "mp3", "m4a", "ogg", "flac"],
            label_visibility="collapsed"
        )

        if audio_file is not None:
            file_mb = len(audio_file.getvalue()) / (1024 * 1024)
            if file_mb > 25:
                st.markdown('<div class="warn-box">File exceeds 25 MB. Please upload a shorter recording.</div>', unsafe_allow_html=True)
            else:
                suffix = Path(audio_file.name).suffix.lower()
                st.audio(audio_file.getvalue())
                if st.button("TRANSCRIBE FILE", key="transcribe_file"):
                    with st.spinner("Transcribing audio with Whisper AI..."):
                        try:
                            transcript = transcribe_audio(audio_file.getvalue(), suffix)
                            st.session_state["transcribed_text"] = transcript
                            st.session_state["transcript_ready"] = True
                        except RuntimeError as e:
                            st.error(str(e))
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")

        if st.session_state.get("transcript_ready") and st.session_state.get("transcribed_text"):
            t = st.session_state["transcribed_text"]
            st.markdown('<div class="sec-lbl" style="margin-top:14px">TRANSCRIBED TEXT</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tx-box">{t[:2000]}</div>', unsafe_allow_html=True)
            final_text = t
            input_mode = "audio_upload"

    # ── TAB 3: PASTE TRANSCRIPT ──────────────
    with tab_text:
        st.markdown("""
        <div class="info-box">
            Paste the call transcript directly. Minimum 5 words required.
            Use the sample buttons below to see how the system works.
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Load Sample Scam Call", key="sv"):
                st.session_state["manual_text"] = SAMPLE_VISHING
        with c2:
            if st.button("Load Sample Safe Call", key="ss"):
                st.session_state["manual_text"] = SAMPLE_SAFE

        typed = st.text_area(
            "manual_transcript",
            value=st.session_state.get("manual_text", ""),
            height=165,
            placeholder="Paste the call transcript here...",
            label_visibility="collapsed",
        )
        if typed.strip():
            final_text = typed
            input_mode = "text"

    # ── ADVANCED SETTINGS ────────────────────
    with st.expander("Advanced Settings — AI Model Selection"):
        model_choice = st.selectbox(
            "Detection Engine",
            ["SVM", "Logistic Regression", "Random Forest", "Neural Network"],
            help="SVM gives the best balance of speed and accuracy for this dataset.",
        )
        st.markdown("""
        <div class="info-box">
            SVM and Logistic Regression produce full AI Reasoning explanations.
            Random Forest and Neural Network provide verdict and confidence only.
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .card

    # ══════════════════════════════════════════
    # ANALYZE BUTTON
    # ══════════════════════════════════════════
    if st.button("ANALYZE TRANSCRIPT", key="analyze_btn"):
        if not final_text.strip():
            st.markdown("""
            <div class="r-card r-unknown">
              <div style="text-align:center;padding:14px">
                <div class="r-verdict c-amber" style="font-size:18px">NO INPUT DETECTED</div>
                <div style="color:var(--muted);margin-top:8px;font-family:'Rajdhani',sans-serif">
                    Record audio, upload a file, or paste a transcript first.
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            clean = sanitize_input(final_text, max_length=10000)
            with st.spinner("Scanning transcript for threat indicators..."):
                label, confidence = run_inference(clean, model_choice)
                is_insuff, reason = insufficient_evidence(clean, confidence)

            if is_insuff:
                st.markdown(f"""
                <div class="r-card r-unknown">
                  <div style="text-align:center">
                    <div class="r-verdict c-amber">INCONCLUSIVE</div>
                    <div style="color:var(--muted);font-family:'Rajdhani',sans-serif;font-size:14px;margin-top:8px">{reason}</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:9px;color:#1a3355;margin-top:12px">
                        Provide a longer transcript with more context.
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                log_analysis(username, len(clean), input_mode, model_choice, label, confidence)
                record_rate_event(username)
                render_result(label, confidence, clean, model_choice)

    # ── HISTORY ──
    st.markdown('<div style="margin-top:36px">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">YOUR SCAN HISTORY</div>', unsafe_allow_html=True)
    render_history()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── FOOTER ──
    st.markdown("""
    <div class="ftr">
        <div class="ftr-t">SHIELDGUARD v1.0 — CYBERSECURITY FYP</div>
        <div class="ftr-t">SVM + LR + RF + NN &nbsp;|&nbsp; WHISPER ASR &nbsp;|&nbsp; SUPABASE &nbsp;|&nbsp; XAI</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close .wrap