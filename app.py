import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="BIPA Loyalty Analytics", page_icon="📊", layout="wide")

PINK = "#E5007D"
LIGHT = "#FFF0F7"
DARK = "#2B1B25"

st.markdown(f"""
<style>
.stApp {{ background:#fff; }}
h1,h2,h3 {{ color:{DARK}; }}
div[data-testid="stMetric"] {{ border:1px solid #f0d5e3; padding:14px; border-radius:12px; background:{LIGHT}; }}
.small-note {{ color:#666; font-size:0.85rem; }}
</style>
""", unsafe_allow_html=True)

st.title("BIPA Loyalty Analytics")
st.caption("Customer Value × Opportunity — synthetic CRVM portfolio prototype")

DEMO = Path(__file__).parent / "data" / "transactions.csv"
uploaded = st.sidebar.file_uploader("Upload transaction CSV", type="csv")

@st.cache_data
def read_demo():
    return pd.read_csv(DEMO)

tx = pd.read_csv(uploaded) if uploaded else read_demo()

def suggest(cols, options):
    low = {str(c).lower().strip(): c for c in cols}
    for x in options:
        if x in low:
            return low[x]
    return None

aliases = {
    "customer_id": ["customer_id","customer","member_id","card_id","loyalty_id"],
    "date": ["date","transaction_date","purchase_date"],
    "net_sales": ["net_sales","sales","revenue","amount","net_revenue"],
    "margin": ["margin","gross_margin","contribution_margin"],
    "discount": ["discount","discount_amount"],
    "points_earned": ["points_earned","points"],
    "points_redeemed": ["points_redeemed","redeemed_points"],
    "promotion_used": ["promotion_used","promo_used","promotion"],
    "category": ["category","product_category","product_group"],
    "store_id": ["store_id","store","location_id"]
}

mapping = {}
for target, opts in aliases.items():
    guess = suggest(tx.columns, opts)
    default = list(tx.columns).index(guess) + 1 if guess in tx.columns else 0
    mapping[target] = st.sidebar.selectbox(target, ["—"] + list(tx.columns), index=default)
mapping = {k:v for k,v in mapping.items() if v != "—"}

missing = [x for x in ["customer_id","date","net_sales"] if x not in mapping]
if missing:
    st.warning("Map these required fields: " + ", ".join(missing))
    st.stop()

tx = tx.rename(columns={v:k for k,v in mapping.items()})
tx["date"] = pd.to_datetime(tx.date, errors="coerce")
tx["net_sales"] = pd.to_numeric(tx.net_sales, errors="coerce").fillna(0)
for c in ["margin","discount","points_earned","points_redeemed","promotion_used"]:
    if c in tx:
        tx[c] = pd.to_numeric(tx[c], errors="coerce").fillna(0)
tx = tx.dropna(subset=["customer_id","date"])

as_of = tx.date.max() + pd.Timedelta(days=1)
g = tx.groupby("customer_id").agg(
    last_purchase=("date","max"),
    frequency=("customer_id","count"),
    monetary=("net_sales","sum")
).reset_index()
g["recency_days"] = (as_of - g.last_purchase).dt.days
g["avg_basket"] = g.monetary / g.frequency

if "margin" in tx:
    m = tx.groupby("customer_id").margin.sum()
    g["margin"] = g.customer_id.map(m).fillna(0)
    g["margin_rate"] = g.margin / g.monetary.replace(0, np.nan)
else:
    g["margin"] = np.nan
    g["margin_rate"] = np.nan

g["promo_share"] = g.customer_id.map(tx.groupby("customer_id").promotion_used.mean()).fillna(0) if "promotion_used" in tx else 0
g["category_breadth"] = g.customer_id.map(tx.groupby("customer_id").category.nunique()).fillna(1) if "category" in tx else 1

