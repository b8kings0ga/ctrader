"""Tests for WebSocketClient."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the WebSocketClient
from src.data.websocket_client import WebSocketClient


# Fixtures for TestWebSocketClient
@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = Mock()
    
    # Configure the mock to return appropriate values for different calls
    config.get.side_effect = lambda section, key=None, default=None: {
        ('exchange', 'api_key'): 'test_api_key',
        ('exchange', 'api_secret'): 'test_api_secret',
        ('exchange', 'testnet', True): True,
    }.get((section, key, default) if default is not None else (section, key), default)
    
    return config


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def mock_exchange():
    """Create a mock ccxt.pro exchange."""
    exchange = AsyncMock()
    exchange.watch_trades = AsyncMock()
    exchange.close = AsyncMock()
    exchange.set_sandbox_mode = Mock()
    return exchange


@pytest.fixture
def mock_strategy():
    """Create a mock strategy."""
    strategy = Mock()
    strategy.config = {'symbols': ["BTC/USDT", "ETH/USDT"]}
    strategy.on_trade = AsyncMock()
    return strategy

@pytest.fixture
def websocket_client(mock_config, mock_logger, mock_exchange, mock_strategy):
    """Create a WebSocketClient instance with mocked dependencies."""
    with patch('ccxt.pro.binance', return_value=mock_exchange):
        client = WebSocketClient(mock_config, mock_strategy, mock_logger)
        
    return client


# Unit tests for WebSocketClient
@pytest.mark.asyncio
async def test_init(mock_config, mock_logger, mock_strategy):
    """Test initialization of WebSocketClient."""
    with patch('ccxt.pro.binance') as mock_binance:
        mock_exchange = Mock()
        mock_binance.return_value = mock_exchange
        
        client = WebSocketClient(mock_config, mock_strategy, mock_logger)
        
        # Verify ccxt.pro.binance was called with correct parameters
        mock_binance.assert_called_once()
        
        # Verify exchange was initialized with correct parameters
        assert client.exchange == mock_exchange
        
        # Verify sandbox mode was set (testnet)
        mock_exchange.set_sandbox_mode.assert_called_once_with(True)
        
        # Verify strategy was stored
        assert client.strategy == mock_strategy
        
        # Verify symbols were retrieved from strategy config
        assert client.symbols == mock_strategy.config['symbols']
        
        # Verify logger was stored
        assert client.logger == mock_logger
        
        # Verify running flag is False
        assert client.running is False


@pytest.mark.asyncio
async def test_connect(websocket_client, mock_logger):
    """Test connect method."""
    await websocket_client.connect()
    
    # Verify logger.info was called with correct message
    mock_logger.info.assert_called_with(f"Connecting to WebSocket for symbols: {websocket_client.symbols}")


@pytest.mark.asyncio
async def test_handle_messages(websocket_client, mock_logger, mock_exchange, mock_strategy):
    """Test _handle_messages method."""
    # Setup mock trade data
    mock_trades = [
        {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'amount': 1.0,
            'side': 'buy',
            'timestamp': 1619712345000
        },
        {
            'symbol': 'ETH/USDT',
            'price': 3000.0,
            'amount': 10.0,
            'side': 'sell',
            'timestamp': 1619712346000
        }
    ]
    
    # Configure mock_exchange.watch_trades to return mock_trades
    mock_exchange.watch_trades.side_effect = [
        mock_trades,  # First call returns mock_trades
        Exception("Test exception"),  # Second call raises exception to test error handling
        asyncio.CancelledError()  # Third call raises CancelledError to exit the loop
    ]
    
    # Set running to True
    websocket_client.running = True
    
    # Call _handle_messages
    with pytest.raises(asyncio.CancelledError):
        await websocket_client._handle_messages()
    
    # Verify watch_trades was called with correct parameters
    mock_exchange.watch_trades.assert_called_with(websocket_client.symbols)
    
    # Verify strategy.on_trade was called for each trade
    assert mock_strategy.on_trade.call_count == 2
    mock_strategy.on_trade.assert_any_call(mock_trades[0])
    mock_strategy.on_trade.assert_any_call(mock_trades[1])
    
    # Verify logger.error was called for the exception
    mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_start(websocket_client):
    """Test start method."""
    # Patch the connect and _handle_messages methods
    websocket_client.connect = AsyncMock()
    websocket_client._handle_messages = AsyncMock()
    
    # Call start
    await websocket_client.start()
    
    # Verify connect was called
    websocket_client.connect.assert_called_once()
    
    # Verify _handle_messages was called
    websocket_client._handle_messages.assert_called_once()
    
    # Verify running is True
    assert websocket_client.running is True


@pytest.mark.asyncio
async def test_start_exception(websocket_client, mock_logger):
    """Test start method with exception."""
    # Patch the connect method to raise an exception
    websocket_client.connect = AsyncMock(side_effect=Exception("Test exception"))
    
    # Call start
    await websocket_client.start()
    
    # Verify logger.error was called
    mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_stop(websocket_client, mock_exchange, mock_logger):
    """Test stop method."""
    # Set running to True
    websocket_client.running = True
    
    # Call stop
    await websocket_client.stop()
    
    # Verify running is False
    assert websocket_client.running is False
    
    # Verify exchange.close was called
    mock_exchange.close.assert_called_once()
    
    # Verify logger.info was called
    assert mock_logger.info.call_count >= 2


@pytest.mark.asyncio
async def test_stop_not_running(websocket_client, mock_exchange):
    """Test stop method when not running."""
    # Set running to False
    websocket_client.running = False
    
    # Call stop
    await websocket_client.stop()
    
    # Verify exchange.close was not called
    mock_exchange.close.assert_not_called()