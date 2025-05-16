"""MCP server for vector embeddings with pgvector"""

import os
import psycopg2
import logging
import json

from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Any
from psycopg2 import sql

load_dotenv()

mcp = FastMCP("pgvector")

DB_PARAMS = {
    "dbname": "pgvector_mcp",
    "user": os.getenv("MEM0_USER"),
    "password": os.getenv("MEM0_PASSWORD"),
    "host": os.getenv("MEM0_HOST"),
    "port": os.getenv("MEM0_PORT"),
}


class SearchResult(BaseModel):
    text_value: str
    id: int
    cosine_dist: float
    metadata: dict[str, Any]


@mcp.tool()
def search(
    query_text: str, limit: int = 3, metadata_filter: dict[str, Any] | None = None
) -> list[SearchResult]:
    """
    Search for text similar to the query in the vector database

    Args:
        query_text (str): The text to find entries similar to
        limit (int): How many entries to return, default 3
        metadata_filter (dict[str, Any] | None): Optional list of metadata parameters to use as a filter. Will only return objects that match all metadata fields

    Returns:
        list[SearchResult]: List of SearchResults, ordered by cosine distance to the query
    """
    query_embedding = _text_to_embedding(query_text)

    conn, cursor = _establish_connection()

    sql_query = sql.SQL("""
        SELECT text_content, id, embedding <=> %s::vector as distance, metadata
        FROM text_embeddings
    """)

    where_clause = sql.SQL("")
    params = [query_embedding.tolist()]

    # if metadata_filter is provided, add WHERE clause to the query
    if metadata_filter:
        where_conditions = []
        for key, value in metadata_filter.items():
            where_conditions.append(
                sql.SQL("metadata->>{} = {}").format(
                    sql.Literal(str(key)), sql.Literal(str(value))
                )
            )

        if where_conditions:
            where_clause = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_conditions)

    order_limit = sql.SQL("""
        ORDER BY distance
        LIMIT %s
    """)
    final_query = sql.SQL(" ").join([sql_query, where_clause, order_limit])

    params.append(limit)

    cursor.execute(final_query, tuple(params))

    results = cursor.fetchall()

    search_results = [
        SearchResult(
            text_value=result[0],
            id=result[1],
            cosine_dist=result[2],
            metadata=result[3],
        )
        for result in results
    ]

    cursor.close()
    conn.close()

    return search_results


def store(input_text: str, metadata: dict[str, Any] = {}) -> bool:
    """
    Store text as vector embedding

    Args:
        input_text (str): The text to be stored in the vector database
        metadata (dict[str, Any]): Optional metadata to be included with the entry

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        embedding = _text_to_embedding(input_text.value)

        conn, cursor = _establish_connection()

        cursor.execute(
            """
            INSERT INTO text_embeddings (text_content, embedding, metadata)
            VALUES (%s, %s, %s);
        """,
            (input_text, embedding.tolist(), json.dumps(metadata)),
        )

        conn.commit()

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return False


def batch_store(texts: list[str], metadata: dict[str, Any] = {}):
    """
    Store multiple strings as vector embeddings simultaneously

    Args:
        texts (list[str]): The text to be stored in the vector database
        metadata (dict[str, Any]): Optional metadata to be included with the entries

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        embeddings = _text_to_embedding(texts)

        conn, cursor = _establish_connection()

        cursor.executemany(
            """
            INSERT INTO text_embeddings (text_content, embedding, metadata)
            VALUES (%s, %s, %s);
        """,
            [
                (text, embedding.tolist(), json.dumps(metadata))
                for text, embedding in zip(texts, embeddings)
            ],
        )

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

        cursor.execute(
            """
            DELETE FROM text_embeddings
            WHERE id = %s
            RETURNING id;
        """,
            (entry_id,),
        )

        deleted_id = cursor.fetchone()

        conn.commit()

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


def batch_delete(entry_ids: list[int]) -> dict:
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
                cursor.execute(
                    """
                    DELETE FROM text_embeddings
                    WHERE id = %s
                    RETURNING id;
                """,
                    (entry_id,),
                )

                if cursor.fetchone():
                    deleted_ids.append(entry_id)
                else:
                    failed_ids.append(entry_id)

            except Exception as e:
                logging.error(f"Error deleting entry {entry_id}: {str(e)}")
                failed_ids.append(entry_id)

        conn.commit()

        cursor.close()
        conn.close()

        return {
            "success": len(deleted_ids),
            "failed": len(failed_ids),
            "deleted_ids": deleted_ids,
            "failed_ids": failed_ids,
        }

    except Exception as e:
        logging.error(f"Error in batch deletion: {str(e)}")
        return {
            "success": 0,
            "failed": len(entry_ids),
            "deleted_ids": [],
            "failed_ids": entry_ids,
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

        conn.commit()

        cursor.close()
        conn.close()

        if count_after == 0:
            logging.info(
                f"Successfully cleared database. Removed {count_before} entries."
            )
            return True
        else:
            logging.warning("Database not completely cleared")
            return False

    except Exception as e:
        logging.error(f"Error clearing database: {str(e)}")
        return False


def _initialize_table():
    conn, cursor = _establish_connection()

    cursor.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS text_embeddings (
            id SERIAL PRIMARY KEY,
            text_content TEXT NOT NULL,
            embedding vector(384) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        ALTER TABLE text_embeddings
        ADD metadata JSONB NOT NULL;
    """)

    conn.commit()

    cursor.close()
    conn.close()


def _establish_connection():
    """Create the db connection"""

    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    return conn, cursor


def _text_to_embedding(input_text: str | list[str]):
    model = SentenceTransformer("all-MiniLM-L6-v2")

    if type(input_text) is str:
        embedding = model.encode([input_text])[0]
    elif type(input_text) is list:
        embedding = model.encode(input_text)
    else:
        raise ValueError(f"Invalid type to be embedded: {type(input_text)}")

    return embedding


if __name__ == "__main__":
    # print(search("What is the difference between simple and custom workflows?", metadata_filter={"filepath": "README.md"}))

    mcp.run(transport="stdio")
