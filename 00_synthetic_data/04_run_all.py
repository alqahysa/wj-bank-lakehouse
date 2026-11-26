"""Regenerate every CSV in data/ in the right order."""
import importlib

if __name__ == "__main__":
    importlib.import_module("01_master_data").generate_master_data()
    importlib.import_module("02_historical_transactions").generate_historical_transactions()
    importlib.import_module("03_complaints").generate_complaints()