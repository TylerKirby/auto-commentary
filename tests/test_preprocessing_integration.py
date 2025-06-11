"""
Integration tests for the preprocessing agent.

These tests make actual API calls and require valid OpenAI API keys.
Run with: pytest tests/test_preprocessing_integration.py -m integration
"""

import os

import pytest

from src.agents.models import (
    LanguageType,
    PreprocessedText,
    TextRequest,
)
from src.agents.preprocessing import preprocess_text


@pytest.fixture(scope="module")
def check_api_key():
    """
    Check if OpenAI API key is available for integration tests.

    :return: None
    :raises: pytest.skip if API key is not available
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OpenAI API key not found - skipping integration tests")


@pytest.mark.integration
@pytest.mark.asyncio
class TestPreprocessTextIntegration:
    """Integration test cases for the preprocess_text function."""

    async def test_preprocess_ancient_greek_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of Ancient Greek text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Καλημέρα κόσμε")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "Καλημέρα κόσμε"
        assert result.language == LanguageType.ANCIENT_GREEK

    async def test_preprocess_latin_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of Latin text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Salve mundi")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "Salve mundi"
        assert result.language == LanguageType.LATIN

    async def test_preprocess_english_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of English text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Hello world")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "Hello world"
        assert result.language == LanguageType.OTHER

    async def test_preprocess_mixed_classical_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of mixed classical languages with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        # Mix of Greek and Latin - should classify as one or the other
        text_request = TextRequest(text="Καλημέρα et salve")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "Καλημέρα et salve"
        # Should be either ANCIENT_GREEK or LATIN, not OTHER
        assert result.language in [
            LanguageType.ANCIENT_GREEK,
            LanguageType.LATIN,
        ]

    async def test_preprocess_classical_quote_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of famous classical quotes with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange - Famous Latin phrase
        text_request = TextRequest(text="Veni, vidi, vici")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "Veni, vidi, vici"
        assert result.language == LanguageType.LATIN


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text,expected_language_options",
    [
        ("Καλημέρα", [LanguageType.ANCIENT_GREEK]),
        ("Salve", [LanguageType.LATIN]),
        ("Hello", [LanguageType.OTHER]),
        ("Bonjour", [LanguageType.OTHER]),
        ("Hola", [LanguageType.OTHER]),
        # Mixed content - could be classified as either depending on AI
        (
            "Ancient Greek: Καλημέρα",
            [LanguageType.ANCIENT_GREEK, LanguageType.OTHER],
        ),
        ("Latin: Salve", [LanguageType.LATIN, LanguageType.OTHER]),
    ],
)
class TestPreprocessTextIntegrationParametrized:
    """Parametrized integration tests for different text inputs."""

    async def test_preprocess_text_parametrized_real_api(
        self,
        input_text: str,
        expected_language_options: list[LanguageType],
        check_api_key,
    ) -> None:
        """
        Test preprocessing with parametrized inputs using real API.

        :param input_text: The input text to preprocess
        :param expected_language_options: List of acceptable language results
        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text=input_text)

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == input_text
        assert result.language in expected_language_options


@pytest.mark.integration
@pytest.mark.asyncio
class TestPreprocessTextIntegrationEdgeCases:
    """Edge case integration tests."""

    async def test_empty_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of empty text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == ""
        # Empty text should likely be classified as OTHER
        assert result.language == LanguageType.OTHER

    async def test_whitespace_only_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of whitespace-only text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="   \n\t  ")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "   \n\t  "
        # Whitespace should likely be classified as OTHER
        assert result.language == LanguageType.OTHER

    async def test_numbers_and_symbols_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of numbers and symbols with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange
        text_request = TextRequest(text="123 !@# $%^")

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == "123 !@# $%^"
        # Numbers and symbols should be classified as OTHER
        assert result.language == LanguageType.OTHER


@pytest.mark.integration
@pytest.mark.asyncio
class TestPreprocessTextIntegrationPerformance:
    """Performance-related integration tests."""

    async def test_large_text_real_api(self, check_api_key) -> None:
        """
        Test preprocessing of larger text with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        # Arrange - Longer Latin text (excerpt from Lorem Ipsum)
        long_latin = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
            "sed do eiusmod tempor incididunt ut labore et dolore magna "
            "aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
            "ullamco laboris nisi ut aliquip ex ea commodo consequat."
        )
        text_request = TextRequest(text=long_latin)

        # Act
        result = await preprocess_text(text_request)

        # Assert
        assert isinstance(result, PreprocessedText)
        assert result.text == long_latin
        # Lorem Ipsum is pseudo-Latin, could be classified as either
        assert result.language in [LanguageType.LATIN, LanguageType.OTHER]

    async def test_concurrent_requests_real_api(self, check_api_key) -> None:
        """
        Test multiple concurrent preprocessing requests with real API.

        :param check_api_key: Fixture to check API key availability
        :return: None
        """
        import asyncio

        # Arrange
        test_cases = [
            ("Καλημέρα", LanguageType.ANCIENT_GREEK),
            ("Salve", LanguageType.LATIN),
            ("Hello", LanguageType.OTHER),
        ]

        # Create tasks for concurrent execution
        tasks = [preprocess_text(TextRequest(text=text)) for text, _ in test_cases]

        # Act
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        for i, (expected_text, expected_lang) in enumerate(test_cases):
            result = results[i]
            assert isinstance(result, PreprocessedText)
            assert result.text == expected_text
            assert result.language == expected_lang
