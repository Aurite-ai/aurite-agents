"""MCP server for vector embeddings with pgvector"""
import os
import psycopg2

from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("pgvector")

DB_PARAMS = {
    'dbname': 'pgvector_mcp',
    'user': os.getenv("MEM0_USER"),
    'password': os.getenv("MEM0_PASSWORD"),
    'host': os.getenv("MEM0_HOST"),
    'port': os.getenv("MEM0_PORT"),
}

def _establish_connection():
    """Create the db connection"""
    
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    return conn, cursor

def _text_to_embedding(input_text: str | list[str]):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    match type(input_text):
        case str:
            embedding = model.encode([input_text])[0]
        case list:
            embedding = model.encode(input_text)
        case _:
            raise ValueError(f"Invalid type to be embedded: {type(input_text)}")
    
    return embedding

def store_text_in_vector_db(input_text: str) -> bool:
    """
    Store text as vector embedding in PostgreSQL with pgvector extension on Google Cloud SQL
    
    Args:
        input_text (str): The text to be stored in the vector database
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        embedding = _text_to_embedding(input_text)
        
        conn, cursor = _establish_connection()
        
        # create table if it doesn't exist
        cursor.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
            
            CREATE TABLE IF NOT EXISTS text_embeddings (
                id SERIAL PRIMARY KEY,
                text_content TEXT NOT NULL,
                embedding vector(384) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            INSERT INTO text_embeddings (text_content, embedding)
            VALUES (%s, %s);
        """, (input_text, embedding.tolist()))
        
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False
    
def batch_store_texts(texts: list[str]):
    embeddings = _text_to_embedding(texts)
        
    conn, cursor = _establish_connection()
    
    cursor.executemany("""
        INSERT INTO text_embeddings (text_content, embedding)
        VALUES (%s, %s);
    """, [(text, embedding.tolist()) for text, embedding in zip(texts, embeddings)])
    
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return True

def search_similar_texts(query_text: str, limit: int = 5):
    query_embedding = _text_to_embedding(query_text)
    
    conn, cursor = _establish_connection()
    
    # search for similar texts using cosine similarity
    cursor.execute("""
        SELECT text_content, embedding <=> %s::vector as distance
        FROM text_embeddings
        ORDER BY distance
        LIMIT %s;
    """, (query_embedding.tolist(), limit))
    
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return results

if __name__ == "__main__":
    mcp.run(transport="stdio")
