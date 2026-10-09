"""Workspace chrome. Hides the default Streamlit document look."""

THEME_CSS = """
<style>
:root {
  --bg:#07090d; --panel:#10151c; --panel2:#0c1118; --line:#243041;
  --text:#e7edf5; --muted:#8b9bb0; --accent:#7eb6ff; --danger:#e06b75;
  --warn:#e2b15a; --ok:#6fbfa0;
}
html, body, .stApp { background:var(--bg) !important; color:var(--text); font-family:"Segoe UI", ui-sans-serif, system-ui, sans-serif; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility:hidden; height:0; }
.block-container { padding:0.6rem 1rem 1rem 1rem; max-width:100%; }
section[data-testid="stSidebar"] {
  background:#0a0e14; border-right:1px solid var(--line); width:220px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] { display:none; }
div[data-testid="stRadio"] label { font-size:0.86rem; }
.topbar {
  display:flex; align-items:center; gap:16px; border:1px solid var(--line);
  background:#0c1118; border-radius:10px; padding:10px 14px; margin-bottom:10px;
}
.brand { font-weight:600; letter-spacing:.16em; font-size:.78rem; color:var(--accent); }
.casechip { color:var(--text); font-size:.84rem; }
.live { margin-left:auto; color:var(--ok); font-size:.72rem; letter-spacing:.12em; }
.panel {
  background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:12px 14px; margin-bottom:10px;
}
.kicker { color:var(--muted); font-size:.68rem; letter-spacing:.14em; text-transform:uppercase; }
.h { font-size:1.05rem; font-weight:600; margin:.15rem 0 .4rem; }
.muted { color:var(--muted); font-size:.78rem; }
.statrow { display:flex; gap:18px; }
.stat b { display:block; font-size:1.25rem; font-weight:600; }
.stat span { color:var(--muted); font-size:.7rem; letter-spacing:.08em; text-transform:uppercase; }
.sig {
  border-left:2px solid var(--accent); background:#0c121a; border-radius:8px;
  padding:8px 10px; margin-bottom:8px;
}
.sig.warn { border-left-color:var(--warn); }
.sig.danger { border-left-color:var(--danger); }
.badge {
  display:inline-block; border:1px solid var(--line); border-radius:999px;
  padding:1px 7px; font-size:.68rem; color:var(--muted); margin-right:4px;
}
.notice { border:1px solid #2a3a28; background:#101611; color:#c9ddcf; border-radius:8px; padding:8px 10px; font-size:.78rem; }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; }
</style>
"""
