"""MCP Server for the mock automotive database"""

import os
import psycopg2
import uuid
import random 

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import psycopg2.extras
from pydantic import BaseModel, Field
from psycopg2.extras import execute_values
from psycopg2 import Error as PostgresError
from faker import Faker
from datetime import datetime, timedelta, date
from typing import Optional
from uuid import UUID
from decimal import Decimal

class Customer(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    credit_score: int
    income_bracket: str
    financing_status: str

class CustomerContact(BaseModel):
    id: UUID
    customer_id: UUID
    type: str
    label: str
    value: str
    preferred: bool

class Agent(BaseModel):
    id: UUID
    name: str
    email: str
    phone: str
    role: str
    active: bool

class Interaction(BaseModel):
    id: UUID
    customer_id: UUID
    agent_id: UUID
    channel: str
    notes: str
    interaction_at: datetime

class Sale(BaseModel):
    id: UUID
    customer_id: UUID
    agent_id: UUID
    car_id: UUID
    price: Decimal = Field(decimal_places=2)
    status: str
    reason_lost: Optional[str]
    sold_at: datetime

class Car(BaseModel):
    id: UUID
    make: str
    model: str
    year: int
    price: Decimal = Field(decimal_places=2)
    inventory_status: str

class Promotion(BaseModel):
    id: UUID
    car_id: UUID
    title: str
    discount: Decimal = Field(decimal_places=2)
    valid_from: date
    valid_until: date

load_dotenv()

mcp = FastMCP("auto_db")

DB_PARAMS = {
    "dbname": os.getenv("MOCK_AUTO_DB", default="mock-automotive"),
    "user": os.getenv("MOCK_AUTO_USER"),
    "password": os.getenv("MOCK_AUTO_PASSWORD"),
    "host": os.getenv("MOCK_AUTO_HOST"),
    "port": os.getenv("MOCK_AUTO_PORT"),
}

@mcp.tool()
def execute_select(query: str) -> list:
    """
    Executes a SELECT query on the automotive database. The database has the following format:
    -- 1. customers
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP,
    credit_score INT,
    income_bracket VARCHAR(50),
    financing_status VARCHAR(50)
);

-- 2. customer_contacts
CREATE TABLE customer_contacts (
    id UUID PRIMARY KEY,
    customer_id UUID,
    type VARCHAR(50),
    label VARCHAR(50),
    value VARCHAR(255),
    preferred BOOLEAN,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- 3. agents
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    role VARCHAR(50),
    active BOOLEAN
);

-- 4. interactions
CREATE TABLE interactions (
    id UUID PRIMARY KEY,
    customer_id UUID,
    agent_id UUID,
    channel VARCHAR(50),
    notes TEXT,
    interaction_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- 5. cars
CREATE TABLE cars (
    id UUID PRIMARY KEY,
    make VARCHAR(50),
    model VARCHAR(50),
    year INT,
    price DECIMAL(10, 2),
    inventory_status VARCHAR(50)
);

-- 6. sales
CREATE TABLE sales (
    id UUID PRIMARY KEY,
    customer_id UUID,
    agent_id UUID,
    car_id UUID,
    price DECIMAL(10, 2),
    status VARCHAR(50),
    reason_lost TEXT,
    sold_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
);

-- 7. promotions
CREATE TABLE promotions (
    id UUID PRIMARY KEY,
    car_id UUID,
    title VARCHAR(255),
    discount DECIMAL(10, 2),
    valid_from DATE,
    valid_until DATE,
    FOREIGN KEY (car_id) REFERENCES cars(id)
);
    
    Args:
        query (str): SQL SELECT query to execute
    
    Returns:
        list: List of tuples containing the query results
        
    Raises:
        ValueError: If query is not a SELECT statement
    """
    # Normalize query by removing extra whitespace and converting to uppercase
    normalized_query = query.strip().upper()
    
    # Verify query starts with SELECT
    if not normalized_query.startswith('SELECT'):
        raise ValueError("Query must be a SELECT statement")
        
    return execute_query(query)

def search_customers(search_params: dict = None, limit: int = 10) -> dict[str, str | Customer]:
    """
    Search for customers based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Customer model fields (id, name, created_at, credit_score, income_bracket, financing_status)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} customers
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    
    return _search_models(model_class=Customer, table_name="customers", search_params=search_params, limit=limit)
            
def search_customer_contacts(search_params: dict = None, limit: int = 10) -> dict[str, str | CustomerContact]:
    """
    Search for customer contacts based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match CustomerContact model fields (id, customer_id, type, label, value, preferred)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} contacts
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=CustomerContact, table_name="customer_contacts", search_params=search_params, limit=limit)

