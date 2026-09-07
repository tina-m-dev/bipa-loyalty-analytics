# BIPA Loyalty Analytics — CRVM Prototype

A synthetic customer analytics prototype exploring how loyalty data can be transformed into **customer segmentation, targeted actions and loyalty investment decisions**.

> **Core business question:** For which customers does an additional €1 of loyalty investment generate the highest incremental contribution?

## What this demonstrates

- RFM-style customer analysis
- Customer **Value × Opportunity** segmentation
- Translation of segments into loyalty actions
- Item-level category analysis and category breadth
- Loyalty economics and an illustrative investment simulator
- SQL/BI-style KPI thinking implemented in Python + Streamlit
- Data-quality checks and flexible CSV column mapping

## Analytical logic

The prototype separates two questions that are often treated as one:

**Customer value:** How valuable is this customer today?

**Customer opportunity:** How much potential is there to change their future behaviour?

This creates four actionable groups:

| Segment | Suggested treatment |
|---|---|
| High Value / High Opportunity | Protect & Grow |
| High Value / Low Opportunity | Retain Efficiently |
| Low Value / High Opportunity | Develop |
| Low Value / Low Opportunity | Automate / Low-cost |

The objective is not to maximize points redemption. **The objective is to maximize incremental customer value.**

## Data model

The demo intentionally separates **receipts** from **receipt items/categories**.

### `transactions.csv`

One row = one customer transaction / receipt. It contains customer, date, store, sales, margin, discount, loyalty points and promotion fields.

### `transaction_items.csv`

One row = one item/category line within a receipt. A single receipt can therefore contain multiple categories — for example, Baby + Hair Care + Oral Care.

This enables more meaningful CRVM analysis such as:

- category breadth
- category penetration
- cross-category behaviour
- potential cross-sell opportunities

## Flexible CSV mapping

The app does not require the uploaded CSV to use the same column names as the demo.

For example, your customer identifier could be called `member_id`, `card_id` or `customer_id`. In the sidebar, map that column to the business field **Customer ID**.

Required transaction fields:

- Customer ID
- Transaction date
- Net sales

Optional transaction fields include margin, discount, loyalty points, promotion usage and Store ID.

For item-level category analysis, provide a transaction-items CSV and map:

- Transaction ID
- Category
- optionally item net sales and item margin

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```text
bipa-loyalty-analytics/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── transactions.csv
│   └── transaction_items.csv
└── docs/
    └── bipa_case_one_pager.png
```

## Important note

This is a **portfolio prototype**, not an analysis of BIPA customer data. The opportunity score is an illustrative behavioural score, not a predictive model. The simulator uses explicitly labelled illustrative assumptions. In a production setting, incremental impact should be estimated through controlled experiments/A-B testing and measured using incremental revenue, margin, retention, frequency, loyalty cost and ROI.

## Case one-pager

The `docs` folder contains the accompanying one-page CRVM thought piece: **BIPA Card — From Customer Data to Customer Value**.
