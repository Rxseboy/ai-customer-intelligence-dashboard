from setuptools import setup, find_packages

setup(
    name="ecommerce-customer-intelligence-system",
    version="2.0.0",
    packages=find_packages(),
    description=(
        "Production-Grade E-Commerce Customer Intelligence System — "
        "MLOps pipeline with Feature Store, Auto Retraining, RAG AI Assistant, "
        "Drift Monitoring, and CI/CD hardening."
    ),
    author="Rizqi Fajar",
    author_email="rizqyfajar99@gmail.com",
    python_requires=">=3.11",
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pyarrow>=12.0.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.7",
        "python-dotenv>=1.0.0",
        "scikit-learn>=1.3.0",
        "xgboost>=2.0.0",
        "joblib>=1.3.0",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.0.0",
        "streamlit>=1.30.0",
        "plotly>=5.18.0",
        "matplotlib>=3.7.0",
    ],
    extras_require={
        "mlops": [
            "mlflow>=2.0.0",
            "evidently>=0.4.0",
        ],
        "rag": [
            "langchain>=0.1.0",
            "langchain-community>=0.0.20",
            "langchain-google-genai>=1.0.3",
            "google-generativeai>=0.4.0",
        ],
        "bigquery": [
            "google-cloud-bigquery>=3.11.0",
            "db-dtypes>=1.1.1",
        ],
        "ratelimit": [
            "slowapi>=0.1.0",
        ],
        "all": [
            "mlflow>=2.0.0",
            "evidently>=0.4.0",
            "langchain>=0.1.0",
            "langchain-community>=0.0.20",
            "langchain-google-genai>=1.0.3",
            "google-generativeai>=0.4.0",
            "google-cloud-bigquery>=3.11.0",
            "db-dtypes>=1.1.1",
            "slowapi>=0.1.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