def search_agents(search_params: dict = None, limit: int = 10) -> dict[str, str | Agent]:
    """
    Search for agents based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Agent model fields (id, name, email, phone, role, active)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} agents
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Agent, table_name="agents", search_params=search_params, limit=limit)

def search_interactions(search_params: dict = None, limit: int = 10) -> dict[str, str | Interaction]:
    """
    Search for interactions based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Interaction model fields (id, customer_id, agent_id, channel, notes, interaction_at)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} interactions
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Interaction, table_name="interactions", search_params=search_params, limit=limit)

def search_sales(search_params: dict = None, limit: int = 10) -> dict[str, str | Sale]:
    """
    Search for sales based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Sale model fields (id, customer_id, agent_id, car_id, price, status, reason_lost, sold_at)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} sales
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Sale, table_name="sales", search_params=search_params, limit=limit)

def search_cars(search_params: dict = None, limit: int = 10) -> dict[str, str | Car]:
    """
    Search for cars based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Car model fields (id, make, model, year, price, inventory_status)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} cars
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Car, table_name="cars", search_params=search_params, limit=limit)

def search_promotions(search_params: dict = None, limit: int = 10) -> dict[str, str | Promotion]:
    """
    Search for promotions based on provided parameters
    
    Args:
        search_params: Dictionary containing search parameters
            Keys should match Promotion model fields (id, car_id, title, discount, valid_from, valid_until)
            Values are strings to search with ILIKE operator
            If None, returns first {limit} promotions
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        dict: Status of the operation with message and results
    """
    return _search_models(model_class=Promotion, table_name="promotions", search_params=search_params, limit=limit)
            
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

def execute_query(query: str) -> list | str:
    """
    Executes an SQL query on the automotive database
    
    Args:
        query (str): SQL query to execute
    
    Returns:
        list: List of tuples containing the query results for SELECT queries
        str: Success message for other query types
    """
    
    conn, cursor = _establish_connection()
    
    try:
        cursor.execute(query)
        
        # Try to fetch results - will work for SELECT queries
        try:
            results = cursor.fetchall()
            return results
        except psycopg2.ProgrammingError:
            # No results to fetch (e.g., INSERT, UPDATE, DELETE)
            conn.commit()
            return "Success"
            
    finally:
        cursor.close()
        conn.close()

def rebuild_tables():
    print(execute_query("""DROP TABLE IF EXISTS promotions;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS cars;
DROP TABLE IF EXISTS interactions;
DROP TABLE IF EXISTS customer_contacts;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS customers;"""))
    
    print(execute_query("""-- 1. customers
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP,
    credit_score INT,
    income_bracket VARCHAR(50),
    financing_status VARCHAR(50)
);

-- 2. customer_contacts
CREATE TABLE customer_contacts (
    id UUID PRIMARY KEY,
    customer_id UUID,
    type VARCHAR(50),
    label VARCHAR(50),
    value VARCHAR(255),
    preferred BOOLEAN,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- 3. agents
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    role VARCHAR(50),
    active BOOLEAN
);

-- 4. interactions
CREATE TABLE interactions (
    id UUID PRIMARY KEY,
    customer_id UUID,
    agent_id UUID,
    channel VARCHAR(50),
    notes TEXT,
    interaction_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- 5. cars
CREATE TABLE cars (
    id UUID PRIMARY KEY,
    make VARCHAR(50),
    model VARCHAR(50),
    year INT,
    price DECIMAL(10, 2),
    inventory_status VARCHAR(50)
);

-- 6. sales
CREATE TABLE sales (
    id UUID PRIMARY KEY,
    customer_id UUID,
    agent_id UUID,
    car_id UUID,
    price DECIMAL(10, 2),
    status VARCHAR(50),
    reason_lost TEXT,
    sold_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
);

-- 7. promotions
CREATE TABLE promotions (
    id UUID PRIMARY KEY,
    car_id UUID,
    title VARCHAR(255),
    discount DECIMAL(10, 2),
    valid_from DATE,
    valid_until DATE,
    FOREIGN KEY (car_id) REFERENCES cars(id)
);"""))

