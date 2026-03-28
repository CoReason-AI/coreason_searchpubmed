import respx

from coreason_searchpubmed.pubmed import get_pubmed_metadata_pmid


@respx.mock
def test_get_pubmed_metadata_pmid_general_exception() -> None:
    # To cover line 46: else: logger.error(f"Unexpected error in batch: {result}")

    # We can mock a completely unexpected exception by mocking the async client method to raise ValueError
    from coreason_searchpubmed.client.async_client import AsyncPubMedClient

    original_efetch = AsyncPubMedClient.efetch

    async def mock_efetch(*_args: object, **_kwargs: object) -> bytes:
        raise ValueError("General unexpected error")

    AsyncPubMedClient.efetch = mock_efetch  # type: ignore

    try:
        import pytest

        with pytest.raises(ValueError, match="General unexpected error"):
            get_pubmed_metadata_pmid(["12345"])
    finally:
        AsyncPubMedClient.efetch = original_efetch  # type: ignore
