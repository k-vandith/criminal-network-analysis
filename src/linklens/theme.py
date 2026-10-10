CSS = r"""
<style>
:root{--ll-bg:#0b0d14;--ll-card:#141824;--ll-line:#282d40;--ll-text:#f4f5fb;--ll-muted:#9ba3bb;--ll-accent:#a49aff}
html,body,[data-testid="stAppViewContainer"],.stApp{background:var(--ll-bg);color:var(--ll-text);font-family:Inter,"Segoe UI",system-ui,sans-serif}
[data-testid="stSidebar"]{background:#10131d;border-right:1px solid var(--ll-line)}
[data-testid="stHeader"]{background:transparent}#MainMenu,footer{visibility:hidden}
.block-container{max-width:1440px;padding-top:1.5rem;padding-bottom:3rem}
h1,h2,h3{font-family:"Segoe UI",system-ui,sans-serif;letter-spacing:-.035em}
.ll-hero{padding:28px 30px;border:1px solid #34334f;border-radius:20px;background:radial-gradient(circle at 92% 8%,#31295b 0,transparent 34%),linear-gradient(135deg,#191c2c,#111521 70%);margin:6px 0 20px}
.ll-eyebrow{font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:#b6adff;font-weight:700}
.ll-hero h1{font-size:2.35rem;margin:.4rem 0}.ll-hero p{color:#c2c8da;font-size:1.03rem;max-width:780px}
.ll-card{background:var(--ll-card);border:1px solid var(--ll-line);border-radius:16px;padding:18px 20px;min-height:112px}
.ll-label{font-size:.75rem;color:var(--ll-muted);letter-spacing:.07em;text-transform:uppercase}.ll-value{font:600 1.9rem "Segoe UI",sans-serif;margin:5px 0}.ll-help{font-size:.82rem;color:var(--ll-muted)}
.ll-section{border-bottom:1px solid var(--ll-line);padding-bottom:9px;margin:26px 0 14px}.ll-tag{display:inline-block;padding:4px 9px;border-radius:100px;background:#282541;color:#d4ceff;font-size:.75rem;margin-right:5px}
div[data-testid="stDataFrame"],div[data-testid="stPlotlyChart"]{border:1px solid var(--ll-line);border-radius:14px;overflow:hidden}
.stButton>button{border-radius:10px;border:1px solid #49416f;font-weight:600;min-height:2.6rem}.stButton>button[kind="primary"]{background:#8b7cff;color:#0c0d16;border-color:#8b7cff}
[data-testid="stMetric"]{background:var(--ll-card);border:1px solid var(--ll-line);border-radius:14px;padding:14px}
[data-testid="stAlert"]{border-radius:12px}
</style>
"""
