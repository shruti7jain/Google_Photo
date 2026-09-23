import pytest
from preprocessing.cleaner import TextCleaner
from preprocessing.chunker import TextChunker

class TestTextCleaner:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_empty_string(self):
        assert self.cleaner.clean("") == ""
        assert self.cleaner.clean(None) == ""

    def test_url_removal(self):
        text = "Check this out https://example.com/photo and this www.google.com!"
        expected = "Check this out and this !"
        assert self.cleaner.clean(text) == expected

    def test_excessive_newlines(self):
        text = "Line 1\n\n\n\nLine 2\n\n\nLine 3"
        expected = "Line 1\n\nLine 2\n\nLine 3"
        assert self.cleaner.clean(text) == expected

    def test_excessive_spaces(self):
        text = "This   has    way  too   many spaces."
        expected = "This has way too many spaces."
        assert self.cleaner.clean(text) == expected

    def test_unicode_normalization(self):
        # Fullwidth 'H', 'e', 'l', 'l', 'o'
        text = "\uFF28\uFF45\uFF4C\uFF4C\uFF4F" 
        expected = "Hello"
        assert self.cleaner.clean(text) == expected

class TestTextChunker:
    def setup_method(self):
        self.chunker = TextChunker(chunk_size=100, overlap=20)

    def test_empty_string(self):
        assert self.chunker.chunk("") == []
        assert self.chunker.chunk(None) == []

    def test_single_short_sentence(self):
        text = "This is a short sentence."
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_multiple_sentences_within_chunk(self):
        text = "Sentence one. Sentence two. Sentence three."
        # All fit in 100 chars
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunking_exceeds_size(self):
        # Each sentence is ~45 chars. 3 sentences = ~135 chars, exceeding 100 limit.
        s1 = "This is the first long sentence in the text."
        s2 = "This is the second long sentence right here."
        s3 = "This is the third and final long sentence."
        text = f"{s1} {s2} {s3}"
        
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 2
        # First chunk should have s1 and s2
        assert chunks[0] == f"{s1} {s2}"
        # Second chunk should have s3
        assert chunks[1] == s3
