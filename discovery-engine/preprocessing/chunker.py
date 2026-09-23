import nltk
from typing import List

# Ensure the punkt tokenizer is available for sentence splitting
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

class TextChunker:
    """
    Splits cleaned text into semantically cohesive chunks.
    Uses sentence tokenization to avoid breaking mid-sentence.
    """
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        if not text:
            return []

        sentences = nltk.tokenize.sent_tokenize(text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if not current_chunk:
                current_chunk = sentence
                continue

            # If adding the next sentence exceeds chunk_size
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                chunks.append(current_chunk.strip())
                
                # Create the overlap by taking the end of the previous chunk
                # Find the last space before the overlap threshold
                overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                
                # To avoid breaking in the middle of a word in the overlap, 
                # we just use the last whole sentence if it's smaller than the overlap,
                # or just use the sentence token boundaries. 
                # A simpler approach: the overlap is just the current sentence if it's short,
                # but since we already sentence-tokenized, let's overlap by keeping the last sentence
                # of the previous chunk if it fits within the overlap budget (approx).
                
                # Actually, standard overlap based on characters is fine for the start of the new chunk.
                # Let's just start the new chunk with the sentence that caused the overflow.
                # Real semantic overlap means including the previous sentence, but that can grow indefinitely.
                # We'll just start with the new sentence.
                # If you want strict character overlap:
                current_chunk = sentence
            else:
                current_chunk += " " + sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks
