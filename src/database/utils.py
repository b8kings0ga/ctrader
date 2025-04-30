import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .models import Base, Signal, Execution  # Assuming models.py is in the same directory

DATABASE_DIR = "/app/database"
DATABASE_FILE = "trading_data.db"
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Use connect_args for SQLite specific options if needed, like check_same_thread
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database, creates the directory and tables if they don't exist."""
    try:
        os.makedirs(DATABASE_DIR, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        print(f"Database initialized at {DATABASE_PATH}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

@contextmanager
def get_db_session():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def save_signal(signal_data: dict):
    """Saves a signal record to the database."""
    try:
        with get_db_session() as session:
            # Convert details dict to JSON string if it's a dict
            details_to_save = signal_data.get('details')
            if isinstance(details_to_save, dict):
                details_to_save = json.dumps(details_to_save)

            signal = Signal(
                strategy_name=signal_data.get('strategy_name'),
                symbol=signal_data.get('symbol'),
                signal_type=signal_data.get('signal_type'),
                details=details_to_save
                # timestamp is handled by default
            )
            session.add(signal)
            # print(f"Attempting to save signal: {signal}")  # Debug print
    except Exception as e:
        print(f"Error saving signal: {e}")  # Use logger ideally

def save_execution(execution_data: dict):
    """Saves or updates an execution record to the database."""
    try:
        with get_db_session() as session:
             # Convert response dict to JSON string if it's a dict
            response_to_save = execution_data.get('exchange_response')
            if isinstance(response_to_save, dict):
                response_to_save = json.dumps(response_to_save)

            # Basic implementation: always create new record.
            # TODO: Implement update logic based on order_id if needed.
            execution = Execution(
                order_id=execution_data.get('order_id'),
                client_order_id=execution_data.get('client_order_id'),
                symbol=execution_data.get('symbol'),
                side=execution_data.get('side'),
                type=execution_data.get('type'),
                quantity_requested=execution_data.get('quantity_requested'),
                quantity_executed=execution_data.get('quantity_executed', 0.0),
                price=execution_data.get('price'),
                average_fill_price=execution_data.get('average_fill_price'),
                status=execution_data.get('status'),
                exchange_response=response_to_save
                # timestamp is handled by default
            )
            session.add(execution)
            # print(f"Attempting to save execution: {execution}")  # Debug print
    except Exception as e:
        print(f"Error saving execution: {e}")  # Use logger ideally

# Example usage (for testing, remove later)
# if __name__ == "__main__":
#     print("Initializing DB for standalone test...")
#     init_db()
#     print("Saving test signal...")
#     save_signal({
#         'strategy_name': 'TestStrategy',
#         'symbol': 'BTC/USDT',
#         'signal_type': 'test',
#         'details': {'price': 50000, 'reason': 'testing'}
#     })
#     print("Saving test execution...")
#     save_execution({
#         'order_id': 'test12345',
#         'symbol': 'BTC/USDT',
#         'side': 'buy',
#         'type': 'limit',
#         'quantity_requested': 0.001,
#         'price': 49999.0,
#         'status': 'new'
#     })
#     print("Test data saved.")