# Copyright (c) 2026 CoReason, Inc.
import asyncio
import concurrent.futures

import pandas as pd

from coreason_searchpubmed.client.async_client import AsyncPubMedClient
from coreason_searchpubmed.client.exceptions import PubMedNetworkError
from coreason_searchpubmed.models.article import Article
from coreason_searchpubmed.parsers.xml_parser import parse_pubmed_xml
from coreason_searchpubmed.utils.export import to_dataframe
from coreason_searchpubmed.utils.logger import logger


def get_pubmed_metadata_pmid(pmids: list[str], api_key: str | None = None) -> pd.DataFrame:
    if not pmids:
        return pd.DataFrame()

    def run_async() -> pd.DataFrame:
        try:
            _ = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(1) as pool:
                return pool.submit(lambda: asyncio.run(_async_get_pubmed_metadata(pmids, api_key))).result()
        except RuntimeError:
            return asyncio.run(_async_get_pubmed_metadata(pmids, api_key))

    return run_async()

async def _async_get_pubmed_metadata(pmids: list[str], api_key: str | None) -> pd.DataFrame:
    client = AsyncPubMedClient(api_key=api_key)
    batch_size = 200
    all_articles: list[Article] = []

    try:
        tasks = []
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            tasks.append(_fetch_and_parse_batch(client, batch))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                if isinstance(result, PubMedNetworkError):
                    logger.error(f"Batch failed: {result}")
                else:
                    logger.error(f"Unexpected error in batch: {result}")
            else:
                if isinstance(result, list):
                    all_articles.extend(result)

    finally:
        await client.close()

    return to_dataframe(all_articles)

async def _fetch_and_parse_batch(client: AsyncPubMedClient, batch: list[str]) -> list[Article]:
    xml_content = await client.efetch(db="pubmed", ids=batch, retmode="xml")
    return parse_pubmed_xml(xml_content)
