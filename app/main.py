import streamlit as st
from auth import validate_password, validate_username, hash_password, verify_password
from database import (
    init_db,
    get_user, create_user,
    record_login_attempt, is_locked_out, count_recent_failures,
    MAX_ATTEMPTS, LOCKOUT_MINUTES
)
from streamlit_app import render_app

# -------------------------------------------------
# Init
# -------------------------------------------------
init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "login_attempt_user" not in st.session_state:
    st.session_state.login_attempt_user = ""

# -------------------------------------------------
# AUTH CSS
# -------------------------------------------------
def inject_auth_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&family=Share+Tech+Mono&display=swap');

    :root {
        --bg:     #04080f;
        --card:   #08111c;
        --red:    #e8203c;
        --green:  #00e87a;
        --blue:   #00aaff;
        --text:   #d8eaf8;
        --muted:  #4a7090;
        --border: #112233;
        --glow:   0 0 18px rgba(0,170,255,.3);
    }

    .stApp {
        background: var(--bg) !important;
        background-image:
            radial-gradient(ellipse at 25% 25%, rgba(0,80,170,.09) 0%, transparent 55%),
            radial-gradient(ellipse at 75% 75%, rgba(232,32,60,.06) 0%, transparent 55%),
            repeating-linear-gradient(0deg,  transparent,transparent 48px,rgba(0,170,255,.018) 48px,rgba(0,170,255,.018) 49px),
            repeating-linear-gradient(90deg, transparent,transparent 48px,rgba(0,170,255,.018) 48px,rgba(0,170,255,.018) 49px)
            !important;
        font-family: 'Rajdhani', sans-serif !important;
        color: var(--text) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }

    @keyframes fadeUp    { from{opacity:0;transform:translateY(24px);} to{opacity:1;transform:translateY(0);} }
    @keyframes flicker   { 0%,94%,100%{opacity:1;} 95%,99%{opacity:.78;} }
    @keyframes glowpulse { 0%,100%{opacity:.35;transform:scaleX(.3);} 50%{opacity:1;transform:scaleX(1);} }

    .auth-page {
        min-height:100vh; display:flex; flex-direction:column;
        align-items:center; justify-content:center; padding:48px 20px;
    }

    .brand { text-align:center; margin-bottom:36px; animation:fadeUp .5s ease; }
    .brand-logo {
        font-family:'Orbitron',sans-serif; font-size:34px; font-weight:900;
        color:var(--text); letter-spacing:6px; animation:flicker 7s infinite;
    }
    .brand-logo b { color:var(--red); }
    .brand-sub {
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:var(--blue); letter-spacing:6px; text-transform:uppercase; margin-top:5px;
    }
    .brand-desc { font-size:15px; color:var(--muted); margin-top:10px; }

    .auth-card {
        background:var(--card); border:1px solid var(--border);
        border-radius:14px; padding:42px 46px; width:100%; max-width:460px;
        position:relative; overflow:hidden; animation:fadeUp .6s ease;
    }
    .auth-card::before {
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg,transparent 0%,var(--blue) 30%,var(--red) 70%,transparent 100%);
    }
    .auth-card::after {
        content:''; position:absolute; top:2px; left:20%; right:20%;
        height:1px; background:var(--blue); opacity:.35; filter:blur(3px);
        animation:glowpulse 3.5s ease-in-out infinite;
    }

    .stTabs [data-baseweb="tab-list"] {
        background:rgba(0,0,0,.35) !important; border-radius:8px !important;
        padding:4px !important; gap:4px !important; border:none !important; margin-bottom:26px !important;
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

    .flbl {
        font-family:'Share Tech Mono',monospace; font-size:10px; color:var(--muted);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:5px; margin-top:18px;
    }

    .stTextInput > div > div > input {
        background:#020911 !important; border:1px solid var(--border) !important;
        border-radius:8px !important; color:var(--text) !important;
        font-family:'Rajdhani',sans-serif !important; font-size:16px !important;
        font-weight:500 !important; padding:13px 17px !important; letter-spacing:.5px !important;
        transition:border-color .3s, box-shadow .3s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:rgba(0,170,255,.5) !important; box-shadow:var(--glow) !important;
    }
    .stTextInput > div > div > input::placeholder { color:#1a3a55 !important; }
    .stTextInput label { display:none !important; }

    .stButton button {
        background:linear-gradient(135deg, #0055bb, #003a88) !important;
        color:white !important; border:1px solid rgba(0,170,255,.28) !important;
        border-radius:8px !important; font-family:'Orbitron',sans-serif !important;
        font-size:11px !important; font-weight:700 !important; letter-spacing:4px !important;
        padding:14px !important; width:100% !important; margin-top:22px !important;
        box-shadow:0 4px 18px rgba(0,80,200,.22) !important; transition:all .3s !important;
        text-transform:uppercase !important;
    }
    .stButton button:hover {
        background:linear-gradient(135deg, #0070dd, #0050aa) !important;
        box-shadow:0 4px 28px rgba(0,170,255,.38) !important; transform:translateY(-1px) !important;
    }

    .stSuccess > div {
        background:rgba(0,232,122,.08) !important; border:1px solid rgba(0,232,122,.28) !important;
        border-radius:8px !important; color:var(--green) !important;
        font-family:'Rajdhani',sans-serif !important; font-size:15px !important;
    }
    .stError > div {
        background:rgba(232,32,60,.08) !important; border:1px solid rgba(232,32,60,.28) !important;
        border-radius:8px !important; color:var(--red) !important;
        font-family:'Rajdhani',sans-serif !important; font-size:15px !important;
    }
    .stWarning > div {
        background:rgba(240,168,0,.07) !important; border:1px solid rgba(240,168,0,.25) !important;
        border-radius:8px !important; color:#d09020 !important;
        font-family:'Rajdhani',sans-serif !important; font-size:15px !important;
    }

    .pw-hint {
        background:rgba(0,0,0,.35); border:1px solid rgba(0,170,255,.1);
        border-radius:6px; padding:12px 15px; margin-top:9px;
        font-family:'Share Tech Mono',monospace; font-size:10px;
        color:#2a5070; line-height:1.9; letter-spacing:.5px;
    }

    .lock-box {
        background:rgba(232,32,60,.07); border:1px solid rgba(232,32,60,.25);
        border-left:3px solid var(--red); border-radius:8px;
        padding:14px 18px; margin:14px 0;
        font-family:'Share Tech Mono',monospace; font-size:11px; color:#c04060; line-height:1.7;
    }

    .badges { display:flex; justify-content:center; gap:18px; margin-top:28px; flex-wrap:wrap; }
    .sbadge {
        font-family:'Share Tech Mono',monospace; font-size:9px; color:#1a3a55;
        letter-spacing:2px; display:flex; align-items:center; gap:5px;
    }
    .sdot { width:4px; height:4px; background:#0a4a28; border-radius:50%; box-shadow:0 0 5px #00e87a; }

    .auth-ftr {
        text-align:center; margin-top:24px;
        font-family:'Share Tech Mono',monospace; font-size:9px; color:#0e2235; letter-spacing:3px;
    }

    ::-webkit-scrollbar { width:5px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
    </style>
    """, unsafe_allow_html=True)


# -------------------------------------------------
# LOGIN PAGE
# -------------------------------------------------
def login_page():
    st.markdown('<div class="flbl">Username</div>', unsafe_allow_html=True)
    username = st.text_input(
        "u", key="login_username",
        placeholder="Enter username",
        label_visibility="collapsed"
    )

    st.markdown('<div class="flbl">Password</div>', unsafe_allow_html=True)
    password = st.text_input(
        "p", key="login_password", type="password",
        placeholder="Enter password",
        label_visibility="collapsed"
    )

    # Check lockout state before showing button
    if username.strip():
        locked, mins_remaining = is_locked_out(username.strip())
        if locked:
            st.markdown(f"""
            <div class="lock-box">
                ACCOUNT TEMPORARILY LOCKED<br>
                Too many failed attempts. Try again in approximately {mins_remaining} minute(s).<br>
                Max attempts: {MAX_ATTEMPTS} &nbsp;|&nbsp; Lockout window: {LOCKOUT_MINUTES} minutes
            </div>
            """, unsafe_allow_html=True)
            return

    if st.button("ACCESS SYSTEM", key="login_btn"):
        uname = username.strip()
        if not uname or not password:
            st.error("Username and password are required.")
            return

        # Check lockout before querying DB
        locked, mins_remaining = is_locked_out(uname)
        if locked:
            st.error(f"Account locked. Try again in {mins_remaining} minute(s).")
            return

        user_row = get_user(uname)

        if user_row and verify_password(password, user_row["password_hash"]):
            record_login_attempt(uname, success=True)
            st.session_state.authenticated   = True
            st.session_state.user            = uname
            st.session_state["transcript_ready"]   = False
            st.session_state["transcribed_text"]   = ""
            st.session_state["manual_text"]        = ""
            st.success("Authentication successful. Loading system...")
            st.rerun()
        else:
            record_login_attempt(uname, success=False)
            st.session_state.login_attempt_user = uname

            # Re-check lockout after recording
            locked_now, mins_now = is_locked_out(uname)
            if locked_now:
                st.error(
                    f"Account locked after {MAX_ATTEMPTS} failed attempts. "
                    f"Try again in {mins_now} minute(s)."
                )
            else:
                failures   = count_recent_failures(uname)
                remaining  = MAX_ATTEMPTS - failures
                st.error(
                    f"Invalid credentials. "
                    f"{remaining} attempt(s) remaining before lockout."
                )


# -------------------------------------------------
# REGISTER PAGE
# -------------------------------------------------
def register_page():
    st.markdown('<div class="flbl">Username</div>', unsafe_allow_html=True)
    username = st.text_input(
        "ru", key="reg_username",
        placeholder="Choose a username (letters, numbers, underscore)",
        label_visibility="collapsed"
    )

    st.markdown('<div class="flbl">Password</div>', unsafe_allow_html=True)
    password = st.text_input(
        "rp", key="reg_password", type="password",
        placeholder="Minimum 12 characters",
        label_visibility="collapsed"
    )

    st.markdown('<div class="flbl">Confirm Password</div>', unsafe_allow_html=True)
    confirm = st.text_input(
        "rc", key="reg_confirm", type="password",
        placeholder="Re-enter your password",
        label_visibility="collapsed"
    )

    st.markdown("""
    <div class="pw-hint">
        PASSWORD REQUIREMENTS<br>
        &mdash; 12 or more characters<br>
        &mdash; At least one uppercase and one lowercase letter<br>
        &mdash; At least one number<br>
        &mdash; At least one special character &nbsp;( ! @ # $ % ^ &amp; * ... )
    </div>
    """, unsafe_allow_html=True)

    if st.button("CREATE ACCOUNT", key="reg_btn"):
        uname = username.strip()

        u_ok, u_msg = validate_username(uname)
        if not u_ok:
            st.error(u_msg)
            return

        p_ok, p_msg = validate_password(password)
        if not p_ok:
            st.error(p_msg)
            return

        if password != confirm:
            st.error("Passwords do not match.")
            return

        try:
            create_user(uname, hash_password(password))
            st.success("Account created successfully. Please log in.")
        except Exception:
            st.error("Username already exists. Please choose a different username.")


# -------------------------------------------------
# ROUTER
# -------------------------------------------------
if not st.session_state.authenticated:
    inject_auth_css()

    st.markdown("""
    <div class="auth-page">
        <div class="brand">
            <div class="brand-logo">SHIELD<b>GUARD</b></div>
            <div class="brand-sub">Voice Threat Intelligence Platform</div>
            <div class="brand-desc">AI-powered vishing detection — built for everyone</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        login_page()
    with tab2:
        register_page()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="badges">
            <div class="sbadge"><span class="sdot"></span>BCRYPT HASHING</div>
            <div class="sbadge"><span class="sdot"></span>BRUTE-FORCE LOCKOUT</div>
            <div class="sbadge"><span class="sdot"></span>SUPABASE CLOUD DB</div>
            <div class="sbadge"><span class="sdot"></span>AUDIT LOGGING</div>
            <div class="sbadge"><span class="sdot"></span>INPUT SANITIZED</div>
        </div>
        <div class="auth-ftr">
            SHIELDGUARD v1.0 &nbsp;·&nbsp; CYBERSECURITY FYP &nbsp;·&nbsp; UNAUTHORIZED ACCESS IS PROHIBITED
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    render_app()