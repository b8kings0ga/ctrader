"""Feature engineering for ML models in ctrader."""

from typing import Dict, Any, List, Optional, Tuple


class FeatureEngineering:
    """Calculates features from market data for ML models."""

    @staticmethod
    def calculate_spread(bid: float, ask: float) -> Optional[float]:
        """Calculates the bid-ask spread.
        
        Args:
            bid: The bid price
            ask: The ask price
            
        Returns:
            The spread (ask - bid) or None if inputs are invalid
        """
        if bid is not None and ask is not None and ask > bid:
            return ask - bid
        return None

    @staticmethod
    def calculate_mid_price(bid: float, ask: float) -> Optional[float]:
        """Calculates the mid-price.
        
        Args:
            bid: The bid price
            ask: The ask price
            
        Returns:
            The mid-price ((bid + ask) / 2) or None if inputs are invalid
        """
        if bid is not None and ask is not None:
            return (bid + ask) / 2.0
        return None

    @staticmethod
    def calculate_book_imbalance(bids: List[Tuple[float, float]], asks: List[Tuple[float, float]], depth: int = 5) -> Optional[float]:
        """Calculates a simple order book imbalance.
        
        The imbalance is calculated as: sum(bid_volumes) / (sum(bid_volumes) + sum(ask_volumes))
        
        Args:
            bids: List of (price, volume) tuples for bids, sorted by price descending
            asks: List of (price, volume) tuples for asks, sorted by price ascending
            depth: Number of price levels to consider
            
        Returns:
            The order book imbalance ratio or None if calculation fails
        """
        try:
            if not bids or not asks:
                return None
                
            # Take only up to 'depth' levels
            bids_to_use = bids[:depth]
            asks_to_use = asks[:depth]
            
            # Calculate sum of volumes
            bid_volume_sum = sum(volume for _, volume in bids_to_use)
            ask_volume_sum = sum(volume for _, volume in asks_to_use)
            
            # Calculate imbalance
            total_volume = bid_volume_sum + ask_volume_sum
            if total_volume > 0:
                return bid_volume_sum / total_volume
            return None
        except Exception:
            return None

    def generate_tick_features(self, market_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Generates features from a single market data tick.
        
        Args:
            market_data: Dictionary containing market data with keys like 'bid', 'ask',
                         potentially 'bids', 'asks'
                         
        Returns:
            Dictionary of calculated features
        """
        features: Dict[str, Optional[float]] = {}
        
        # Extract basic price data
        bid = market_data.get('bid')
        ask = market_data.get('ask')
        
        # Calculate basic features
        features['spread'] = self.calculate_spread(bid, ask)
        features['mid_price'] = self.calculate_mid_price(bid, ask)
        
        # Calculate order book imbalance if data is available
        bids_data = market_data.get('bids')
        asks_data = market_data.get('asks')
        if bids_data and asks_data:
            features['book_imbalance_5'] = self.calculate_book_imbalance(bids_data, asks_data, depth=5)
        else:
            features['book_imbalance_5'] = None
            
        return features


# Example usage (for testing, not part of the class)
if __name__ == '__main__':
    fe = FeatureEngineering()
    sample_data = {
        'symbol': 'BTC/USDT', 
        'bid': 60000.0, 
        'ask': 60000.1, 
        'bids': [(60000.0, 1.0), (59999.9, 2.0)], 
        'asks': [(60000.1, 0.5), (60000.2, 1.5)]
    }
    tick_features = fe.generate_tick_features(sample_data)
    print(f"Sample Tick Features: {tick_features}")