"""
Database package for Pixil and RGB matrix metrics.

This package provides database functionality for storing and querying
performance metrics from Pixil script execution and future RGB matrix
hardware monitoring.

Main Classes:
- PixilMetricsDB: Store and retrieve Pixil script performance data
- PixilQueries: Helper class for common Pixil metric queries

Future classes will include matrix hardware metrics when needed.
"""

from .pixil_metrics import PixilMetricsDB
from .queries.pixil_queries import PixilQueries

# Future matrix database imports will go here when implemented
# from .matrix_metrics import MatrixMetricsDB  
# from .queries.matrix_queries import MatrixQueries

__all__ = [
    'PixilMetricsDB',
    'PixilQueries'
]

# Package version for future database migrations
__version__ = '1.0.0'