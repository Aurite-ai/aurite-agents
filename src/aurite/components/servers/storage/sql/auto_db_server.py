"""MCP Server for the mock automotive database"""

import os
import psycopg2

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from pydantic import BaseModel
from psycopg2.extras import execute_values
from psycopg2 import Error as PostgresError
from faker import Faker

class Customer(BaseModel):
    name: str
    phone_number: str
    address: str

load_dotenv()

mcp = FastMCP("auto_db")

DB_PARAMS = {
    "dbname": os.getenv("MOCK_AUTO_DB", default="mock-automotive"),
    "user": os.getenv("MOCK_AUTO_USER"),
    "password": os.getenv("MOCK_AUTO_PASSWORD"),
    "host": os.getenv("MOCK_AUTO_HOST"),
    "port": os.getenv("MOCK_AUTO_PORT"),
}

def insert_customers(customers: list[Customer]) -> dict:
    """
    Insert multiple customers into the database using bulk insert
    
    Args:
        customers: List of Customer objects to insert
    
    Returns:
        dict: Status of the operation with message
    """
    if not customers:
        return {"status": "error", "message": "No customers provided"}
        
    try:
        conn, cursor = _establish_connection()
        
        # Get valid fields from Customer model
        valid_fields = list(Customer.model_fields.keys())
        
        # Convert customers to list of tuples for bulk insert
        values = [
            tuple(getattr(customer, field) for field in valid_fields)
            for customer in customers
        ]
        
        # Create the SQL template with the correct number of placeholders
        placeholders = "(" + ", ".join(["%s"] * len(valid_fields)) + ")"
        
        # Use execute_values for efficient bulk insert
        execute_values(
            cursor,
            f"INSERT INTO customers ({', '.join(valid_fields)}) VALUES %s",
            values,
            template=placeholders,
            page_size=100
        )
        
        conn.commit()
        return {
            "status": "success", 
            "message": f"Successfully inserted {len(customers)} customers"
        }
        
    except PostgresError as e:
        if conn:
            conn.rollback()
        return {"status": "error", "message": f"Database error: {str(e)}"}
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@mcp.tool()
def search_customers(search_params: dict = None, limit: int = 10) -> dict:
    """
    Search for customers based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Customer model fields ("name", "phone_number", or "address")
            Values are strings to search with ILIKE operator
            If None, returns first {limit} customers
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    try:
        conn, cursor = _establish_connection()
        
        # Get valid fields from Customer model
        valid_fields = Customer.model_fields.keys()
        
        # Build the WHERE clause safely
        where_clauses = []
        params = []
        
        # Process search parameters if provided
        if search_params:
            for field, value in search_params.items():
                if field in valid_fields and value:
                    where_clauses.append(f"{field} ILIKE %s")
                    params.append(f"%{value}%")
                
        # Construct the final query
        query = f"SELECT {', '.join(valid_fields)} FROM customers"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add LIMIT clause
        query += f" LIMIT {limit}"
            
        # Execute the parameterized query
        cursor.execute(query, params)
        
        # Fetch results
        results = cursor.fetchall()
        
        # Convert results to list of dictionaries using field names
        customers = [
            Customer.model_validate({field: value for field, value in zip(valid_fields, row)})
            for row in results
        ]
        
        return {
            "status": "success",
            "message": f"Found {len(customers)} matching customers",
            "data": customers
        }
        
    except PostgresError as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}
        
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
def execute_query(query: str) -> list:
    """
    Executes an SQL query on the automotive database
    
    Args:
        query (str): SQL query to execute
    
    Returns:
        list: List of tuples containing the query results
    """
    
    conn, cursor = _establish_connection()
    
    cursor.execute(query)
    
    conn.commit()
    conn.close()
    cursor.close()
    
    return "Success"
            
def add_fake_people(count: int):
    fake = Faker()
    
    customers = []
    
    for i in range(count):
        customers.append(Customer(name=fake.name(), phone_number=fake.phone_number(), address=fake.address()))
    
    result = insert_customers(customers)
    
    return result

def _establish_connection():
    """Create the db connection"""

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    return conn, cursor

if __name__ == "__main__":
    '''
    print(execute_query("DROP TABLE customers;"))
    
    print(execute_query("""
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    phone_number VARCHAR(100) NOT NULL,
    address VARCHAR(200) NOT NULL
);
"""))
    '''
    
    # print(add_fake_people(20))
    
    # print(search_customers({"name": "david"}))

    mcp.run(transport="stdio")
