# BIPA Loyalty Analytics — CRVM Prototype

A synthetic customer analytics prototype exploring how loyalty data can be transformed into **customer segmentation, targeted actions and loyalty investment decisions**.

> **Core business question:** For which customers does an additional €1 of loyalty investment generate the highest incremental contribution?

## What this demonstrates

- RFM-style customer analysis
- Customer **Value × Opportunity** segmentation
- Translation of segments into loyalty actions
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

## Data

The repository uses **synthetic data only**. The GitHub demo dataset is intentionally lightweight: it contains up to six transactions per synthetic customer so the repository stays suitable for a portfolio/demo project.

Fields include customer ID, transaction date, store, net sales, margin, discount, loyalty points, promotion usage and category.

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
│   └── transactions.csv
└── docs/
    └── bipa_case_one_pager.png
```

## Important note

This is a **portfolio prototype**, not an analysis of BIPA customer data. The simulator uses explicitly labelled illustrative assumptions. In a production setting, incremental impact should be estimated through controlled experiments/A-B testing and measured using incremental revenue, margin, retention, frequency, loyalty cost and ROI.

## Case one-pager

The `docs` folder contains the accompanying one-page CRVM thought piece: **BIPA Card — From Customer Data to Customer Value**.
