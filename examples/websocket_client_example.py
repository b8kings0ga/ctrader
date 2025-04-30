#!/usr/bin/env python3
"""Example script for using the WebSocketClient."""

import asyncio
import logging
import sys
from unittest.mock import MagicMock

from src.data.websocket_client import WebSocketClient
from src.strategies.arbitrage_strategy import SimpleArbitrageStrategy
from src.utils.config import config_manager
from src.utils.logger import get_logger
from src.execution.execution_handler import ExecutionHandler

# Configure logging
logger = get_logger("websocket_example")
logger.setLevel(logging.INFO)

# Add console handler to see logs in terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

async def main():
    """Run the WebSocket client example."""
    # Create a strategy instance with the symbols we want to monitor
    strategy_config = {
        'symbols': ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        'min_profit_threshold': 0.001,
        'threshold': 0.001
    }
    strategy = SimpleArbitrageStrategy("arbitrage_example", strategy_config)
    
    # Create mock objects for strategy initialization
    # In a real application, these would be actual instances
    mock_exchange = MagicMock()
    mock_data_cache = MagicMock()
    
    # Create execution handler
    execution_handler = ExecutionHandler(config_manager, logger)
    
    # Initialize the strategy with execution handler
    strategy.initialize(
        exchange_connector=mock_exchange,
        data_cache=mock_data_cache,
        execution_handler=execution_handler
    )
    
    # Set the signal callback to the execution handler's handle_signal method
    strategy.signal_callback = execution_handler.handle_signal
    
    # Create WebSocket client with the strategy
    client = WebSocketClient(config_manager, strategy, logger)
    
    try:
        # Start the client (this will run indefinitely)
        logger.info("Starting WebSocket client...")
        await client.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping client...")
    except Exception as e:
        logger.error(f"Error in WebSocket client: {e}")
    finally:
        # Ensure client is stopped properly
        logger.info("Stopping WebSocket client...")
        await client.stop()
        logger.info("WebSocket client stopped")

if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user")