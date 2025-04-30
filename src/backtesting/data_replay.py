"""Data replay engine for backtesting."""

import os
from typing import Generator, Optional
import pandas as pd

from src.utils.config import config_manager
from src.utils.logger import get_logger


class DataReplayEngine:
    """Data replay engine for backtesting.
    
    This class is responsible for loading historical data and replaying it
    for backtesting purposes.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
    """
    
    def __init__(self, config=None, logger=None):
        """Initialize the data replay engine.
        
        Args:
            config: Configuration manager (default: global config_manager)
            logger: Logger instance (default: create new logger)
        """
        self.config = config or config_manager
        self.logger = logger or get_logger("backtesting.data_replay")
        
        # Load backtesting configuration
        self.backtesting_config = self.config.get("backtesting", {})
        
        self.logger.info("Data replay engine initialized")
        
    def load_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Load historical data for backtesting.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            timeframe: Timeframe for the data (e.g., "1m", "1h", "1d")
            
        Returns:
            DataFrame containing historical data
        """
        self.logger.info(
            f"Loading historical data for {symbol} from {start_date} to {end_date} "
            f"with timeframe {timeframe}"
        )
        
        # Get data directory from config or use default
        data_dir = self.config.get("backtesting", {}).get("data_dir", "data")
        
        # Convert symbol to filename-safe format
        safe_symbol = symbol.replace('/', '-')
        
        # Construct file path
        file_name = f"{safe_symbol}-{timeframe}.csv"
        file_path = os.path.join(data_dir, file_name)
        
        self.logger.debug(f"Looking for data file at: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.error(f"Data file not found: {file_path}")
            self.logger.info(f"You can download data using the 'download-data' command:")
            self.logger.info(f"  python -m src.cli.main download-data --symbol {symbol} --start {start_date} --end {end_date} --timeframe {timeframe}")
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        # Load data from CSV
        try:
            df = pd.read_csv(file_path, parse_dates=['timestamp'], index_col='timestamp')
            self.logger.info(f"Loaded {len(df)} data points from {file_path}")
            
            # Filter data based on date range
            df = df[(df.index >= pd.to_datetime(start_date)) &
                    (df.index <= pd.to_datetime(end_date).replace(hour=23, minute=59, second=59))]
            
            self.logger.info(f"Filtered to {len(df)} data points within date range")
            
            return df
        except Exception as e:
            self.logger.error(f"Error loading data from {file_path}: {e}")
            raise
        
    def replay_data(self, historical_data: pd.DataFrame) -> Generator[dict, None, None]:
        """Replay historical data.
        
        This generator yields each data point from the historical data,
        simulating the flow of real-time market data.
        
        Args:
            historical_data: DataFrame containing historical data
            
        Yields:
            Dictionary containing tick data
        """
        self.logger.info("Starting data replay...")
        
        # Placeholder: In a real implementation, this would iterate through the
        # historical data and yield each data point, but for now we just yield nothing
        yield
        
        self.logger.info("Data replay finished")