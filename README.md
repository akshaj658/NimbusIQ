# 🌌 NimbusIQ — Cloud Cost Intelligence

NimbusIQ is an elegant, production-ready, machine-learning-driven cloud cost forecasting platform. Rebranded from CloudCostAI, NimbusIQ features a robust Flask web application, an ML regression model trained to predict resource costs, a post-model pricing calibration engine, and a premium dark-glassmorphism dashboard with integrated database history and analytics visualization.

---

## 🌟 Key Features

*   **Premium Glassmorphism UI**: Beautiful, responsive layout featuring dark and light theme options, interactive transitions, and a clean, accessible layout.
*   **Tabbed Cost Estimator**: Streamlined wizard-style estimation form that groups inputs by *Service*, *Infrastructure*, *Timeline*, and *Pricing*.
*   **AI Cost Prediction & Calibration**: Combines a trained scikit-learn Linear Regression model with a deterministic post-model pricing engine to factor in regional multipliers and outbound network egress penalties.
*   **Admin Dashboard**: Chart.js visualizations that track historical prediction trends, service shares, regional distributions, and active estimation workloads.
*   **SQLite Prediction History**: Local SQL backend logging all prediction telemetry, complete with a CSV download feature.
*   **Production Hardened**: Configured for instant deployment to Render, complete with WSGI serving via Gunicorn, gevent concurrency, WhiteNoise static caching, and robust Content Security Policies (CSP).

---

## 📁 Repository Structure

```text
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI configuration
├── app/
│   ├── blueprints/
│   │   └── main.py            # Main application blueprint (routes and APIs)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css      # Core layout, glassmorphic styles, and themes
│   │   └── js/
│   │       └── main.js        # DOM interaction, sliders, tab navigation, and Chart.js
│   ├── templates/
│   │   ├── index.html         # Main Estimator landing page
│   │   └── admin.html         # Dashboard & prediction analytics page
│   ├── app.py                 # Flask entrypoint, WSGI setup, security headers, WhiteNoise
│   ├── database.py            # SQLite database initialization & connection helper
│   ├── pricing.py             # Post-model deterministic pricing adjustments & formulas
│   └── services.py            # Service profiles & static resource configuration
├── data/                      # Directory for raw datasets
├── models/
│   ├── feature_names.pkl      # Pickled feature schema
│   ├── linear_regression.pkl  # Trained regression model
│   └── preprocessor.pkl       # Pickled scikit-learn transformer pipeline
├── src/
│   ├── data/
│   │   ├── feature_engineering.py # Custom dataset transformation pipeline
│   │   ├── loader.py             # Data import utilities
│   │   └── preprocessing.py       # Data cleaning and scaling
│   ├── model/
│   │   ├── evaluate.py        # Model validation metrics generator
│   │   ├── predict.py         # Batch and online inference script
│   │   ├── save_model.py      # Serializer for trained model checkpoints
│   │   └── train.py           # Model training loop script
│   └── utils/
│       ├── config.py          # Centralized configuration mapping
│       └── logger.py          # Unified application logger
├── tests/                     # Multi-layer test suite
├── .env.example               # Template for local environment variables
├── pyproject.toml             # Python packaging specification
├── render.yaml                # Render Blueprint infrastructure deployment
├── requirements.txt           # Main dependency declarations
└── runtime.txt                # Target python version
```

---

## ⚙️ Post-Model Calibration Logic

While the core machine learning model in `models/` predicts base infrastructure costs, the application utilizes a business rule engine in [pricing.py](file:///c:/Users/aksha/OneDrive/Desktop/promptwars3/NimbusIQ/app/pricing.py) to dynamically adjust outputs.

1.  **Base Prediction**: The ML model forecasts cost in INR based on core attributes.
2.  **Regional Multipliers**: Applies regional pricing premiums (e.g. US regions as baseline `1.0`, Asia/Europe up to `1.14`, and Middle East up to `1.22`).
3.  **Egress Penalty**: Applies exponential egress penalties for heavy outbound network traffic over 100 GB.
4.  **Workload Density**: Increments cost if CPU or Memory utilization thresholds exceed `60%`.

---

## 🚀 Installation & Local Development

### Prerequisites
*   Python **3.10** or higher
*   Git

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/akshaj658/NimbusIQ.git
    cd NimbusIQ
    ```

2.  **Create and Activate Virtual Environment**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

    # Unix/macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Project Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**
    Copy the sample configuration file and populate your key parameters:
    ```bash
    cp .env.example .env
    ```
    Key parameters in `.env`:
    *   `SECRET_KEY`: Long, random string for Flask session validation (autogenerated if not specified).
    *   `DATABASE_PATH`: Custom path to your SQLite database file.
    *   `SHOW_ADMIN`: Toggle to `true` to enable the admin dashboard page.

5.  **Run Application**
    ```bash
    python app/app.py
    ```
    Access the application locally at: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧪 Running the Test Suite

The project features a comprehensive test suite covering data preprocessing, model evaluation, pricing models, edge cases, and UI input validation. 

To run the tests, install development dependencies and run `pytest`:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## ☁️ Render Deployment

NimbusIQ is configured for seamless deployment on the Render Free Tier.

### Setup Instructions
1.  Connect your GitHub repository to **Render**.
2.  Deploy using the Web Service configuration defined in `render.yaml`:
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn "app.app:app" --worker-class gevent --workers 2 --threads 4 --timeout 120`
    *   **Runtime Environment**: Python 3 (specified in `runtime.txt`)
3.  Add environment variables under **Environment** settings:
    *   `SECRET_KEY`: A secure random password.
    *   `SHOW_ADMIN`: Set to `true` to enable the history dashboard.
