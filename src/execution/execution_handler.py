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
        self.logger.info(f"ExecutionHandler received signal: {signal}")
        
        # Check if the signal is valid
        if signal.get('type') != 'signal' or 'actions' not in signal:
            self.logger.error(f"Invalid signal format: {signal}")
            return
        
        self.logger.info(f"Signal is valid, processing {len(signal['actions'])} actions")
        
        # Process each action in the signal
        for i, action in enumerate(signal['actions']):
            # Add enhanced logging before risk check
            self.logger.info(f"Processing action {i+1}/{len(signal['actions'])}: {action}")
            
            # Perform RiskManager check for this action
            if self.risk_manager and self.strategy:
                self.logger.info(f"Checking action with RiskManager")
                try:
                    is_allowed = self.risk_manager.check_order(action, self.strategy.latest_prices)
                    if not is_allowed:
                        self.logger.warning(f"Action rejected by RiskManager: {action}")
                        continue
                    self.logger.info(f"Action approved by RiskManager")
                except Exception as e:
                    self.logger.error(f"Error in RiskManager.check_order: {e}")
                    continue
            else:
                self.logger.warning(f"RiskManager or strategy not available, skipping risk check")
            
            # Place the order via OrderManager
            if self.order_manager:
                self.logger.info(f"Placing order via OrderManager: {action}")
                try:
                    order_id = await self.order_manager.place_order(action)
                    self.logger.info(f"Order placed successfully, order_id: {order_id}")
                except Exception as e:
                    self.logger.error(f"Error placing order: {e}")
            else:
                self.logger.error(
                    f"OrderManager not available, skipping order: {action.get('side')} "
                    f"{action.get('quantity')} {action.get('symbol')} @ {action.get('type')}"
                )