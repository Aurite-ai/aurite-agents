"""MCP server for vector embeddings with pgvector"""
import os
import psycopg2
import logging

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
    
    if type(input_text) is str:
        embedding = model.encode([input_text])[0]
    elif type(input_text) is list:
        embedding = model.encode(input_text)
    else:
        raise ValueError(f"Invalid type to be embedded: {type(input_text)}")
    
    return embedding

def store(input_text: str) -> bool:
    """
    Store text as vector embedding
    
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
        logging.error(f"Error occurred: {str(e)}")
        return False

def batch_store(texts: list[str]):
    """
    Store multiple strings as vector embeddings simultaneously
    
    Args:
        texts (list[str]): The text to be stored in the vector database
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
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
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return False
    
def delete(entry_id: int):
    """
    Delete a single entry from the vector database by ID
    
    Args:
        entry_id (int): The ID of the entry to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn, cursor = _establish_connection()
        
        cursor.execute("""
            DELETE FROM text_embeddings
            WHERE id = %s
            RETURNING id;
        """, (entry_id,))
        
        deleted_id = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if deleted_id:
            logging.info(f"Successfully deleted entry with ID: {entry_id}")
            return True
        else:
            logging.warning(f"No entry found with ID: {entry_id}")
            return False
                
    except Exception as e:
        logging.error(f"Error deleting entry: {str(e)}")
        return False

def batch_delete_entries(entry_ids: list[int]) -> dict:
    """
    Delete multiple entries from the vector database by their IDs
    
    Args:
        entry_ids (list[int]): List of entry IDs to delete
        
    Returns:
        dict: Dictionary containing success and failure information
    """
    try:
        conn, cursor = _establish_connection()
        
        deleted_ids = []
        failed_ids = []
        
        for entry_id in entry_ids:
            try:
                cursor.execute("""
                    DELETE FROM text_embeddings
                    WHERE id = %s
                    RETURNING id;
                """, (entry_id,))
                
                if cursor.fetchone():
                    deleted_ids.append(entry_id)
                else:
                    failed_ids.append(entry_id)
                    
            except Exception as e:
                logging.error(f"Error deleting entry {entry_id}: {str(e)}")
                failed_ids.append(entry_id)
                
        cursor.close()
        conn.close()
        
        return {
            'success': len(deleted_ids),
            'failed': len(failed_ids),
            'deleted_ids': deleted_ids,
            'failed_ids': failed_ids
        }
        
    except Exception as e:
        logging.error(f"Error in batch deletion: {str(e)}")
        return {
            'success': 0,
            'failed': len(entry_ids),
            'deleted_ids': [],
            'failed_ids': entry_ids
        }
        
def clear_database(confirmation_code: str = None) -> bool:
    """
    Clear all entries from the vector database
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn, cursor = _establish_connection()
        
        cursor.execute("SELECT COUNT(*) FROM text_embeddings;")
        count_before = cursor.fetchone()[0]
        
        # Perform deletion
        cursor.execute("TRUNCATE TABLE text_embeddings;")
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM text_embeddings;")
        count_after = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if count_after == 0:
            logging.info(f"Successfully cleared database. Removed {count_before} entries.")
            return True
        else:
            logging.warning("Database not completely cleared")
            return False
                
    except Exception as e:
        logging.error(f"Error clearing database: {str(e)}")
        return False

@mcp.tool()
def search(query_text: str, limit: int = 5) -> list[(str, int, float)]:
    """
    Search for text similar to the query in the vector database
    
    Args:
        query_text (str): The text to find entries similar to
        limit (int): How many entries to return, default 5
        
    Returns:
        list[(str, int, float)]: List of entries as tuples of text value (str), id (int), and the cosine distance to the query (float)
    """
    query_embedding = _text_to_embedding(query_text)
    
    conn, cursor = _establish_connection()
    
    # search for similar texts using cosine similarity
    cursor.execute("""
        SELECT text_content, id, embedding <=> %s::vector as distance
        FROM text_embeddings
        ORDER BY distance
        LIMIT %s;
    """, (query_embedding.tolist(), limit))
    
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return results

if __name__ == "__main__":
    # print(batch_store(["The sky is blue today", "The grass is green"]))
    # print(delete(5))
    # print(search("color"))
    
    mcp.run(transport="stdio")
