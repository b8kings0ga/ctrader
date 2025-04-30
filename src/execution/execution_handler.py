"""Execution handler for ctrader execution engine."""

from typing import Dict, Any


class ExecutionHandler:
    """Basic execution handler for processing signals.
    
    This class is responsible for receiving signals from strategies
    and processing the requested actions. Initially, it just logs
    the actions it receives.
    
    Attributes:
        config: Configuration manager
        logger: Logger instance
        risk_manager: Risk manager instance
        strategy: Strategy instance
    """
    
    def __init__(self, config, logger, risk_manager=None, strategy=None, order_manager=None):
        """Initialize the execution handler.
        
        Args:
            config: Configuration manager
            logger: Logger instance
            risk_manager: Risk manager instance
            strategy: Strategy instance
            order_manager: Order manager instance
        """
        self.config = config
        self.logger = logger
        self.risk_manager = risk_manager
        self.strategy = strategy
        self.order_manager = order_manager
        
        self.logger.info("Execution handler initialized")
        
    async def handle_signal(self, signal: Dict[str, Any]) -> None:
        """Handle a trading signal.
        
        This method serves as the signal_callback for strategies.
        It logs the received signal and processes any actions.
        
        Args:
            signal: Signal data dictionary
        """
        self.logger.debug(f"Received signal: {signal}")
        
        # Check if the signal is valid
        if signal.get('type') != 'signal' or 'actions' not in signal:
            self.logger.warning(f"Invalid signal format: {signal}")
            return
        
        # Process each action in the signal
        for action in signal['actions']:
            # Perform RiskManager check for this action
            if self.risk_manager and self.strategy:
                is_allowed = self.risk_manager.check_order(action, self.strategy.latest_prices)
                if not is_allowed:
                    self.logger.info(f"Action rejected by RiskManager: {action}")
                    continue
            
            # Place the order via OrderManager
            if self.order_manager:
                await self.order_manager.place_order(action)
            else:
                self.logger.warning(
                    f"OrderManager not available, skipping order: {action.get('side')} "
                    f"{action.get('quantity')} {action.get('symbol')} @ {action.get('type')}"
                )