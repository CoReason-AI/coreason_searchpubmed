import logging

import coreason_searchpubmed.utils.logger as logger_module


def test_logger_setup() -> None:
    assert isinstance(logger_module.logger, logging.Logger)
    assert logger_module.logger.name == "coreason_searchpubmed"
    # Ensure NullHandler is present
    has_null_handler = any(isinstance(h, logging.NullHandler) for h in logger_module.logger.handlers)
    assert has_null_handler
