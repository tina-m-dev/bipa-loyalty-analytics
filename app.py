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
.mapping-box {{ border:1px solid #f0d5e3; border-radius:12px; padding:12px; margin-bottom:12px; }}
.small-note {{ color:#666; font-size:0.85rem; }}
</style>
""", unsafe_allow_html=True)

st.title("BIPA Loyalty Analytics")
st.caption("Customer Value × Opportunity — synthetic CRVM portfolio prototype")

BASE = Path(__file__).parent / "data"
DEMO_TX = BASE / "transactions.csv"
DEMO_ITEMS = BASE / "transaction_items.csv"

@st.cache_data
def read_csv(path_or_buffer):
    return pd.read_csv(path_or_buffer)

def suggest(cols, options):
    low = {str(c).lower().strip(): c for c in cols}
    for x in options:
        if x in low:
            return low[x]
    return None

def map_field(label, cols, aliases, required=False, key_prefix=""):
    guess = suggest(cols, aliases)
    options = ["—"] + list(cols)
    default = options.index(guess) if guess in cols else 0
    suffix = " *" if required else ""
    return st.selectbox(label + suffix, options, index=default, key=f"map_{key_prefix}_{label}")

# ---------------- Sidebar: data loading ----------------
st.sidebar.header("1. Load your data")
st.sidebar.caption("Use the demo data or upload your own CSV files. Your column names do not need to match the demo.")

uploaded_tx = st.sidebar.file_uploader("Transaction-level CSV", type="csv", help="One row should represent one customer transaction / receipt.")
uploaded_items = st.sidebar.file_uploader("Transaction items CSV (optional)", type="csv", help="One row should represent one item or category line on a receipt.")

if uploaded_tx:
    tx_raw = pd.read_csv(uploaded_tx)
    tx_source = "Uploaded transaction data"
else:
    tx_raw = read_csv(DEMO_TX)
    tx_source = "Demo transaction data"

if uploaded_items:
    items_raw = pd.read_csv(uploaded_items)
    items_source = "Uploaded transaction items"
else:
    items_raw = read_csv(DEMO_ITEMS) if DEMO_ITEMS.exists() else None
    items_source = "Demo transaction items" if items_raw is not None else None

st.sidebar.success(tx_source)

# ---------------- Sidebar: mapping ----------------
st.sidebar.header("2. Map your columns")
st.sidebar.caption("Tell the app which CSV column corresponds to each business field. Required fields are marked with *.")

with st.sidebar.expander("Transaction data", expanded=True):
    tx_aliases = {
        "Transaction ID": ["transaction_id","receipt_id","basket_id","order_id"],
        "Customer ID": ["customer_id","customer","member_id","card_id","loyalty_id"],
        "Transaction date": ["date","transaction_date","purchase_date"],
        "Net sales": ["net_sales","sales","revenue","amount","net_revenue"],
        "Margin": ["margin","gross_margin","contribution_margin"],
        "Discount": ["discount","discount_amount"],
        "Points earned": ["points_earned","points"],
        "Points redeemed": ["points_redeemed","redeemed_points"],
        "Promotion used": ["promotion_used","promo_used","promotion"],
        "Store ID": ["store_id","store","location_id"],
    }
    tx_labels = {}
    for label, aliases in tx_aliases.items():
        tx_labels[label] = map_field(label, tx_raw.columns, aliases, label in ["Customer ID","Transaction date","Net sales"], key_prefix="tx")

items_labels = {}
if items_raw is not None:
    with st.sidebar.expander("Transaction items / categories", expanded=True):
        st.sidebar.caption("Use this file when a receipt can contain multiple categories. Category analysis will be based on item-level data.")
        items_aliases = {
            "Transaction ID": ["transaction_id","receipt_id","basket_id","order_id"],
            "Category": ["category","product_category","product_group"],
            "Item net sales": ["net_sales","sales","revenue","amount","line_sales"],
            "Item margin": ["margin","gross_margin","contribution_margin"],
        }
        for label, aliases in items_aliases.items():
            items_labels[label] = map_field(label, items_raw.columns, aliases, label in ["Transaction ID","Category"], key_prefix="items")

# Convert labels to canonical names.
required_labels = {"Customer ID":"customer_id", "Transaction date":"date", "Net sales":"net_sales"}
transaction_id_label = "Transaction ID"
optional_labels = {"Margin":"margin","Discount":"discount","Points earned":"points_earned","Points redeemed":"points_redeemed","Promotion used":"promotion_used","Store ID":"store_id"}
missing = [label for label in required_labels if tx_labels[label] == "—"]
if missing:
    st.warning("Please map these required transaction fields: " + ", ".join(missing))
    st.stop()

rename_tx = {tx_labels[k]: v for k,v in {**required_labels, **optional_labels}.items() if tx_labels[k] != "—"}
if tx_labels.get(transaction_id_label) != "—":
    rename_tx[tx_labels[transaction_id_label]] = "transaction_id"
tx = tx_raw.rename(columns=rename_tx).copy()

def numericize(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
tx["net_sales"] = pd.to_numeric(tx["net_sales"], errors="coerce")
tx = numericize(tx, ["margin","discount","points_earned","points_redeemed","promotion_used"])
tx = tx.dropna(subset=["customer_id","date","net_sales"])

# ---------------- Item-level category model ----------------
items = None
if items_raw is not None and items_labels.get("Transaction ID") != "—" and items_labels.get("Category") != "—":
    rename_items = {
        items_labels["Transaction ID"]:"transaction_id",
        items_labels["Category"]:"category",
    }
    for label, canonical in [("Item net sales","net_sales"),("Item margin","margin")]:
        if items_labels.get(label) not in (None,"—"):
            rename_items[items_labels[label]] = canonical
    items = items_raw.rename(columns=rename_items).copy()
    items["category"] = items["category"].astype(str)
    if "net_sales" in items:
        items["net_sales"] = pd.to_numeric(items["net_sales"], errors="coerce").fillna(0)
    if "margin" in items:
        items["margin"] = pd.to_numeric(items["margin"], errors="coerce").fillna(0)

as_of = tx.date.max() + pd.Timedelta(days=1)
g = tx.groupby("customer_id").agg(
    last_purchase=("date","max"),
    frequency=("customer_id","count"),
    monetary=("net_sales","sum")
).reset_index()
g["recency_days"] = (as_of - g.last_purchase).dt.days
g["avg_basket"] = g.monetary / g.frequency.replace(0, np.nan)

if "margin" in tx:
    m = tx.groupby("customer_id").margin.sum()
    g["margin"] = g.customer_id.map(m).fillna(0)
    g["margin_rate"] = g.margin / g.monetary.replace(0, np.nan)
else:
    g["margin"] = np.nan
    g["margin_rate"] = np.nan

g["promo_share"] = g.customer_id.map(tx.groupby("customer_id").promotion_used.mean()).fillna(0) if "promotion_used" in tx else 0

if items is not None:
    item_customer = items.merge(tx[["transaction_id","customer_id"]], on="transaction_id", how="inner") if "transaction_id" in tx.columns else None
    if item_customer is not None:
        g["category_breadth"] = g.customer_id.map(item_customer.groupby("customer_id").category.nunique()).fillna(0)
    else:
        g["category_breadth"] = 0
else:
    g["category_breadth"] = 1

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

# ---------------- KPI header ----------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Customers", f"{g.customer_id.nunique():,}")
c2.metric("Revenue", f"€{tx.net_sales.sum():,.0f}")
c3.metric("Transactions", f"{len(tx):,}")
c4.metric("Avg. basket", f"€{tx.net_sales.mean():.2f}")

if items is not None:
    st.caption("Category analysis uses transaction-item data: one receipt can contain multiple categories.")
else:
    st.caption("No transaction-item file mapped. Category breadth is unavailable for detailed category analysis.")

# ---------------- Tabs ----------------
t1,t2,t3,t4,t5 = st.tabs(["Customer Segments","RFM Explorer","Category Analysis","Loyalty Economics","Data Quality"])

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
    st.info("The opportunity score is an illustrative behavioural score, not a predictive model. In a real CRVM environment it should be validated with historical uplift and controlled experiments.")

with t2:
    st.subheader("RFM Explorer")
    st.dataframe(
        g[["customer_id","recency_days","frequency","monetary","avg_basket","R_score","F_score","M_score","segment"]].head(500),
        use_container_width=True, hide_index=True
    )
    st.caption("First 500 customers shown.")

with t3:
    st.subheader("Category Analysis")
    if items is None:
        st.warning("Map a transaction-item CSV with Transaction ID and Category to enable item-level category analysis.")
    else:
        category = items.groupby("category", as_index=False).agg(
            transactions=("transaction_id","nunique"),
            category_sales=("net_sales","sum") if "net_sales" in items else ("transaction_id","count")
        ).sort_values("category_sales", ascending=False)
        st.dataframe(category, use_container_width=True, hide_index=True)
        st.bar_chart(category.set_index("category")["category_sales"])

        st.markdown("### Example customer category breadth")
        breadth = g[["customer_id","category_breadth","monetary","segment"]].sort_values("category_breadth", ascending=False).head(100)
        st.dataframe(breadth, use_container_width=True, hide_index=True)
        st.caption("Category breadth = number of distinct categories purchased by the customer across their transaction items.")

with t4:
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

with t5:
    st.subheader("Data Quality")
    rows = []
    for c in ["customer_id","date","net_sales","margin","discount","points_earned","points_redeemed","promotion_used","store_id"]:
        rows.append({"field":c,"present":c in tx.columns,"missing_%":round(tx[c].isna().mean()*100,2) if c in tx else 100})
    if items is not None:
        for c in ["transaction_id","category","net_sales","margin"]:
            rows.append({"field":f"items.{c}","present":c in items.columns,"missing_%":round(items[c].isna().mean()*100,2) if c in items else 100})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption("Synthetic data — created to demonstrate an analytical approach. Results are not BIPA actuals or forecasts.")
