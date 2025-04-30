import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.sqlite import JSON  # Use JSON for flexibility if needed, or Text

Base = declarative_base()

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    strategy_name = Column(String)
    symbol = Column(String)
    signal_type = Column(String)  # e.g., 'arbitrage', 'trend'
    details = Column(Text)  # Store signal-specific data as JSON string or simple text

    def __repr__(self):
        return f"<Signal(id={self.id}, time='{self.timestamp}', strategy='{self.strategy_name}', symbol='{self.symbol}')>"

class Execution(Base):
    __tablename__ = 'executions'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    order_id = Column(String, index=True)  # Exchange's order ID
    client_order_id = Column(String, index=True, nullable=True)  # Optional client-side ID
    symbol = Column(String)
    side = Column(String)  # 'buy' or 'sell'
    type = Column(String)  # 'limit', 'market', etc.
    quantity_requested = Column(Float)
    quantity_executed = Column(Float, default=0.0)
    price = Column(Float, nullable=True)  # Limit price if applicable
    average_fill_price = Column(Float, nullable=True)
    status = Column(String)  # e.g., 'new', 'partially_filled', 'filled', 'canceled', 'rejected', 'error'
    exchange_response = Column(Text, nullable=True)  # Store raw response/error as JSON string or text

    def __repr__(self):
        return f"<Execution(id={self.id}, order_id='{self.order_id}', symbol='{self.symbol}', status='{self.status}')>"

# Add other models if needed (e.g., Position, Balance)