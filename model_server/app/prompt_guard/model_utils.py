import numpy as np


def split_text_into_chunks(text, max_words=300):
    """
    Max number of tokens for tokenizer is 512
    Split the text into chunks of 300 words (as approximation for tokens)
    """
    words = text.split()  # Split text into words
    # Estimate token count based on word count (1 word ≈ 1 token)
    chunk_size = max_words  # Use the word count as an approximation for tokens
    chunks = [
        " ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)
    ]
    return chunks


def softmax(x):
    return np.exp(x) / np.exp(x).sum(axis=0)
