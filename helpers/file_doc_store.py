import os
import json
from typing import Iterator, List, Optional, Sequence, Tuple

from langchain_core.documents import Document
from langchain_core.stores import BaseStore


class FileDocStore(BaseStore[str, Document]):
    def __init__(self, path: str = "./parent_docstore"):
        self.path = path
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            # In read-only filesystems (like Lambda), fall back to /tmp
            if e.errno == 30:  # Read-only file system
                self.path = "/tmp/parent_docstore"
                os.makedirs(self.path, exist_ok=True)
            else:
                raise

    def _get_path(self, key: str) -> str:
        safe_key = key.replace("/", "_")
        return os.path.join(self.path, f"{safe_key}.json")

    def mget(self, keys: Sequence[str]) -> List[Optional[Document]]:
        docs: List[Optional[Document]] = []
        for key in keys:
            file_path = self._get_path(key)
            if not os.path.exists(file_path):
                docs.append(None)
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            docs.append(Document(**data))
        return docs

    def mset(self, key_value_pairs: Sequence[Tuple[str, Document]]) -> None:
        for key, doc in key_value_pairs:
            with open(self._get_path(key), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "page_content": doc.page_content,
                        "metadata": doc.metadata,
                    },
                    f,
                    ensure_ascii=False,
                )

    def mdelete(self, keys: Sequence[str]) -> None:
        for key in keys:
            file_path = self._get_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)

    def yield_keys(self, prefix: Optional[str] = None) -> Iterator[str]:
        for filename in os.listdir(self.path):
            if not filename.endswith(".json"):
                continue
            key = filename[:-5]
            if prefix is None or key.startswith(prefix):
                yield key