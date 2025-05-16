import logging

from aurite.servers.storage.vector.pgvector_server import store, delete, search
from aurite.servers.storage.file_server import list_filepaths, read_file

def test_file_upload():
    filepath = list_filepaths()[0]

    file_content = read_file(filepath)

    assert store(file_content)

    results = search(file_content[:10])

    logging.info(results)

    assert len(results) > 0
    assert results[0][0] == file_content

    assert delete(results[0][1])

def test_file_search():
    results = search("overall architecture")

    logging.info(results)