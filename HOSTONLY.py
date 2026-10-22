import sys
import mysql.connector as my
from chat_functions import *  # Contains your server_connection and sqlscript definitions
'''
{DEPRACATED}
Define your database name variable (or pull this from your json config!)
DB_NAME = "text_service"
'''
# SCRIPTS--------------------------------------------------------
script_payload = sqlscript(sql_script="text_service_schema.sql", json_cfg=None)

if not script_payload:
    print("Schema installation terminated: SQL script source string empty.")
    sys.exit(1)

# CONNECT-----------------------------------------------------------
conn = server_connection()
if conn is None:
    print("Database connection could not be established.")
    sys.exit(1)

cur = None

# CREATE_DB---------------------------------------------------------
try:
    cur = conn.cursor()
    print("Initializing multi-statement database provisioning sequence...")
    
    # Utilizing MySQL Connector 9.2+ native unified batch execution mode
    cur.execute(script_payload, map_results=True)
    
    # Loop through the modern generator returning (statement, result_set) tuples
    for statement, result_set in cur.fetchsets():
        if result_set and result_set.with_rows:
            result_set.fetchall()
            
    # Commit moved INSIDE the success block
    conn.commit()
    print("SCHEMA CREATED SUCCESSFULLY")
    
except Exception as e:
    print("Error -> ", e, "\n\nRolling back...")
    try:
        conn.rollback()
    except my.Error as rollback_error:
        print("Rollback failed:", rollback_error)
    print("Done")
    sys.exit(1)

finally:
    try:
        if cur:
            cur.close()
    finally:
        conn.close()
