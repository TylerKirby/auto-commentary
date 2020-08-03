import re


def clean_text(text: str) -> str:
    """
    Clean text of non alphabetic characters and force lower.
    :param text:
    :return:
    """
    # Force lower
    text = text.lower()
    # Remove non alphabetic and space characters
    text = re.sub('[^a-z ]', '', text)
    # Deduplicate white space
    text = " ".join(text.split())
    return text
