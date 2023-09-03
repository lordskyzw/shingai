from unittest.mock import patch
import pytest

from jobs.tools import create_or_update_semantic_memories


def test_create_or_update_semantic_memories_fail_upsert():
    # Mock the necessary dependencies
    class MockIndex:
        def upsert(self, vectors, namespace):
            raise Exception("Failed to upsert vector embeddings")

    class MockVectorStore:
        def add_texts(self, texts, namespace):
            pass

    mock_index = MockIndex()
    mock_vector_store = MockVectorStore()

    # Replace the actual dependencies with the mocks
    with pytest.raises(RuntimeError) as excinfo:
        with patch("pinecone.Index", return_value=mock_index):
            with patch("Pinecone", return_value=mock_vector_store):
                create_or_update_semantic_memories("recipient")

    # Verify that the expected exception is raised
    assert "An error occurred while adding texts to the vector store." in str(
        excinfo.value
    )
