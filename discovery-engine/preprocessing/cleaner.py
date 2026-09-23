import re
import unicodedata

class TextCleaner:
    """
    Cleans raw document text before chunking and embedding.
    """
    def __init__(self):
        # Regex to match multiple newlines
        self.newlines_re = re.compile(r'\n{3,}')
        # Regex to match multiple spaces
        self.spaces_re = re.compile(r' {2,}')
        # Basic URL regex (excludes trailing sentence punctuation)
        self.url_re = re.compile(r'https?://[^\s!?,;]+|www\.[^\s!?,;]+')

    def clean(self, text: str) -> str:
        if not text:
            return ""

        # 1. Normalize Unicode (NFKC)
        text = unicodedata.normalize('NFKC', text)

        # 2. Remove URLs (often irrelevant to semantic search of user complaints)
        text = self.url_re.sub('', text)

        # 3. Replace 3+ newlines with 2 newlines (preserve paragraph boundaries but avoid huge gaps)
        text = self.newlines_re.sub('\n\n', text)

        # 4. Replace multiple spaces with a single space
        text = self.spaces_re.sub(' ', text)

        return text.strip()
