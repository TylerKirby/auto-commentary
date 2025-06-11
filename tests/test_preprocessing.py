"""
Unit tests for the preprocessing agent.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.models import (
    LanguageType,
    PreprocessedText,
    PreprocessingOutput,
    TextRequest,
)
from src.agents.preprocessing import preprocess_text


class TestPreprocessText:
    """Test cases for the preprocess_text function."""

    @pytest.mark.asyncio
    async def test_preprocess_ancient_greek_text(self) -> None:
        """
        Test preprocessing of Ancient Greek text.

        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Καλημέρα")
        expected_output = PreprocessingOutput(language=LanguageType.ANCIENT_GREEK)
        mock_result = Mock()
        mock_result.output = expected_output

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_run:
            result = await preprocess_text(text_request)

            # Verify the agent was called with correct text
            mock_run.assert_called_once_with("Καλημέρα")

            # Verify the result
            assert isinstance(result, PreprocessedText)
            assert result.text == "Καλημέρα"
            assert result.language == LanguageType.ANCIENT_GREEK

    @pytest.mark.asyncio
    async def test_preprocess_latin_text(self) -> None:
        """
        Test preprocessing of Latin text.

        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Salve")
        expected_output = PreprocessingOutput(language=LanguageType.LATIN)
        mock_result = Mock()
        mock_result.output = expected_output

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_run:
            result = await preprocess_text(text_request)

            # Verify the agent was called with correct text
            mock_run.assert_called_once_with("Salve")

            # Verify the result
            assert isinstance(result, PreprocessedText)
            assert result.text == "Salve"
            assert result.language == LanguageType.LATIN

    @pytest.mark.asyncio
    async def test_preprocess_other_language_text(self) -> None:
        """
        Test preprocessing of text in other languages.

        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Hello world")
        expected_output = PreprocessingOutput(language=LanguageType.OTHER)
        mock_result = Mock()
        mock_result.output = expected_output

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_run:
            result = await preprocess_text(text_request)

            # Verify the agent was called with correct text
            mock_run.assert_called_once_with("Hello world")

            # Verify the result
            assert isinstance(result, PreprocessedText)
            assert result.text == "Hello world"
            assert result.language == LanguageType.OTHER

    @pytest.mark.asyncio
    async def test_preprocess_empty_text(self) -> None:
        """
        Test preprocessing of empty text.

        :return: None
        """
        # Arrange
        text_request = TextRequest(text="")
        expected_output = PreprocessingOutput(language=LanguageType.OTHER)
        mock_result = Mock()
        mock_result.output = expected_output

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_run:
            result = await preprocess_text(text_request)

            # Verify the agent was called with correct text
            mock_run.assert_called_once_with("")

            # Verify the result
            assert isinstance(result, PreprocessedText)
            assert result.text == ""
            assert result.language == LanguageType.OTHER

    @pytest.mark.asyncio
    async def test_preprocess_text_agent_exception(self) -> None:
        """
        Test handling of agent exceptions during preprocessing.

        :return: None
        """
        # Arrange
        text_request = TextRequest(text="Test text")

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            side_effect=Exception("API Error"),
        ) as mock_run:
            with pytest.raises(Exception, match="API Error"):
                await preprocess_text(text_request)

            # Verify the agent was called
            mock_run.assert_called_once_with("Test text")


@pytest.mark.parametrize(
    "input_text,expected_language",
    [
        ("Καλημέρα", LanguageType.ANCIENT_GREEK),
        ("Salve", LanguageType.LATIN),
        ("Hello", LanguageType.OTHER),
        ("", LanguageType.OTHER),
        ("Καλημέρα and Salve", LanguageType.ANCIENT_GREEK),
    ],
)
class TestPreprocessTextParametrized:
    """Parametrized tests for different text inputs."""

    @pytest.mark.asyncio
    async def test_preprocess_text_parametrized(self, input_text: str, expected_language: LanguageType) -> None:
        """
        Test preprocessing with parametrized inputs.

        :param input_text: The input text to preprocess.
        :param expected_language: The expected language classification.
        :return: None
        """
        # Arrange
        text_request = TextRequest(text=input_text)
        expected_output = PreprocessingOutput(language=expected_language)
        mock_result = Mock()
        mock_result.output = expected_output

        # Act & Assert
        with patch(
            "src.agents.preprocessing.preprocessing_agent.run",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await preprocess_text(text_request)

            # Verify the result
            assert isinstance(result, PreprocessedText)
            assert result.text == input_text
            assert result.language == expected_language
