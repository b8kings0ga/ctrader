"""Main CLI entry point for ctrader."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from inquirerpy import inquirer
from rich.console import Console
from rich.table import Table

from src.utils.config import config_manager
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
    if strategy is None:
        # List available strategies
        strategies = config_manager.get("strategies", {})
        if not strategies:
            console.print("[bold red]No strategies configured![/bold red]")
            raise typer.Exit(1)
            
        strategy_names = list(strategies.keys())
        strategy = inquirer.select(
            message="Select a strategy to run:",
            choices=strategy_names,
        ).execute()
    
    if symbol is None:
        # List available symbols
        symbols = config_manager.get("data", "symbols", [])
        if not symbols:
            console.print("[bold red]No symbols configured![/bold red]")
            raise typer.Exit(1)
            
        symbol = inquirer.select(
            message="Select a symbol to trade:",
            choices=symbols,
        ).execute()
    
    console.print(f"[bold green]Running strategy {strategy} on {symbol}[/bold green]")
    console.print(f"Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")
    
    # TODO: Implement actual strategy execution
    console.print("[yellow]Strategy execution not yet implemented[/yellow]")


@app.command()
def backtest(
    strategy: str = typer.Option(
        None, "--strategy", "-s", help="Strategy to backtest"
    ),
    symbol: str = typer.Option(
        None, "--symbol", "-S", help="Symbol to backtest"
    ),
    start_date: str = typer.Option(
        None, "--start-date", "-sd", help="Start date (YYYY-MM-DD)"
    ),
    end_date: str = typer.Option(
        None, "--end-date", "-ed", help="End date (YYYY-MM-DD)"
    ),
):
    """Backtest a trading strategy."""
    if strategy is None:
        # List available strategies
        strategies = config_manager.get("strategies", {})
        if not strategies:
            console.print("[bold red]No strategies configured![/bold red]")
            raise typer.Exit(1)
            
        strategy_names = list(strategies.keys())
        strategy = inquirer.select(
            message="Select a strategy to backtest:",
            choices=strategy_names,
        ).execute()
    
    if symbol is None:
        # List available symbols
        symbols = config_manager.get("data", "symbols", [])
        if not symbols:
            console.print("[bold red]No symbols configured![/bold red]")
            raise typer.Exit(1)
            
        symbol = inquirer.select(
            message="Select a symbol to backtest:",
            choices=symbols,
        ).execute()
    
    console.print(f"[bold green]Backtesting strategy {strategy} on {symbol}[/bold green]")
    if start_date:
        console.print(f"Start date: {start_date}")
    if end_date:
        console.print(f"End date: {end_date}")
    
    # TODO: Implement actual backtesting
    console.print("[yellow]Backtesting not yet implemented[/yellow]")


if __name__ == "__main__":
    app()