g["R_score"] = pd.qcut(g.recency_days.rank(method="first"), 5, labels=[5,4,3,2,1]).astype(int)
g["F_score"] = pd.qcut(g.frequency.rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
g["M_score"] = pd.qcut(g.monetary.rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
g["value_score"] = g.M_score * 0.6 + g.F_score * 0.4
g["opportunity_score"] = (
    g.R_score * 0.45
    + g.promo_share.rank(pct=True) * 5 * 0.35
    + g.category_breadth.rank(pct=True) * 5 * 0.20
)
v = g.value_score >= g.value_score.median()
o = g.opportunity_score >= g.opportunity_score.median()
g["segment"] = np.select(
    [v&o, v&~o, ~v&o],
    ["High Value / High Opportunity", "High Value / Low Opportunity", "Low Value / High Opportunity"],
    default="Low Value / Low Opportunity"
)
g["strategy"] = g.segment.map({
    "High Value / High Opportunity":"Protect & Grow",
    "High Value / Low Opportunity":"Retain Efficiently",
    "Low Value / High Opportunity":"Develop",
    "Low Value / Low Opportunity":"Automate / Low-cost"
})

c1,c2,c3,c4 = st.columns(4)
c1.metric("Customers", f"{g.customer_id.nunique():,}")
c2.metric("Revenue", f"€{tx.net_sales.sum():,.0f}")
c3.metric("Transactions", f"{len(tx):,}")
c4.metric("Avg. basket", f"€{tx.net_sales.mean():.2f}")

t1,t2,t3,t4 = st.tabs(["Customer Segments","RFM Explorer","Loyalty Economics","Data Quality"])

with t1:
    st.subheader("Customer Value × Opportunity")
    seg = g.groupby(["segment","strategy"], as_index=False).agg(
        customers=("customer_id","count"),
        revenue=("monetary","sum"),
        avg_basket=("avg_basket","mean"),
        frequency=("frequency","mean")
    )
    seg["revenue_share"] = seg.revenue / tx.net_sales.sum()
    st.dataframe(seg, use_container_width=True, hide_index=True)
    st.bar_chart(seg.set_index("segment")["customers"])
    st.markdown("### Recommended treatment")
    st.write("**Protect & Grow:** targeted incentive · **Retain Efficiently:** low-cost retention · **Develop:** activation/cross-sell · **Automate:** low-cost digital engagement.")

with t2:
    st.subheader("RFM Explorer")
    st.dataframe(
        g[["customer_id","recency_days","frequency","monetary","avg_basket","R_score","F_score","M_score","segment"]].head(500),
        use_container_width=True, hide_index=True
    )
    st.caption("First 500 customers shown.")

with t3:
    st.subheader("Loyalty Economics")
    if "points_earned" in tx:
        earned = tx.points_earned.sum()
        redeemed = tx.points_redeemed.sum() if "points_redeemed" in tx else 0
        a,b,c = st.columns(3)
        a.metric("Points earned", f"{earned:,.0f}")
        b.metric("Points redeemed", f"{redeemed:,.0f}")
        c.metric("Reward cost @ €0.01", f"€{redeemed*0.01:,.0f}")
        st.info("Baseline is a modelling assumption based on the currently published BIPA loyalty rule: 1 point per €1 and €0.01 per point.")
    else:
        st.warning("Points data not provided.")

    st.markdown("### Loyalty investment simulator")
    budget = st.slider("Illustrative loyalty budget (€)", 1000, 50000, 10000, 1000)
    selected = st.selectbox("Target segment", list(seg["strategy"]))
    row = seg[seg.strategy == selected].iloc[0]
    # Illustrative scenario assumptions, deliberately transparent rather than predictive.
    uplift = {"Protect & Grow":0.03, "Retain Efficiently":0.015, "Develop":0.08, "Automate / Low-cost":0.005}[selected]
    avg_margin_rate = float(g.margin_rate.median()) if g.margin_rate.notna().any() else 0.30
    incremental_revenue = row.avg_basket * row.frequency * row.customers * uplift
    incremental_margin = incremental_revenue * avg_margin_rate
    estimated_roi = incremental_margin / budget if budget else 0
    a,b,c = st.columns(3)
    a.metric("Illustrative incremental revenue", f"€{incremental_revenue:,.0f}")
    b.metric("Illustrative incremental margin", f"€{incremental_margin:,.0f}")
    c.metric("Illustrative ROI", f"{estimated_roi:.2f}x")
    st.caption("Illustrative scenario only — uplift assumptions are not forecasts and are not based on BIPA customer data. A real business case should estimate uplift through controlled experiments.")
    st.markdown("### Core question")
    st.write("**For which customers does an additional €1 of loyalty investment generate the highest incremental contribution?**")

with t4:
    st.subheader("Data Quality")
    rows = []
    for c in ["customer_id","date","net_sales","margin","discount","points_earned","points_redeemed","promotion_used","category","store_id"]:
        rows.append({"column":c,"present":c in tx.columns,"missing_%":round(tx[c].isna().mean()*100,2) if c in tx else 100})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption("Synthetic data — created to demonstrate an analytical approach. Results are not BIPA actuals or forecasts.")
