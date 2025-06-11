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
    id: str
    name: str
    phone_number: str
    address: str

class Vehicle(BaseModel):
    id: str
    owner_id: str
    vin: str
    vrm: str
    model: str
    manufacturer: str
    color: str
    fuel: str
    
class CustomerVehicle(BaseModel):
    customer_id: str
    vehicle_id: str

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
        
    return _insert_models(models=customers, table_name="customers")

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
    
    return _search_models(model_class=Customer, table_name="customers", search_params=search_params, limit=limit)
            
def insert_vehicles(vehicles: list[Vehicle]) -> dict:
    """
    Insert multiple vehicles into the database using bulk insert
    
    Args:
        vehicles: List of Vehicle objects to insert
    
    Returns:
        dict: Status of the operation with message
    """
    if not vehicles:
        return {"status": "error", "message": "No vehicles provided"}
        
    return _insert_models(models=vehicles, table_name="vehicles")

@mcp.tool()
def search_vehicles(search_params: dict = None, limit: int = 10) -> dict:
    """
    Search for vehicles based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Vehicle model fields
            Values are strings to search with ILIKE operator
            If None, returns first {limit} vehicles
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Vehicle, table_name="vehicles", search_params=search_params, limit=limit)
            
def _insert_models(models: list[BaseModel], table_name: str) -> dict:
    """
    Generic function to insert multiple Pydantic models into the specified table
    
    Args:
        models: List of Pydantic model objects to insert
        table_name: Name of the target database table
    
    Returns:
        dict: Status of the operation with message
    """
    if not models:
        return {"status": "error", "message": "No models provided"}
        
    try:
        conn, cursor = _establish_connection()
        
        # Get model class from first item
        model_class = type(models[0])
        
        # Get valid fields from model
        valid_fields = list(model_class.model_fields.keys())
        
        # Convert models to list of tuples for bulk insert
        values = [
            tuple(getattr(model, field) for field in valid_fields)
            for model in models
        ]
        
        # Create the SQL template with the correct number of placeholders
        placeholders = "(" + ", ".join(["%s"] * len(valid_fields)) + ")"
        
        # Use execute_values for efficient bulk insert
        execute_values(
            cursor,
            f"INSERT INTO {table_name} ({', '.join(valid_fields)}) VALUES %s",
            values,
            template=placeholders,
            page_size=100
        )
        
        conn.commit()
        return {
            "status": "success", 
            "message": f"Successfully inserted {len(models)} records into {table_name}"
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

def _search_models(model_class: type[BaseModel], table_name: str, search_params: dict = None, limit: int = 10) -> dict:
    """
    Generic function to search for records based on provided parameters
    
    Args:
        model_class: The Pydantic model class to use for validation
        table_name: Name of the target database table
        search_params: Dictionary containing search parameters
            Keys should match model fields
            Values are strings to search with ILIKE operator
            If None, returns first {limit} records
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    try:
        conn, cursor = _establish_connection()
        
        # Get valid fields from model
        valid_fields = model_class.model_fields.keys()
        
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
        query = f"SELECT {', '.join(valid_fields)} FROM {table_name}"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add LIMIT clause
        query += f" LIMIT {limit}"
            
        # Execute the parameterized query
        cursor.execute(query, params)
        
        # Fetch results
        results = cursor.fetchall()
        
        # Convert results to list of model instances
        models = [
            model_class.model_validate({field: value for field, value in zip(valid_fields, row)})
            for row in results
        ]
        
        return {
            "status": "success",
            "message": f"Found {len(models)} matching records in {table_name}",
            "data": models
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
    vehicles = []
    relationships = []
    
    for i in range(count):
        customers.append(
            Customer(
                id=f"customer_{i}",
                name=fake.name(),
                phone_number=fake.phone_number(),
                address=fake.address(),
            )
        )
        
        vehicles.append(
            Vehicle(
                id=f"vehicle_{i}",
                owner_id=f"customer_{i}",
                vin="fake.vehicle.vin()",
                vrm="fake.vehicle.vrm()",
                model="fake.vehicle.model()",
                manufacturer="fake.vehicle.manufacturer()",
                color="fake.vehicle.color()",
                fuel="fake.vehicle.fuel()"
            )
        )
        
        relationships.append(CustomerVehicle(customer_id=f"customer_{i}", vehicle_id=f"vehicle_{i}"))
        
        """
        vehicles.append(
            Vehicle(
                id=f"vehicle_{i}",
                owner_id=f"customer_{i}",
                vin=fake.vehicle.vin(),
                vrm=fake.vehicle.vrm(),
                model=fake.vehicle.model(),
                manufacturer=fake.vehicle.manufacturer(),
                color=fake.vehicle.color(),
                fuel=fake.vehicle.fuel()
            )
        )
        """
    
    result = insert_customers(customers)

    if result.get("status") != "success":
        return result
    
    result = insert_vehicles(vehicles)
    
    _insert_models(relationships, "customer_vehicles")
    
    return result
    

def _establish_connection():
    """Create the db connection"""

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    return conn, cursor

if __name__ == "__main__":
    '''
    print(execute_query("DROP TABLE customers CASCADE;"))
    
    print(execute_query("""
        CREATE TABLE customers (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            phone_number VARCHAR(255) NOT NULL,
            address TEXT NOT NULL
        );
    """))
    
    print(execute_query("""
        CREATE TABLE vehicles (
            id VARCHAR(255) PRIMARY KEY,
            owner_id VARCHAR(255) NOT NULL,
            vin VARCHAR(255) NOT NULL,
            vrm VARCHAR(255) NOT NULL,
            model VARCHAR(255) NOT NULL,
            manufacturer VARCHAR(255) NOT NULL,
            color VARCHAR(255) NOT NULL,
            fuel VARCHAR(255) NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES customers(id)
        );
    """))
    
    print(execute_query("""
        CREATE TABLE customer_vehicles (
            customer_id VARCHAR(255),
            vehicle_id VARCHAR(255),
            PRIMARY KEY (customer_id, vehicle_id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        );
    """))
    '''
    
    # print(add_fake_people(5))
    
    print(search_vehicles({}))

    # mcp.run(transport="stdio")
