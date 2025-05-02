"""Main CLI entry point for ctrader."""

import json
import os
import sys
import time
import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock

import ccxt
import pandas as pd
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.table import Table

from src.backtesting.backtester import Backtester
from src.data.websocket_client import WebSocketClient
from src.database.utils import init_db, save_signal, save_execution
from src.exchange.binance_connector import OrderRequest, OrderResponse, binance_connector
from src.execution.execution_handler import ExecutionHandler
from src.execution.order_manager import OrderManager
from src.risk.risk_manager import RiskManager
from src.strategies.arbitrage_strategy import SimpleArbitrageStrategy
from src.utils.config import ConfigManager, config_manager
from src.utils.logger import get_logger, setup_logger

# Create logger
logger = get_logger("cli")

# Create typer app
app = typer.Typer(
    name="ctrader",
    help="A personal crypto high-frequency trading (HFT) system.",
    add_completion=False,
)

# Create console for rich output
console = Console()


class LogLevel(str, Enum):
    """Log levels."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@app.callback()
def callback(
    log_level: Optional[LogLevel] = typer.Option(
        None, "--log-level", "-l", help="Log level"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to configuration file"
    ),
):
    """Common options for all commands."""
    if log_level:
        setup_logger(log_level=log_level.value)
        
    if config_file:
        if not config_file.exists():
            typer.echo(f"Configuration file not found: {config_file}")
            raise typer.Exit(1)
            
        # Reinitialize config manager with the specified file
        global config_manager
        config_manager = config_manager.__class__(
            config_dir=str(config_file.parent), config_file=config_file.name
        )


@app.command()
def info():
    """Display information about the system."""
    table = Table(title="ctrader Information")
    
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Exchange", config_manager.get("exchange", "name", "Not configured"))
    table.add_row("Testnet", str(config_manager.get("exchange", "testnet", True)))
    table.add_row("Symbols", ", ".join(config_manager.get("data", "symbols", [])))
    table.add_row("Timeframes", ", ".join(config_manager.get("data", "timeframes", [])))
    table.add_row("Log Level", config_manager.get("general", "log_level", "INFO"))
    
    console.print(table)


@app.command()
def setup():
    """Interactive setup for ctrader."""
    console.print("[bold green]ctrader Setup[/bold green]")
    console.print("This will guide you through the setup process for ctrader.")
    
    # Exchange setup
    exchange_name = inquirer.text(
        message="Exchange name:",
        default=config_manager.get("exchange", "name", "binance"),
    ).execute()
    
    api_key = inquirer.text(
        message="API Key (leave empty to use environment variable):",
        default="",
    ).execute()
    
    api_secret = inquirer.text(
        message="API Secret (leave empty to use environment variable):",
        default="",
        password=True,
    ).execute()
    
    testnet = inquirer.confirm(
        message="Use testnet?",
        default=config_manager.get("exchange", "testnet", True),
    ).execute()
    
    # Save configuration
    config_manager.set("exchange", "name", exchange_name)
    
    if api_key:
        config_manager.set("exchange", "api_key", api_key)
        
    if api_secret:
        config_manager.set("exchange", "api_secret", api_secret)
        
    config_manager.set("exchange", "testnet", testnet)
    
    # Symbols setup
    default_symbols = config_manager.get("data", "symbols", ["BTC/USDT", "ETH/USDT"])
    symbols_str = inquirer.text(
        message="Trading symbols (comma-separated):",
        default=",".join(default_symbols),
    ).execute()
    
    symbols = [s.strip() for s in symbols_str.split(",")]
    config_manager.set("data", "symbols", symbols)
    
    # Save configuration
    config_manager.save()
    
    console.print("[bold green]Setup complete![/bold green]")
    console.print(f"Configuration saved to {Path('config') / 'default_config.yaml'}")


async def main_async(strategy_name: str, symbol: str, paper_trading: bool):
    """Main async function to run the trading system.
    
    Args:
        strategy_name: Name of the strategy to run
        symbol: Symbol to trade
        paper_trading: Whether to use paper trading
    """
    # Setup logging first
    setup_logger()
    # Get logger after setup
    main_logger = get_logger("main")
    
    # Add early diagnostic logging
    print(f"STARTUP: main_async called with strategy={strategy_name}, symbol={symbol}, paper_trading={paper_trading}")
    main_logger.info(f"STARTUP: main_async called with strategy={strategy_name}, symbol={symbol}, paper_trading={paper_trading}")
    
    # Initialize ConfigManager
    config = config_manager
    
    # Initialize the database
    try:
        init_db()
        main_logger.info("Database initialized successfully.")
    except Exception as e:
        main_logger.error(f"Failed to initialize database: {e}")
        # Re-raise to stop execution if DB init fails
        raise
    
    main_logger.info(f"Starting ctrader with strategy {strategy_name} on {symbol}")
    main_logger.info(f"Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")
    
    try:
        # Initialize connector (use real Binance connector with testnet for paper trading)
        if paper_trading:
            main_logger.info("Using real Binance connector with testnet for paper trading")
            # Ensure testnet is enabled in config
            if not config_manager.get("exchange", "testnet", True):
                main_logger.warning("Testnet was disabled in config but paper trading was requested. Enabling testnet.")
                config_manager.set("exchange", "testnet", True)
                
            # Use the real Binance connector which will use testnet based on config
            connector = binance_connector
            main_logger.info(f"Binance testnet mode: {connector.exchange.options.get('testnet', False)}")
            main_logger.info(f"Using API Key: {config_manager.get('exchange', 'api_key', '')[:5]}... (truncated)")
        else:
            main_logger.info("Using real Binance connector for live trading")
            connector = binance_connector
        
        # Initialize RiskManager
        main_logger.info("Initializing RiskManager...")
        risk_manager = RiskManager(config=config, logger=main_logger)
        print("STARTUP: RiskManager initialized")
        main_logger.info("STARTUP: RiskManager initialized")
        
        # Get strategy configuration
        strategy_config = config.get('strategies', None, {}).get(strategy_name, {})
        
        # Ensure symbols are correctly sourced
        strategy_config['symbols'] = strategy_config.get('symbols', [symbol])
        
        # Initialize Strategy with execution_handler.handle_signal as the callback
        main_logger.info(f"Initializing strategy {strategy_name} with config: {strategy_config}")
        strategy = SimpleArbitrageStrategy(
            strategy_id=strategy_name,
            strategy_config=strategy_config,
            signal_callback=None  # We'll set this after initializing ExecutionHandler
        )
        print(f"STARTUP: Strategy {strategy_name} initialized")
        main_logger.info(f"STARTUP: Strategy {strategy_name} initialized")
        
        # Initialize OrderManager with connector
        main_logger.info("Initializing OrderManager...")
        order_manager = OrderManager(
            config=config,
            logger=main_logger,
            exchange_connector=connector
        )
        
        # Initialize ExecutionHandler with risk_manager, strategy, and order_manager
        main_logger.info("Initializing ExecutionHandler...")
        execution_handler = ExecutionHandler(
            config=config,
            logger=main_logger,
            risk_manager=risk_manager,
            strategy=strategy,
            order_manager=order_manager
        )
        
        # Initialize the strategy with required components
        main_logger.info("Initializing strategy with exchange_connector, data_cache, and execution_handler...")
        strategy.initialize(
            exchange_connector=connector,
            data_cache=None,  # We don't have a data_cache in this context
            execution_handler=execution_handler
        )
        main_logger.info("Strategy initialized successfully")
        
        # Set the signal callback on the strategy
        strategy.signal_callback = execution_handler.handle_signal
        main_logger.info("Set signal_callback on strategy to execution_handler.handle_signal")
        
        # Verify the signal_callback is set correctly
        if strategy.signal_callback is not None:
            main_logger.info(f"Verified signal_callback is set on strategy: {strategy.signal_callback.__name__}")
        else:
            main_logger.error("signal_callback is NOT set on strategy!")
        
        # Initialize WebSocketClient
        main_logger.info("Initializing WebSocketClient...")
        ws_client = WebSocketClient(config=config, strategy=strategy, logger=main_logger)
        print("STARTUP: WebSocketClient initialized")
        main_logger.info("STARTUP: WebSocketClient initialized")
        
        main_logger.info("System initialized, starting WebSocket client...")
        print("STARTUP: About to start WebSocketClient")
        main_logger.info("STARTUP: About to start WebSocketClient")
        
        # Start the WebSocket client and handle shutdown
        try:
            await ws_client.start()
        except KeyboardInterrupt:
            main_logger.info("KeyboardInterrupt received. Shutting down...")
        except Exception as e:
            main_logger.error(f"Error during WebSocket client run: {e}", exc_info=True)
        finally:
            main_logger.info("Attempting to stop WebSocket client...")
            await ws_client.stop()
            main_logger.info("WebSocket client stopped.")
        
    except Exception as e:
        main_logger.error(f"Error in main_async: {e}", exc_info=True)
    finally:
        main_logger.info("Shutting down ctrader")


@app.command()
def run(
    strategy: str = typer.Option(
        None, "--strategy", "-s", help="Strategy to run"
    ),
    symbol: str = typer.Option(
        None, "--symbol", "-S", help="Symbol to trade"
    ),
    paper_trading: bool = typer.Option(
        True, "--paper-trading/--live-trading", help="Use paper trading"
    ),
):
    """Run the trading system."""
    # Add early diagnostic logging
    print("STARTUP: run command called")
    console.print("[bold green]STARTUP: run command called[/bold green]")
    logger.info("STARTUP: run command called")
    # Get default values from config
    default_strategy = config_manager.get("general", "default_strategy", "simple_arbitrage")
    default_symbol = config_manager.get("general", "default_symbol", "BTC/USDT")

    # Use CLI options if provided, otherwise use defaults from config
    strategy_name = strategy if strategy is not None else default_strategy
    symbol_to_run = symbol if symbol is not None else default_symbol

    # Validate strategy exists in config
    strategies = config_manager.get("strategies", None, {})
    if not strategies:
        console.print("[bold red]No strategies configured![/bold red]")
        raise typer.Exit(1)

    if strategy_name not in strategies:
        console.print(f"[bold red]Strategy '{strategy_name}' not found in configuration![/bold red]")
        console.print(f"Available strategies: {', '.join(strategies.keys())}")
        raise typer.Exit(1)

    # Validate symbol exists in config
    # Get symbols from data section with empty list as default
    symbols = config_manager.get("data", "symbols", [])
    if symbols and symbol_to_run not in symbols:
        console.print(f"[bold yellow]Warning: Symbol '{symbol_to_run}' not found in configured symbols![/bold yellow]")

    console.print(f"[bold green]Running strategy {strategy_name} on {symbol_to_run}[/bold green]")
    console.print(f"Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")

    try:
        # Run the async main function
        asyncio.run(main_async(strategy_name, symbol_to_run, paper_trading))
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


@app.command()
def backtest(
    strategy_name: str = typer.Option(
        "simple_arbitrage", "--strategy", "-s", help="Name of the strategy to backtest."
    ),
    symbols: Optional[List[str]] = typer.Option(
        None, "--symbol", help="Symbol(s) to configure the strategy with (e.g., BTC/USDT ETH/BTC ETH/USDT). Uses config if None."
    ),
    start_date: str = typer.Option(
        ..., "--start", help="Start date for backtest (YYYY-MM-DD)."
    ),
    end_date: str = typer.Option(
        ..., "--end", help="End date for backtest (YYYY-MM-DD)."
    ),
    timeframe: str = typer.Option(
        "1m", help="Timeframe for historical data (e.g., '1m', '1h')."
    ),
):
    """
    Runs a backtest for a given strategy and parameters.
    """
    logger.info(f"Starting CLI backtest command...")

    # --- Load Configuration ---
    # Rely on default config_manager
    config = config_manager.config  # Get the full config dictionary
#
    # --- Validate Strategy ---
    strategies = config.get('strategies', {})
    if not strategies:
        logger.error("No strategies configured!")
        console.print("[bold red]No strategies configured![/bold red]")
        raise typer.Exit(code=1)
#
    if strategy_name not in strategies:
        logger.error(f"Unknown strategy name: {strategy_name}")
        console.print(f"[bold red]Strategy '{strategy_name}' not found in configuration![/bold red]")
        console.print(f"Available strategies: {', '.join(strategies.keys())}")
        raise typer.Exit(code=1)
#
    # --- Instantiate Strategy ---
    strategy_config = config.get('strategies', {}).get(strategy_name, {})
#
    # Override symbols from CLI if provided
    if symbols:
        strategy_config['symbols'] = symbols
    else:
        # Ensure symbols are loaded from config if not provided via CLI
        symbols = strategy_config.get('symbols', [])
        if not symbols:
            logger.error("No symbols provided via CLI or found in config for the strategy. Exiting.")
            console.print("[bold red]No symbols provided via CLI or found in config for the strategy![/bold red]")
            raise typer.Exit(code=1)
#
    logger.info(f"Instantiating strategy '{strategy_name}' with config: {strategy_config}")
    strategy_instance = SimpleArbitrageStrategy(strategy_id=strategy_name, strategy_config=strategy_config)
#
    # --- Instantiate Backtester ---
    logger.info("Instantiating Backtester...")
    backtester_instance = Backtester(strategy=strategy_instance, config=config_manager)
#
    # --- Run Backtest ---
    # Note: backtester.run expects *one* symbol for data loading.
    # We'll use the first symbol from the list for this purpose.
    # The strategy itself uses its full configured list internally.
    if not symbols:
        logger.error("Strategy symbols list is empty after configuration. Cannot determine primary symbol for data loading.")
        console.print("[bold red]Strategy symbols list is empty after configuration. Cannot determine primary symbol for data loading.[/bold red]")
        raise typer.Exit(code=1)
#
    primary_symbol = symbols[0]
    logger.info(f"Running backtest using primary symbol '{primary_symbol}' for data loading...")
    console.print(f"[bold green]Backtesting strategy {strategy_name} on {primary_symbol}[/bold green]")
    console.print(f"Start date: {start_date}")
    console.print(f"End date: {end_date}")
    console.print(f"Timeframe: {timeframe}")
    console.print(f"All symbols for strategy: {', '.join(symbols)}")
#
    try:
        results = backtester_instance.run(
            symbol=primary_symbol,  # Use first symbol for data loading
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )
#
        # --- Print Results ---
        logger.info("Backtest finished. Results:")
        console.print("[bold green]Backtest finished. Results:[/bold green]")
        # Pretty print the results dictionary
        console.print(json.dumps(results, indent=2))
#
    except FileNotFoundError as fnf:
        logger.error(f"Data file not found during backtest: {fnf}. Ensure data exists for {primary_symbol} in the expected location.")
        console.print(f"[bold red]Data file not found during backtest: {fnf}[/bold red]")
        console.print(f"Ensure data exists for {primary_symbol} in the expected location.")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception(f"An error occurred during the backtest run: {e}")
        console.print(f"[bold red]An error occurred during the backtest run: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("test-db")
def test_db_save():
    """
    Tests saving a sample signal and execution to the database.
    """
    print("--- Starting Database Save Test ---")
    try:
        print("Initializing database...")
        init_db()  # Ensure DB exists
        print("Database initialized.")
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        raise typer.Exit(code=1)

    # Test saving a signal
    print("Attempting to save a test signal...")
    test_signal = {
        'strategy_name': 'TestStrategy',
        'symbol': 'TEST/USD',
        'signal_type': 'test_buy',
        'details': {'price': 1.0, 'reason': 'CLI test'}
    }
    try:
        save_signal(test_signal)
        print("SUCCESS: Test signal saved.")
    except Exception as e:
        print(f"ERROR: Failed to save test signal: {e}")

    # Test saving an execution
    print("Attempting to save a test execution...")
    test_execution = {
        'order_id': 'test-order-123',
        'client_order_id': 'test-client-456',
        'symbol': 'TEST/USD',
        'side': 'buy',
        'type': 'limit',
        'quantity_requested': 100.0,
        'price': 0.99,
        'status': 'filled',
        'quantity_executed': 100.0,
        'average_fill_price': 0.99,
        'exchange_response': {'msg': 'Filled via CLI test'}
    }
    try:
        save_execution(test_execution)
        print("SUCCESS: Test execution saved.")
    except Exception as e:
        print(f"ERROR: Failed to save test execution: {e}")

    print("--- Database Save Test Complete ---")
    print(f"Check the database file at ./database/trading_data.db (host path)")
    print(f"(Corresponds to /app/database/trading_data.db inside the container)")


@app.command() # Explicitly name the command
def download_data(
    symbols: List[str] = typer.Option(..., "--symbol", help="Symbol(s) to download data for (e.g., BTC/USDT). Can be specified multiple times."),
    start_date: str = typer.Option(..., "--start", help="Start date for download (YYYY-MM-DD)."),
    end_date: str = typer.Option(..., "--end", help="End date for download (YYYY-MM-DD)."),
    timeframe: str = typer.Option("1m", help="Timeframe for historical data (e.g., '1m', '5m', '1h', '1d')."),
    output_dir: str = typer.Option("data", help="Directory to save the downloaded data.")
):
    """
    Downloads historical OHLCV data from Binance and saves it as CSV files.
    """
    logger.info(f"Starting data download command...")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize ccxt exchange
    exchange = ccxt.binance({
        'enableRateLimit': True,  # Important for fetching large amounts of data
        # Add API keys here if needed for higher rate limits, though often not required for public data
        # Fix parameter mismatch: pass None as key and "" as default
        # 'apiKey': config_manager.get("exchange", "api_key", None, ""),
        # 'secret': config_manager.get("exchange", "api_secret", None, ""),
    })
    
    # Use testnet if configured
    # Get testnet setting with True as default
    testnet = config_manager.get("exchange", "testnet", True)
    if testnet:
        exchange.set_sandbox_mode(True)
        logger.info("Using Binance testnet")
    
    # Convert dates to milliseconds timestamps
    try:
        since = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_milli = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        raise typer.Exit(code=1)

    limit = 1000  # Number of candles per request (Binance limit is often 1000)

    for symbol in symbols:
        logger.info(f"Downloading data for {symbol} ({timeframe}) from {start_date} to {end_date}...")
        all_ohlcv = []
        current_since = since

        while current_since < end_milli:
            try:
                logger.debug(f"Fetching {limit} candles for {symbol} starting from {datetime.fromtimestamp(current_since/1000)}...")
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)

                if not ohlcv:
                    logger.warning(f"No more data returned for {symbol} at {datetime.fromtimestamp(current_since/1000)}. Stopping.")
                    break  # Stop if no data is returned

                all_ohlcv.extend(ohlcv)
                last_timestamp = ohlcv[-1][0]

                # Check if we received fewer candles than requested, indicating end of data
                if len(ohlcv) < limit:
                    logger.info(f"Reached end of available data for {symbol} at {datetime.fromtimestamp(last_timestamp/1000)}.")
                    break

                # Move to the next time window
                # Add 1 millisecond to avoid fetching the last candle again
                current_since = last_timestamp + 1

                # Optional: Add a small delay to respect rate limits if not handled by ccxt's enableRateLimit
                # await asyncio.sleep(exchange.rateLimit / 1000)

            except ccxt.NetworkError as e:
                logger.error(f"Network error fetching data for {symbol}: {e}. Retrying...")
                time.sleep(5)  # Wait before retrying
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error fetching data for {symbol}: {e}. Skipping symbol.")
                break  # Stop fetching for this symbol on exchange error
            except Exception as e:
                logger.exception(f"Unexpected error fetching data for {symbol}: {e}. Skipping symbol.")
                break  # Stop fetching for this symbol on unexpected error

        if all_ohlcv:
            # Convert to DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').drop_duplicates().set_index('timestamp')

            # Filter final dataframe to ensure it's within the requested range
            df = df[(df.index >= pd.to_datetime(start_date)) &
                    (df.index <= pd.to_datetime(end_date).replace(hour=23, minute=59, second=59))]

            # Save to CSV
            safe_symbol = symbol.replace('/', '-')  # Make symbol filename-safe
            filename = f"{safe_symbol}-{timeframe}.csv"
            filepath = os.path.join(output_dir, filename)
            try:
                df.to_csv(filepath)
                logger.info(f"Successfully saved {len(df)} data points for {symbol} to {filepath}")
            except Exception as e:
                logger.exception(f"Error saving data for {symbol} to {filepath}: {e}")
        else:
            logger.warning(f"No data was downloaded for {symbol}.")

    logger.info("Data download process finished.")


if __name__ == "__main__":
    app()