import oracledb
import logging

logger = logging.getLogger(__name__)

class LocationDatabase:
    def __init__(self):
        """Initialize the Oracle database connection for locations"""
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
            logger.info("Connected to Oracle database (Locations)")
            return True, None
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_all_states(self):
        """Get list of all states (for dropdown)"""
        try:
            self.cursor.execute("SELECT state_name FROM states ORDER BY state_name")
            states = [row[0] for row in self.cursor.fetchall()]
            logger.info(f"Retrieved {len(states)} states")
            return True, states
        except Exception as e:
            logger.error(f"Failed to get states: {str(e)}")
            return False, []
    
    def get_all_neighborhoods(self):
        """Get list of all neighborhoods (for dropdown)"""
        try:
            self.cursor.execute("SELECT neighborhood_name FROM neighborhoods ORDER BY neighborhood_name")
            neighborhoods = [row[0] for row in self.cursor.fetchall()]
            logger.info(f"Retrieved {len(neighborhoods)} neighborhoods")
            return True, neighborhoods
        except Exception as e:
            logger.error(f"Failed to get neighborhoods: {str(e)}")
            return False, []
    
    def close(self):
        """Close the database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Database connection closed (Locations)")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
