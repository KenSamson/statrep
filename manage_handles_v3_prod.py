import oracledb
import hashlib
import logging

logger = logging.getLogger(__name__)

class HandlesDatabase:
    def __init__(self):
        """Initialize the Oracle database connection for handles"""
        # Oracle connection details (hardcoded for now - will refactor later)
        self.connection_string = '''(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1521)(host=adb.us-phoenix-1.oraclecloud.com))(connect_data=(service_name=g5cdaf2f9aabdbb_yeiublpmhgwxw343_low.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))'''
        self.user = "MAILMAN"
        self.password = "$Tms320c52password!"
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Connect to the Oracle database"""
        try:
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=self.connection_string
            )
            self.cursor = self.connection.cursor()
            logger.info("Connected to Oracle database (Handles)")
            return True, None
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def hash_pin(self, pin):
        """Hash a PIN using SHA-256"""
        return hashlib.sha256(pin.encode()).hexdigest()
    
    def add_handle(self, handle, pin):
        """
        Add a new handle with PIN
        Returns: (success: bool, error_message: str or None)
        """
        try:
            pin_hash = self.hash_pin(pin)
            self.cursor.execute(
                "INSERT INTO handles (handle, pin_hash) VALUES (:1, :2)",
                (handle, pin_hash)
            )
            self.connection.commit()
            logger.info(f"Added handle: {handle}")
            return True, None
        except Exception as e:
            error_msg = f"Failed to add handle: {str(e)}"
            logger.error(error_msg)
            self.connection.rollback()
            return False, error_msg
    
    def verify_pin(self, handle, pin):
        """Verify if a PIN matches the stored hash for a handle"""
        try:
            pin_hash = self.hash_pin(pin)
            
            self.cursor.execute(
                "SELECT pin_hash FROM handles WHERE handle = :1",
                (handle,)
            )
            result = self.cursor.fetchone()
            
            if result is None:
                return False  # Handle doesn't exist
            
            is_valid = result[0] == pin_hash
            if is_valid:
                logger.info(f"PIN verified for handle: {handle}")
            else:
                logger.warning(f"PIN verification failed for handle: {handle}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"PIN verification error: {str(e)}")
            return False
    
    def pin_needs_change(self, handle, pin):
        """Check if PIN starts with 'z' (temporary PIN requiring change)"""
        return pin.lower().startswith('z')
    
    def change_pin(self, handle, new_pin):
        """
        Change PIN for a handle (admin or forced change, no old PIN verification)
        Returns: (success: bool, error_message: str or None)
        """
        try:
            new_pin_hash = self.hash_pin(new_pin)
            self.cursor.execute(
                "UPDATE handles SET pin_hash = :1 WHERE handle = :2",
                (new_pin_hash, handle)
            )
            self.connection.commit()
            logger.info(f"PIN changed for handle: {handle}")
            return True, None
        except Exception as e:
            error_msg = f"Failed to change PIN: {str(e)}"
            logger.error(error_msg)
            self.connection.rollback()
            return False, error_msg
    
    def update_last_used(self, handle):
        """Update the last_used timestamp for a handle"""
        try:
            self.cursor.execute(
                "UPDATE handles SET last_used = CURRENT_TIMESTAMP WHERE handle = :1",
                (handle,)
            )
            self.connection.commit()
            logger.info(f"Updated last_used for handle: {handle}")
            return True
        except Exception as e:
            logger.error(f"Failed to update last_used: {str(e)}")
            return False
    
    def get_all_handles(self):
        """Get list of all handles (for dropdown)"""
        try:
            self.cursor.execute("SELECT handle FROM handles ORDER BY handle")
            handles = [row[0] for row in self.cursor.fetchall()]
            logger.info(f"Retrieved {len(handles)} handles")
            return True, handles
        except Exception as e:
            logger.error(f"Failed to get handles: {str(e)}")
            return False, []
    
    def close(self):
        """Close the database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Database connection closed (Handles)")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
