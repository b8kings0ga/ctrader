"""Strategy registry for ctrader."""

from typing import Dict, Type

from src.strategies.base_strategy import BaseStrategy


class StrategyRegistry:
    """Registry for trading strategies.
    
    This class provides a mechanism to register and retrieve strategy classes by name.
    It ensures that all strategies are properly registered and can be instantiated by name.
    """
    
    def __init__(self):
        """Initialize the strategy registry."""
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        
    def register(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """Register a strategy class.
        
        Args:
            name: Name of the strategy
            strategy_class: Strategy class to register
        
        Raises:
            ValueError: If a strategy with the same name is already registered
            TypeError: If the strategy class does not inherit from BaseStrategy
        """
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' is already registered")
            
        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(f"Strategy class must inherit from BaseStrategy")
            
        self._strategies[name] = strategy_class
        
    def get(self, name: str) -> Type[BaseStrategy]:
        """Get a strategy class by name.
        
        Args:
            name: Name of the strategy
            
        Returns:
            Strategy class
            
        Raises:
            KeyError: If the strategy is not registered
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' is not registered")
            
        return self._strategies[name]
        
    def list_strategies(self) -> Dict[str, Type[BaseStrategy]]:
        """List all registered strategies.
        
        Returns:
            Dictionary of strategy names and classes
        """
        return self._strategies.copy()


# Create a singleton instance
strategy_registry = StrategyRegistry()


def register_strategy(name: str, strategy_class: Type[BaseStrategy]) -> None:
    """Register a strategy class in the global registry.
    
    This is a convenience function that delegates to the singleton registry.
    
    Args:
        name: Name of the strategy
        strategy_class: Strategy class to register
    """
    strategy_registry.register(name, strategy_class)
    
    
def get_strategy_class(name: str) -> Type[BaseStrategy]:
    """Get a strategy class by name from the global registry.
    
    This is a convenience function that delegates to the singleton registry.
    
    Args:
        name: Name of the strategy
        
    Returns:
        Strategy class
    """
    return strategy_registry.get(name)
    
    
def list_strategies() -> Dict[str, Type[BaseStrategy]]:
    """List all registered strategies from the global registry.
    
    This is a convenience function that delegates to the singleton registry.
    
    Returns:
        Dictionary of strategy names and classes
    """
    return strategy_registry.list_strategies()