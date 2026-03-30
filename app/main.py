import os

# Ensure ffmpeg is on PATH (extracted at D:\ffmpeg)
_ffmpeg_bin = r"D:\ffmpeg\ffmpeg-8.1-essentials_build\bin"
if _ffmpeg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

# Tell pydub where ffmpeg/ffprobe are explicitly
from pydub import AudioSegment
AudioSegment.converter = os.path.join(_ffmpeg_bin, "ffmpeg.exe")
AudioSegment.ffprobe   = os.path.join(_ffmpeg_bin, "ffprobe.exe")

import streamlit as st
from auth import validate_password, validate_username, hash_password, verify_password
from database import (
    init_db,
    get_user, create_user,
    record_login_attempt, is_locked_out, count_recent_failures,
    MAX_ATTEMPTS, LOCKOUT_MINUTES
)
from streamlit_app import render_app
from rag_module import ensure_scam_library

# ─────────────────────────────────────────────
# Page config — must be FIRST streamlit call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title  = "ShieldGuard — Vishing Detection",
    page_icon   = "assets/favicon.png" if False else None,
    layout      = "centered",
    initial_sidebar_state = "collapsed",
)

# ─────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────
init_db()
ensure_scam_library()   # Phase 2: populate ChromaDB on first run

for key, default in {
    "authenticated":      False,
    "user":               None,
    "login_attempt_user": "",
    "transcript_ready":   False,
    "transcribed_text":   "",
    "manual_text":        "",
    "recorded_audio":     None,
    "llm_result":         None,      # Phase 2: crew output dict
    "rag_matches":        [],        # Phase 2: ChromaDB results
    "hybrid_mode":        False,     # Phase 2: whether LLM was triggered
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
# Auth-page CSS
# ─────────────────────────────────────────────
def inject_auth_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

    :root {
        --bg:      #04080f;
        --card:    #08111c;
        --red:     #e8203c;
        --green:   #00e87a;
        --blue:    #00aaff;
        --text:    #d8eaf8;
        --muted:   #4a7090;
        --border:  #112233;
        --glow:    0 0 20px rgba(0,170,255,.32);
    }

    /* ── global ── */
    html, body, .stApp {
        background: var(--bg) !important;
        font-family: 'Rajdhani', sans-serif !important;
        color: var(--text) !important;
    }
    .stApp {
        background-image:
            radial-gradient(ellipse at 20% 20%, rgba(0,80,170,.09) 0%, transparent 55%),
            radial-gradient(ellipse at 80% 80%, rgba(232,32,60,.06) 0%, transparent 55%),
            repeating-linear-gradient(0deg,  transparent,transparent 48px,rgba(0,170,255,.016) 48px,rgba(0,170,255,.016) 49px),
            repeating-linear-gradient(90deg, transparent,transparent 48px,rgba(0,170,255,.016) 48px,rgba(0,170,255,.016) 49px) !important;
    }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        max-width: 480px !important;
        padding-top: 6vh !important;
        padding-bottom: 4vh !important;
    }

    /* ── animations ── */
    @keyframes fadeUp    { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
    @keyframes flicker   { 0%,93%,100%{opacity:1} 94%,99%{opacity:.75} }
    @keyframes glowline  { 0%,100%{opacity:.3;transform:scaleX(.25)} 50%{opacity:1;transform:scaleX(1)} }

    /* ── brand block ── */
    .brand {
        text-align:center; margin-bottom:32px;
        animation: fadeUp .55s ease;
    }
    .brand-logo {
        font-family:'Orbitron',sans-serif; font-size:32px; font-weight:900;
        color:var(--text); letter-spacing:6px; animation:flicker 8s infinite;
        line-height:1;
    }
    .brand-logo b { color:var(--red); }
    .brand-sub {
        font-family:'Share Tech Mono',monospace; font-size:9px;
        color:var(--blue); letter-spacing:7px; text-transform:uppercase; margin-top:6px;
    }
    .brand-desc { font-size:14px; color:var(--muted); margin-top:8px; }

    /* ── auth card ── */
    .auth-card {
        background:var(--card); border:1px solid var(--border);
        border-radius:14px; padding:38px 40px 32px;
        position:relative; overflow:hidden;
        animation: fadeUp .65s ease;
    }
    .auth-card::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg,transparent,var(--blue) 30%,var(--red) 70%,transparent);
    }
    .auth-card::after {
        content:''; position:absolute; top:2px; left:15%; right:15%; height:1px;
        background:var(--blue); opacity:.3; filter:blur(3px);
        animation:glowline 3.5s ease-in-out infinite;
    }

    /* ── tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background:rgba(0,0,0,.4) !important; border-radius:8px !important;
        padding:4px !important; gap:4px !important;
        border:none !important; margin-bottom:24px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--muted) !important;
        font-family:'Orbitron',sans-serif !important; font-size:10px !important;
        font-weight:700 !important; letter-spacing:3px !important;
        border-radius:6px !important; padding:10px 0 !important;
        border:none !important; flex:1 !important; text-align:center !important;
        text-transform:uppercase !important;
    }
    .stTabs [aria-selected="true"] {
        background:rgba(0,170,255,.12) !important; color:var(--blue) !important;
        border:1px solid rgba(0,170,255,.25) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding:0 !important; }
    .stTabs [data-baseweb="tab-highlight"] { display:none !important; }

    /* ── field label ── */
    .flbl {
        font-family:'Share Tech Mono',monospace; font-size:9px; color:var(--muted);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:4px; margin-top:16px;
    }

    /* ── inputs ── */
    .stTextInput > div > div > input {
        background:#020911 !important; border:1px solid var(--border) !important;
        border-radius:8px !important; color:var(--text) !important;
        font-family:'Rajdhani',sans-serif !important; font-size:16px !important;
        font-weight:500 !important; padding:12px 16px !important;
        transition:border-color .3s, box-shadow .3s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:rgba(0,170,255,.55) !important; box-shadow:var(--glow) !important;
    }
    .stTextInput > div > div > input::placeholder { color:#1a3355 !important; }
    .stTextInput label { display:none !important; }

    /* ── button ── */
    .stButton button {
        background:linear-gradient(135deg,#0055bb,#003a88) !important;
        color:white !important; border:1px solid rgba(0,170,255,.3) !important;
        border-radius:8px !important; font-family:'Orbitron',sans-serif !important;
        font-size:11px !important; font-weight:700 !important; letter-spacing:4px !important;
        padding:13px !important; width:100% !important; margin-top:20px !important;
        box-shadow:0 4px 18px rgba(0,80,200,.2) !important; transition:all .3s !important;
    }
    .stButton button:hover {
        background:linear-gradient(135deg,#0070ee,#0055bb) !important;
        box-shadow:0 4px 28px rgba(0,170,255,.4) !important;
        transform:translateY(-1px) !important;
    }

    /* ── alerts ── */
    .stSuccess > div {
        background:rgba(0,232,122,.07) !important; border:1px solid rgba(0,232,122,.25) !important;
        border-radius:8px !important; color:var(--green) !important;
        font-family:'Rajdhani',sans-serif !important;
    }
    .stError > div {
        background:rgba(232,32,60,.07) !important; border:1px solid rgba(232,32,60,.25) !important;
        border-radius:8px !important; color:var(--red) !important;
        font-family:'Rajdhani',sans-serif !important;
    }

    /* ── password hint ── */
    .pw-hint {
        background:rgba(0,0,0,.3); border:1px solid rgba(0,170,255,.1);
        border-radius:6px; padding:11px 14px; margin-top:10px;
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:#2a5070; line-height:1.9;
    }

    /* ── lockout box ── */
    .lock-box {
        background:rgba(232,32,60,.07); border:1px solid rgba(232,32,60,.22);
        border-left:3px solid var(--red); border-radius:8px;
        padding:13px 16px; margin:12px 0;
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:#c04060; line-height:1.75;
    }

    /* ── security badges ── */
    .badges {
        display:flex; justify-content:center; gap:14px;
        margin-top:24px; flex-wrap:wrap;
    }
    .sbadge {
        font-family:'Share Tech Mono',monospace; font-size:8px;
        color:#1a3a55; letter-spacing:1px;
        display:flex; align-items:center; gap:4px;
    }
    .sdot {
        width:4px; height:4px; background:#0a4a28;
        border-radius:50%; box-shadow:0 0 5px #00e87a; flex-shrink:0;
    }

    /* ── footer ── */
    .auth-ftr {
        text-align:center; margin-top:20px;
        font-family:'Share Tech Mono',monospace; font-size:8px;
        color:#0d1e30; letter-spacing:2px;
    }

    /* ── scrollbar ── */
    ::-webkit-scrollbar { width:4px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────
def login_page():
    username = st.text_input(
        "__u", key="login_username",
        placeholder="Enter username",
        label_visibility="collapsed"
    )
    st.markdown('<div class="flbl" style="margin-top:14px;">Password</div>', unsafe_allow_html=True)
    password = st.text_input(
        "__p", key="login_password", type="password",
        placeholder="Enter password",
        label_visibility="collapsed"
    )

    if username.strip():
        locked, mins_left = is_locked_out(username.strip())
        if locked:
            st.markdown(f"""
            <div class="lock-box">
                ACCOUNT TEMPORARILY LOCKED<br>
                Too many failed attempts. Try again in {mins_left} minute(s).<br>
                Limit: {MAX_ATTEMPTS} attempts &nbsp;|&nbsp; Window: {LOCKOUT_MINUTES} min
            </div>""", unsafe_allow_html=True)
            return

    if st.button("ACCESS SYSTEM", key="login_btn"):
        uname = username.strip()
        if not uname or not password:
            st.error("Username and password are required.")
            return

        locked, mins_left = is_locked_out(uname)
        if locked:
            st.error(f"Account locked. Try again in {mins_left} minute(s).")
            return

        user_row = get_user(uname)
        if user_row and verify_password(password, user_row["password_hash"]):
            record_login_attempt(uname, success=True)
            for k, v in {
                "authenticated":    True,
                "user":             uname,
                "transcript_ready": False,
                "transcribed_text": "",
                "manual_text":      "",
                "recorded_audio":   None,
            }.items():
                st.session_state[k] = v
            st.success("Authentication successful — loading system...")
            st.rerun()
        else:
            record_login_attempt(uname, success=False)
            locked_now, mins_now = is_locked_out(uname)
            if locked_now:
                st.error(f"Account locked after {MAX_ATTEMPTS} failed attempts. Try again in {mins_now} minute(s).")
            else:
                failures  = count_recent_failures(uname)
                remaining = MAX_ATTEMPTS - failures
                st.error(f"Invalid credentials. {remaining} attempt(s) remaining before lockout.")


# ─────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────
def register_page():
    username = st.text_input(
        "__ru", key="reg_username",
        placeholder="Letters, numbers, underscore (3–32 chars)",
        label_visibility="collapsed"
    )
    st.markdown('<div class="flbl" style="margin-top:14px;">Password</div>', unsafe_allow_html=True)
    password = st.text_input(
        "__rp", key="reg_password", type="password",
        placeholder="Minimum 12 characters",
        label_visibility="collapsed"
    )
    st.markdown('<div class="flbl" style="margin-top:14px;">Confirm Password</div>', unsafe_allow_html=True)
    confirm = st.text_input(
        "__rc", key="reg_confirm", type="password",
        placeholder="Re-enter your password",
        label_visibility="collapsed"
    )

    st.markdown("""
    <div class="pw-hint">
        REQUIREMENTS &mdash; 12+ chars &nbsp;·&nbsp; Uppercase + lowercase<br>
        At least one number &nbsp;·&nbsp; One special char ( ! @ # $ % ^ &amp; * )
    </div>""", unsafe_allow_html=True)

    if st.button("CREATE ACCOUNT", key="reg_btn"):
        uname = username.strip()
        u_ok, u_msg = validate_username(uname)
        if not u_ok:
            st.error(u_msg); return
        p_ok, p_msg = validate_password(password)
        if not p_ok:
            st.error(p_msg); return
        if password != confirm:
            st.error("Passwords do not match."); return
        try:
            create_user(uname, hash_password(password))
            st.success("Account created. Please log in.")
        except Exception:
            st.error("Username already exists. Choose a different one.")


# ─────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────
if not st.session_state.authenticated:
    inject_auth_css()

    # Brand — uses st.markdown so it sits inside Streamlit's centered container
    st.markdown("""
    <div class="brand">
        <div class="brand-logo">SHIELD<b>GUARD</b></div>
        <div class="brand-sub">Voice Threat Intelligence Platform</div>
        <div class="brand-desc">AI-powered vishing detection — built for everyone</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        st.markdown('<div class="flbl">Username</div>', unsafe_allow_html=True)
        login_page()
    with tab2:
        st.markdown('<div class="flbl">Username</div>', unsafe_allow_html=True)
        register_page()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="badges">
        <div class="sbadge"><span class="sdot"></span>BCRYPT ROUNDS-12</div>
        <div class="sbadge"><span class="sdot"></span>BRUTE-FORCE LOCKOUT</div>
        <div class="sbadge"><span class="sdot"></span>SUPABASE CLOUD</div>
        <div class="sbadge"><span class="sdot"></span>AUDIT LOGGING</div>
        <div class="sbadge"><span class="sdot"></span>XSS SANITIZED</div>
    </div>
    <div class="auth-ftr">
        SHIELDGUARD v1.0 &nbsp;·&nbsp; CYBERSECURITY FYP &nbsp;·&nbsp; UNAUTHORIZED ACCESS IS PROHIBITED
    </div>
    """, unsafe_allow_html=True)

else:
    render_app()