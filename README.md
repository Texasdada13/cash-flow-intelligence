# Cash Flow Intelligence

AI-powered cash flow analysis and forecasting for small and medium businesses.
Your Virtual CFO, powered by Claude AI.

## Features

- **Cash Flow Forecasting**: Predict cash position with AI-powered time series analysis
- **Financial Health Scoring**: Multi-dimensional scoring and risk classification
- **AI CFO Consultant**: Conversational AI for financial advice and insights
- **Benchmark Comparison**: Compare metrics against industry standards
- **Trend Analysis**: Identify patterns, seasonality, and anomalies

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **AI**: Anthropic Claude API
- **Forecasting**: Prophet / Statistical methods
- **Frontend**: Bootstrap 5, Chart.js

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/Texasdada13/cash-flow-intelligence.git
cd cash-flow-intelligence
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export ANTHROPIC_API_KEY=your_key_here
export SECRET_KEY=your_secret_key
```

5. Run the application:
```bash
python web/app.py
```

6. Open http://localhost:5000 in your browser

## Deployment

This project is configured for Render deployment. See `render.yaml` for the blueprint.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Project Structure

```
cash-flow-intelligence/
├── config/
│   └── settings.py          # Configuration settings
├── src/
│   ├── ai_core/              # Claude AI integration
│   │   ├── chat_engine.py    # Conversational AI
│   │   └── claude_client.py  # API wrapper
│   ├── database/
│   │   └── models.py         # SQLAlchemy models
│   ├── forecasting/          # Time series forecasting
│   │   ├── cash_flow_forecaster.py
│   │   └── trend_analyzer.py
│   └── patterns/             # Reusable patterns
│       ├── benchmark_engine.py
│       ├── risk_classification.py
│       └── weighted_scoring.py
├── web/
│   ├── app.py                # Flask application
│   └── templates/            # HTML templates
├── requirements.txt
├── render.yaml               # Render deployment
└── README.md
```

## Part of Patriot Tech Product Suite

Cash Flow Intelligence is the first product in the **Fractional C-Suite** series:

- **Cash Flow Intelligence** (CFO) - *This project*
- App Rationalization Pro (CTO)
- AI Practice Platform (CSO)
- *More coming soon...*

## License

Copyright 2024 Patriot Tech Systems Consulting LLC
