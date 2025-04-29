# ctrader

A personal crypto high-frequency trading (HFT) system focused on arbitrage opportunities on Binance Spot.

## Project Summary

This project aims to build an automated and stable HFT system tailored for a single developer. It will leverage market data, external indicators, and machine learning (starting with simple models) to identify and execute arbitrage trades on Binance Spot. The system is designed to be modular, maintainable, and built primarily using Python with libraries like `ccxt`, `pandas`, `scikit-learn`, `typer`, and `fastapi`.

## High-Level Milestones (Approx. 6 Months)

1.  **Phase 1: Foundation (1 month)**
    *   Project setup, environment configuration.
    *   Implement data collection (Websockets, REST API) and storage (Redis, Time-Series DB).
    *   Basic Binance exchange connectivity.
    *   Core system architecture definition.
2.  **Phase 2: Strategy Implementation (1.5 months)**
    *   Develop a flexible strategy framework.
    *   Implement the first arbitrage strategy (e.g., triangular).
    *   Add subsequent strategies.
    *   Strategy evaluation and selection mechanism.
3.  **Phase 3: ML Integration (1 month)**
    *   Build feature engineering pipeline.
    *   Implement and train initial simple ML models (e.g., regression, classification).
    *   Integrate ML signals into the strategy framework.
    *   Model evaluation and retraining process.
4.  **Phase 4: Testing & Optimization (1 month)**
    *   Develop a comprehensive backtesting framework.
    *   Optimize strategies and ML models using historical data.
    *   Evaluate system performance and robustness.
    *   Implement basic risk management controls.
5.  **Phase 5: Deployment (1.5 months)**
    *   Set up paper trading environment.
    *   Deploy for live trading with minimal capital.
    *   Implement basic monitoring and alerting.
    *   Establish maintenance procedures.

## Initial TODOs (Phase 1)

*   [ ] Initialize Python project using `uv`.
*   [ ] Set up `pyproject.toml` with initial dependencies (`typer`, `ccxt`, `pandas`, `numpy`, `redis`, `websockets`, `aiohttp`, `pytest`).
*   [ ] Create basic directory structure (already done).
*   [ ] Implement configuration management (`config/`).
*   [ ] Develop basic logging utility (`src/utils/logger.py`).
*   [ ] Implement Binance API connector (`src/exchange/binance_connector.py`) using `ccxt`.
*   [ ] Set up basic data ingestion via Websockets for a single pair (`src/data/websocket_client.py`).
*   [ ] Implement basic Redis caching for incoming data (`src/data/cache.py`).
*   [ ] Create initial CLI structure using `typer` (`src/cli/main.py`).
*   [ ] Write initial unit tests for utilities and connectors (`tests/`).