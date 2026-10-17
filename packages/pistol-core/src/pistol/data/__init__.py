"""Data adapters. Each module exports fetch_* functions for one data source.

Fallback chain per data type is in config.SOURCE_PRIORITY. Tools call the
appropriate function directly; if it returns None, they try the next source.
"""
