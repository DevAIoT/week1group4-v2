"""
Database Module
Handles SQLite database operations for data persistence
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager


class Database:
    """Database manager for curtain control system"""
    
    def __init__(self, db_path: str):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialize_schema()
        
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise e
        finally:
            conn.close()
    
    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        schema = '''
        CREATE TABLE IF NOT EXISTS light_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_value INTEGER NOT NULL,
            calibrated_value REAL,
            sensor_id TEXT DEFAULT 'main'
        );
        
        CREATE TABLE IF NOT EXISTS curtain_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            operation TEXT NOT NULL,
            trigger TEXT,
            light_level_before INTEGER,
            light_level_after INTEGER,
            duration_ms INTEGER,
            success BOOLEAN DEFAULT 1,
            error_message TEXT
        );
        
        CREATE TABLE IF NOT EXISTS system_config (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            data_type TEXT DEFAULT 'string',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            component TEXT NOT NULL,
            severity TEXT DEFAULT 'error'
        );
        
        CREATE INDEX IF NOT EXISTS idx_light_timestamp ON light_readings(timestamp);
        CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON curtain_operations(timestamp);
        '''
        
        try:
            with self.get_connection() as conn:
                conn.executescript(schema)
            self.logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    # Light Readings Operations
    
    def insert_light_reading(self, raw_value: int, calibrated_value: Optional[float] = None, 
                            sensor_id: str = 'main'):
        """Insert a light sensor reading"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    'INSERT INTO light_readings (raw_value, calibrated_value, sensor_id) VALUES (?, ?, ?)',
                    (raw_value, calibrated_value, sensor_id)
                )
            self.logger.debug(f"Inserted light reading: {raw_value}")
        except Exception as e:
            self.logger.error(f"Failed to insert light reading: {e}")
    
    def get_recent_light_readings(self, hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get recent light readings
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of readings to return
            
        Returns:
            List of light reading dictionaries
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT * FROM light_readings 
                       WHERE timestamp > ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?''',
                    (cutoff, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get light readings: {e}")
            return []
    
    def get_light_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get statistics for light readings"""
        cutoff = datetime.now() - timedelta(hours=hours)
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT 
                        COUNT(*) as count,
                        AVG(raw_value) as average,
                        MIN(raw_value) as minimum,
                        MAX(raw_value) as maximum
                       FROM light_readings 
                       WHERE timestamp > ?''',
                    (cutoff,)
                )
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            self.logger.error(f"Failed to get light statistics: {e}")
            return {}
    
    # Curtain Operations Logging
    
    def log_operation(self, operation: str, trigger: str, light_level_before: Optional[int] = None,
                     light_level_after: Optional[int] = None, duration_ms: Optional[int] = None,
                     success: bool = True, error_message: Optional[str] = None):
        """Log a curtain operation"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    '''INSERT INTO curtain_operations 
                       (operation, trigger, light_level_before, light_level_after, 
                        duration_ms, success, error_message) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (operation, trigger, light_level_before, light_level_after, 
                     duration_ms, success, error_message)
                )
            self.logger.info(f"Logged operation: {operation} ({trigger})")
        except Exception as e:
            self.logger.error(f"Failed to log operation: {e}")
    
    def get_recent_operations(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent curtain operations"""
        cutoff = datetime.now() - timedelta(hours=hours)
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT * FROM curtain_operations 
                       WHERE timestamp > ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?''',
                    (cutoff, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get operations: {e}")
            return []
    
    # System Configuration
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get a system setting"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    'SELECT setting_value FROM system_config WHERE setting_key = ?',
                    (key,)
                )
                row = cursor.fetchone()
                return row['setting_value'] if row else None
        except Exception as e:
            self.logger.error(f"Failed to get setting {key}: {e}")
            return None
    
    def set_setting(self, key: str, value: str, data_type: str = 'string'):
        """Set a system setting"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO system_config 
                       (setting_key, setting_value, data_type, updated_at) 
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                    (key, value, data_type)
                )
            self.logger.debug(f"Set setting: {key} = {value}")
        except Exception as e:
            self.logger.error(f"Failed to set setting {key}: {e}")
    
    # Error Logging
    
    def log_error(self, error_type: str, error_message: str, component: str, severity: str = 'error'):
        """Log a system error"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    '''INSERT INTO error_log 
                       (error_type, error_message, component, severity) 
                       VALUES (?, ?, ?, ?)''',
                    (error_type, error_message, component, severity)
                )
            self.logger.debug(f"Logged error: {error_type} in {component}")
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def get_recent_errors(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent system errors"""
        cutoff = datetime.now() - timedelta(hours=hours)
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT * FROM error_log 
                       WHERE timestamp > ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?''',
                    (cutoff, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Failed to get errors: {e}")
            return []
    
    # Maintenance Operations
    
    def cleanup_old_data(self, retention_days: int = 30):
        """Remove data older than retention period"""
        cutoff = datetime.now() - timedelta(days=retention_days)
        try:
            with self.get_connection() as conn:
                # Clean old light readings
                cursor = conn.execute(
                    'DELETE FROM light_readings WHERE timestamp < ?',
                    (cutoff,)
                )
                light_deleted = cursor.rowcount
                
                # Clean old operations
                cursor = conn.execute(
                    'DELETE FROM curtain_operations WHERE timestamp < ?',
                    (cutoff,)
                )
                ops_deleted = cursor.rowcount
                
                # Clean old errors
                cursor = conn.execute(
                    'DELETE FROM error_log WHERE timestamp < ?',
                    (cutoff,)
                )
                errors_deleted = cursor.rowcount
                
            self.logger.info(f"Cleanup: deleted {light_deleted} readings, "
                           f"{ops_deleted} operations, {errors_deleted} errors")
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
    
    def vacuum(self):
        """Optimize database by running VACUUM"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('VACUUM')
            conn.close()
            self.logger.info("Database vacuumed successfully")
        except Exception as e:
            self.logger.error(f"Failed to vacuum database: {e}") 