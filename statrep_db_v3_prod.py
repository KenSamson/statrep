import oracledb
import logging
from datetime import datetime

# Configure logging for server-side debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StatrepDatabase:
    def __init__(self):
        """Initialize the Oracle database connection"""
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
            logger.info("Connected to Oracle database (STATREP)")
            return True, None
        except Exception as e:
            error_msg = f"Database connection failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def insert_statrep(self, amcon_handle, datetime_group, state, neighborhood, location, conditions,
                       position=None, commercial_power=None, water=None,
                       sanitation=None, grid_comms=None, transportation=None,
                       comments=None):
        """
        Insert a new STATREP record
        Returns: (success: bool, result: record_id or error_message)
        """
        
        # Use RETURNING clause to get the generated ID
        insert_sql_with_return = """
        INSERT INTO statrep (
            amcon_handle, datetime_group, state, neighborhood, location, conditions,
            position, commercial_power, water, sanitation,
            grid_comms, transportation, comments
        ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13)
        RETURNING id INTO :14
        """
        
        try:
            # Create output variable for the returned ID
            id_var = self.cursor.var(int)
            
            self.cursor.execute(insert_sql_with_return, (
                amcon_handle, datetime_group, state, neighborhood, location, conditions,
                position, commercial_power, water, sanitation,
                grid_comms, transportation, comments,
                id_var
            ))
            self.connection.commit()
            
            record_id = id_var.getvalue()[0]
            logger.info(f"STATREP inserted - ID: {record_id}, Handle: {amcon_handle}")
            return True, record_id
            
        except Exception as e:
            error_msg = f"Insert failed: {str(e)}"
            logger.error(error_msg)
            self.connection.rollback()
            return False, error_msg
    
    def get_all_statreps(self, limit=None):
        """Retrieve all STATREP records, optionally limited"""
        try:
            if limit:
                query = f"SELECT * FROM statrep ORDER BY datetime_group DESC FETCH FIRST {limit} ROWS ONLY"
            else:
                query = "SELECT * FROM statrep ORDER BY datetime_group DESC"
            
            self.cursor.execute(query)
            return True, self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return False, str(e)
    
    def get_statrep_by_handle(self, amcon_handle):
        """Retrieve all STATREPs for a specific handle"""
        try:
            self.cursor.execute(
                "SELECT * FROM statrep WHERE amcon_handle = :1 ORDER BY datetime_group DESC",
                (amcon_handle,)
            )
            return True, self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return False, str(e)
    
    def get_last_statrep_for_handle(self, amcon_handle):
        """Get the most recent STATREP for a handle"""
        try:
            self.cursor.execute(
                """SELECT * FROM statrep 
                   WHERE amcon_handle = :1 
                   ORDER BY datetime_group DESC 
                   FETCH FIRST 1 ROW ONLY""",
                (amcon_handle,)
            )
            result = self.cursor.fetchone()
            return True, result
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return False, str(e)
    
    def close(self):
        """Close the database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Database connection closed (STATREP)")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
