"""
Agent for preprocessing text.
"""

import asyncio

from dotenv import load_dotenv
from pydantic_ai import Agent

from src.agents.models import (
    PreprocessedText,
    PreprocessingOutput,
    TextRequest,
)

load_dotenv()

PREPROCESSING_AGENT_MODEL = "openai:gpt-4o-mini"


preprocessing_agent = Agent(
    model=PREPROCESSING_AGENT_MODEL,
    output_type=PreprocessingOutput,
    system_prompt="""
    You are a helpful assistant that preprocesses text.
    You will be given a text and you will need to preprocess it.
    You must respond with a single string only from these options:
    - ancient_greek
    - latin
    - other
    """,
)


async def preprocess_text(text_request: TextRequest) -> PreprocessedText:
    """Preprocess text."""
    result = await preprocessing_agent.run(text_request.text)
    return PreprocessedText(
        text=text_request.text,
        language=result.output.language,
    )


if __name__ == "__main__":

    async def main():
        text_request = TextRequest(text="Καλημέρα")
        preprocessed_text = await preprocess_text(text_request)
        print(preprocessed_text)

    asyncio.run(main())
