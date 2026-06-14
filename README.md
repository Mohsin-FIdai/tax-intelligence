# 🔍 Graph AI for Broadening the National Tax Net

> Enterprise-grade AI-powered Tax Compliance Intelligence Platform for Pakistan

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-red.svg)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🏆 Hackathon Context
**Problem:** Pakistan faces a massive tax gap due to fragmented, siloed government databases (FBR, NADRA, Excise). Tax evaders exploit these disconnected systems to hide luxury assets while declaring zero income.
**Solution:** The Tax Intelligence Platform ingests, mathematically cleans, and merges these databases. Using Entity Resolution, XGBoost Risk Classification, and NetworkX Graph Theory, it autonomously uncovers hidden wealth, detects criminal syndicates, and estimates recoverable tax gaps.
**Team:** Tech Titans

## 🌐 Live Demo
*Live Demo URL:*[ [Deploying Soon to Streamlit Community Cloud / Render / Vercel]](https://tax-intelligence-nvzzehjuf88ynz8humgtdb.streamlit.app/)

---

## 🎯 Overview

This platform identifies potential tax evaders, under-reporting individuals, and suspicious financial behavior through **Knowledge Graphs**, **Entity Resolution**, **Machine Learning**, **Anomaly Detection**, and **Explainable AI**.

Built on synthetic Pakistani datasets, it demonstrates how siloed government databases can be intelligently connected to broaden the national tax net.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT DASHBOARD                   │
│  Executive │ Entity Res │ Graph │ Risk │ Profile │ Inv  │
├─────────────────────────────────────────────────────────┤
│                     FASTAPI BACKEND                      │
│     Citizens │ Graph │ Risk │ Search │ Reports APIs      │
├─────────────────────────────────────────────────────────┤
│                      CORE ENGINE                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │   ETL    │ │ Entity   │ │Knowledge │ │    ML    │  │
│  │ Pipeline │ │Resolution│ │  Graph   │ │ Pipeline │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │  Risk    │ │   XAI    │ │  Report  │               │
│  │ Scoring  │ │ Explainer│ │Generator │               │
│  └──────────┘ └──────────┘ └──────────┘               │
├─────────────────────────────────────────────────────────┤
│                    DATA LAYER                            │
│        Synthetic CSVs │ Processed Data │ Models          │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **🔗 Entity Resolution** — Links records across 8 databases using fuzzy matching, phonetic codes, and CNIC correlation
- **🕸️ Knowledge Graph** — 11 node types, 10 relationship types with interactive PyVis visualization
- **🤖 ML Anomaly Detection** — Ensemble of Isolation Forest, LOF, One-Class SVM
- **📊 Risk Scoring** — Deviation scores (0-100) with A-E categorization
- **🔍 Explainable AI** — SHAP-based explanations with human-readable audit trails
- **🇵🇰 Pakistan-Specific** — CNIC validation, PKR formatting, 200+ name variations
- **📄 PDF Reports** — Professional investigation and citizen reports
- **🎨 Enterprise Dashboard** — 6-page dark-themed Streamlit UI

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone or navigate to the project
cd tax-intelligence

# Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Generate data + run full ML pipeline
python run_pipeline.py
```

This will:
1. Generate 10,000 synthetic Pakistani citizens across 8 datasets
2. Run ETL: validate, clean, and normalize all data
3. Resolve entities across datasets into unified citizen profiles
4. Extract 20+ ML features per citizen
5. Train anomaly detection and risk classification models
6. Compute net worth estimates and deviation scores
7. Build a knowledge graph with 50K+ nodes

### Launch the Dashboard

```bash
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

### Launch the API (optional)

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`

---

## 🐳 Docker

```bash
docker-compose up --build
```

- Dashboard: `http://localhost:8501`
- API: `http://localhost:8000`

---

## 📁 Project Structure

```
tax-intelligence/
├── app/                          # Streamlit Dashboard
│   ├── streamlit_app.py          # Main entry point
│   ├── pages/                    # 6 dashboard pages
│   ├── components/               # Reusable UI components
│   └── styles/theme.css          # Premium dark theme CSS
├── backend/                      # FastAPI REST API
│   ├── main.py
│   ├── api/                      # Route modules
│   ├── models/schemas.py         # Pydantic schemas
│   └── services/data_service.py  # Data access layer
├── core/                         # Core business logic
│   ├── data_ingestion/           # ETL pipeline
│   ├── entity_resolution/        # Name normalization + ER
│   ├── knowledge_graph/          # Graph construction + analytics
│   ├── ml/                       # Feature engineering + models
│   ├── risk_scoring/             # Net worth + deviation scoring
│   ├── xai/                      # SHAP + audit trails
│   └── reports/                  # PDF generation
├── generators/                   # Synthetic data generator
├── config/settings.py            # Central configuration
├── run_pipeline.py               # Master pipeline runner
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 📊 Dashboard Pages

| Page | Description |
|------|-------------|
| **Executive Dashboard** | KPIs, risk distribution, province heatmap, income vs net worth |
| **Entity Resolution** | Match confidence, method breakdown, data quality metrics |
| **Knowledge Graph** | Interactive PyVis network, ego graphs, community detection |
| **Risk Analytics** | Score distribution, feature importance, PCA anomaly plot |
| **Citizen Profile** | Deep-dive: assets, risk gauge, audit trail, PDF generation |
| **Investigation Center** | Global search, filters, pagination, CSV/Excel/PDF export |

---

## 🔧 Configuration

All settings are in `config/settings.py`:

- Dataset sizes (default: 10,000 citizens)
- Entity resolution thresholds
- ML model hyperparameters
- Risk category ranges and colors
- UI theme colors

---

## 📋 Data Sources (Synthetic)

| Dataset | Records | Key Fields |
|---------|---------|------------|
| Tax Records | ~10K | CNIC, Income, Tax Paid, Filing Status |
| Vehicle Records | ~8K | CNIC, Make/Model, Market Value |
| Property Records | ~6K | CNIC, Type, Value, Location |
| Utility Bills | ~15K | CNIC, Electricity/Gas, Monthly Amount |
| Banking Indicators | ~8K | CNIC, Transactions, Balance |
| Travel Records | ~5K | CNIC, Destination, Class, Airline |
| Business Records | ~3K | CNIC, Company, Role, Revenue |
| Mobile Records | ~12K | CNIC, Phone Number, Operator |

---

## 🛡️ Disclaimer

This system operates entirely on **synthetic/anonymized data**. No real citizen data is used. It is designed as a demonstration of how AI and graph technology can assist in tax compliance analytics.

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.
![alt text](Data_ingestion_hub.png)
![alt text](Main_dashboard.png)
![alt text](tax_heatMap.png)
![alt text](entitryResolution.png)
![alt text](knowledgegraph.png)
![alt text](investigation_center.png)
                                                  