def create_fake_data(multiplier: int = 1, customer_count: int = 10, agent_count: int = 5, interaction_count: int = 10, owned_car_count: int = 10, available_car_count: int = 10, promotion_count: int = 5):
    """Creates and inserts fake data into all database tables for testing purposes.

    Generates realistic test data for an automotive dealership database including customers,
    customer contacts, agents, interactions, cars (both sold and available), sales records,
    and promotional offers. All generated data is inserted into the corresponding database tables.

    Args:
        multiplier (int, optional): Number to multiply all count parameters by. Useful to quickly adjust order of magnitude of data generated. Defaults to 1. 
        customer_count (int, optional): Base number of customers to create. Defaults to 10.
        agent_count (int, optional): Base number of agents to create. Defaults to 5.
        interaction_count (int, optional): Base number of customer-agent interactions to create. Defaults to 10.
        owned_car_count (int, optional): Base number of sold cars to create. Defaults to 10.
        available_car_count (int, optional): Base number of available cars to create. Defaults to 10.
        promotion_count (int, optional): Base number of promotions to create. Defaults to 5.

    The actual number of records created will be the base counts multiplied by the multiplier parameter.
    Each customer will have 1-3 contact methods generated.
    Each sold car will have an associated sales record.
    Promotions are only created for available cars.

    Note:
        Requires the Faker library for generating realistic fake data.
        Uses random selection from predefined lists for car makes/models and status values.
        Dates are generated within reasonable ranges (e.g., last 10 years for most records).
    """
    
    fake = Faker()

    customers = []
    customer_contacts = []
    agents = []
    interactions = []
    sold_cars = []
    available_cars = []
    sales = []
    promotions = []
    
    customer_count *= multiplier
    agent_count *= multiplier
    interaction_count *= multiplier
    owned_car_count *= multiplier
    available_car_count *= multiplier
    promotion_count *= multiplier
    
    # customers
    for i in range(customer_count):
        customer = Customer(
            id = uuid.uuid4(),
            name = fake.name(),
            created_at = fake.date_time_between(start_date=datetime.now() - timedelta(weeks=520), end_date=datetime.now()),
            credit_score = random.randrange(500,850),
            income_bracket = random.choice(["<50k", "50k-100k", ">100k"]),
            financing_status = random.choice(["pre-approved", "pending", "declined"]),
        )
        
        customers.append(customer)
        
        preferred = True
        
        #customer_contacts
        for i in range(random.randrange(1,4)):
            contact_type = random.choice(["email", "phone", "whatsapp", "messenger"])
            match contact_type:
                case "email":
                    value = fake.email()
                case "phone":
                    value = fake.phone_number()
                case "whatsapp":
                    value = fake.phone_number()
                case "messenger":
                    value = "@" + fake.user_name()
            
            customer_contact = CustomerContact(
                id = uuid.uuid4(),
                customer_id = customer.id, 
                type = contact_type,
                label = random.choice(["work", "personal"]),
                value = value,
                preferred = preferred,
            )
            
            customer_contacts.append(customer_contact)
            
            preferred = False
    
    # agents
    for i in range(agent_count):
        agent = Agent(
            id = uuid.uuid4(),
            name = fake.name(),
            email = fake.email(),
            phone = fake.phone_number(),
            role = random.choice(["sales", "manager"]),
            active = (random.random() > 0.2),
        )
        
        agents.append(agent)
        
    
    # interactions
    for i in range(interaction_count):        
        interaction = Interaction(
            id = uuid.uuid4(),
            customer_id = random.choice(customers).id, #random from list of customers
            agent_id = random.choice(agents).id, #random from list of agents
            channel = random.choice(["phone", "email"]),
            notes = fake.paragraph(nb_sentences=2),
            interaction_at = fake.date_time_between(start_date=datetime.now() - timedelta(weeks=520), end_date=datetime.now()), # random last 10 years
        )
        
        interactions.append(interaction)
        
    # cars
    make_list=["Honda", "Tesla", "Toyota", "Ford", "Chevrolet", "BMW", "Mercedes-Benz", "Audi", "Volkswagen", "Nissan", "Hyundai", "Kia", "Mazda", "Subaru", "Lexus", "Volvo", "Porsche", "Jaguar", "Land Rover", "Jeep"]
    model_list=["Civic", "Model 3", "Camry", "F-150", "Corvette", "3 Series", "E-Class", "A4", "Golf", "Altima", "Elantra", "Sorento", "CX-5", "Outback", "RX", "XC90", "911", "F-Type", "Range Rover", "Wrangler"]
    
    # sales
    for i in range(owned_car_count):
        car = Car(
            id = uuid.uuid4(),
            make = random.choice(make_list),
            model = random.choice(model_list),
            year = random.randrange(2010, 2025),
            price = random.randrange(20000,80000), 
            inventory_status = "sold",
        )
        
        sold_cars.append(car)
        
        sale = Sale(
            id = uuid.uuid4(),
            customer_id = random.choice(customers).id,
            agent_id = random.choice(agents).id,
            car_id = car.id, 
            price = car.price,
            status = random.choice(["closed", "won", "lost"]),
            reason_lost = fake.paragraph(nb_sentences=1),
            sold_at = fake.date_time_between(start_date=datetime.now() - timedelta(weeks=520), end_date=datetime.now()), # random last 10 years
        )
        
        sales.append(sale)
        
        
    for i in range(available_car_count):
        car = Car(
            id = uuid.uuid4(),
            make = random.choice(make_list),
            model = random.choice(model_list),
            year = random.randrange(2010, 2025),
            price = random.randrange(20000,80000), 
            inventory_status = random.choice(["in_stock", "reserved"]),
        )    
    
        available_cars.append(car)
        
    # promotions
    for i in range(promotion_count):
        random_car = random.choice(available_cars)
        
        valid_from = fake.date_between(start_date=datetime.now() - timedelta(days=30), end_date=datetime.now() + timedelta(days=30)) # random +/- a month
        
        promotion = Promotion(
            id = uuid.uuid4(),
            car_id = random_car.id,
            title = fake.paragraph(nb_sentences=1),
            discount = random_car.price * random.randrange(10,40) / 100,
            valid_from = valid_from, 
            valid_until = fake.date_between(start_date=valid_from, end_date=datetime.now() + timedelta(days=60)),
        )
        
        promotions.append(promotion)
            
    cars = sold_cars + available_cars
        
    tables = {
        "customers": customers,
        "customer_contacts": customer_contacts,
        "agents": agents,
        "interactions": interactions,
        "cars": cars,
        "sales": sales,
        "promotions": promotions,
    }
    
    psycopg2.extras.register_uuid()
    for table_name in tables:
        result = _insert_models(tables[table_name], table_name)
        print(result)
       
    '''
    def print_list(arr: list):
        for item in arr:
            print(item)
    
    print("===CUSTOMERS===")
    print_list(customers)
    
    print("===CUSTOMER CONTACTS===")
    print_list(customer_contacts)
    
    print("===AGENTS===")
    print_list(agents)
    
    print("===INTERACTIONS===")
    print_list(interactions)
    
    print("===SOLD CARS===")
    print_list(sold_cars)
    
    print("===AVAILABLE CARS===")
    print_list(available_cars)
    
    print("===SALES===")
    print_list(sales)
    
    print("===PROMOTIONS===")
    print_list(promotions)    
    ''' 


def _establish_connection():
    """Create the db connection"""

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    return conn, cursor

if __name__ == "__main__":
    # rebuild_tables()
    
    # create_fake_data(multiplier=100)
    
    mcp.run(transport="stdio")
