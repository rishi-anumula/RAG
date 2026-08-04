from typing import List, Optional, Callable

class RecursiveCharacterTextSplitter:
    """
    Lightweight, standalone implementation of RecursiveCharacterTextSplitter.
    Splits text recursively by separators to create chunks within chunk_size.
    Eliminates dependency on heavy external libraries like langchain-text-splitters.
    """
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        length_function: Callable[[str], int] = len,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators if separators is not None else ["\n\n", "\n", " ", ""]
        self.length_function = length_function

    def split_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []

        for i, s in enumerate(separators):
            if s == "":
                separator = ""
                break
            if s in text:
                separator = s
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: List[str] = []
        for s in splits:
            if self.length_function(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    sub_chunks = self._split_text(s, new_separators)
                    final_chunks.extend(sub_chunks)

        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs: List[str] = []
        current_doc: List[str] = []
        total = 0

        for d in splits:
            len_d = self.length_function(d)
            sep_len = self.length_function(separator) if current_doc else 0

            if total + len_d + sep_len > self.chunk_size:
                if current_doc:
                    doc = separator.join(current_doc)
                    if doc.strip():
                        docs.append(doc)
                    
                    # Backtrack to satisfy overlap
                    while total > self.chunk_overlap or (
                        total + len_d + sep_len > self.chunk_size and total > 0
                    ):
                        popped = current_doc.pop(0)
                        total -= self.length_function(popped) + (self.length_function(separator) if current_doc else 0)

            current_doc.append(d)
            total += len_d + (sep_len if len(current_doc) > 1 else 0)

        if current_doc:
            doc = separator.join(current_doc)
            if doc.strip():
                docs.append(doc)

        return docs
