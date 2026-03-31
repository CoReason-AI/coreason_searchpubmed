import unittest.mock

import pytest

from coreason_searchpubmed.client.async_client import AsyncPubMedClient
from coreason_searchpubmed.pubmed import get_pubmed_metadata_pmid


def test_get_pubmed_metadata_pmid_general_exception() -> None:
    # To cover line 46: else: logger.error(f"Unexpected error in batch: {result}")

    # We can mock a completely unexpected exception by mocking the async client method to raise ValueError
    async def mock_efetch(*_args: object, **_kwargs: object) -> bytes:
        raise ValueError("General unexpected error")

    with (
        unittest.mock.patch.object(AsyncPubMedClient, "efetch", new=mock_efetch),
        pytest.raises(ValueError, match="General unexpected error"),
    ):
        get_pubmed_metadata_pmid(["12345"])
