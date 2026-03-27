"""
LlamaIndex setup with ChromaDB and Gemini
Provides singleton instances of index and chat engine
"""

import os
import json
import time
from collections import deque
from pathlib import Path
from typing import Optional, List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings

# LlamaIndex imports - using core package structure
from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.gemini import Gemini  
from llama_index.embeddings.gemini import GeminiEmbedding
from google.api_core.exceptions import ResourceExhausted

import yaml
from dotenv import load_dotenv

load_dotenv()


class LlamaIndexManager:
    """Manages LlamaIndex components with ChromaDB backend"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self._index = None
        self._chat_engine = None
        self._chroma_client = None
        self._collection = None
        self._request_times = deque()
        self._max_requests_per_minute = 8  # Gemini default limit per model
        self._max_retry_attempts = 3
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _init_chroma(self) -> ChromaVectorStore:
        """Initialize ChromaDB client and collection"""
        persist_dir = self.config['chroma']['persist_dir']
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        self._chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        collection_name = self.config['chroma']['collection_name']
        self._collection = self._chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Personal notes and memories"}
        )
        
        return ChromaVectorStore(chroma_collection=self._collection)
    
    def _get_llm_and_embed(self):
        """Get LLM and embedding models"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        llm = Gemini(
            model=self.config['llm']['model'],
            api_key=api_key,
            temperature=self.config['llm']['temperature']
        )
        
        embed_model = GeminiEmbedding(
            model_name=self.config['embeddings']['model'],
            api_key=api_key
        )
        
        return llm, embed_model
    
    def _throttle_llm(self) -> None:
        """Simple rate limiter to respect Gemini quota"""
        now = time.time()
        window_seconds = 60
        max_requests = self._max_requests_per_minute
        # Remove timestamps outside the window
        while self._request_times and now - self._request_times[0] > window_seconds:
            self._request_times.popleft()
        if len(self._request_times) >= max_requests:
            sleep_time = window_seconds - (now - self._request_times[0]) + 0.1
            if sleep_time > 0:
                print(f"⚠️  Gemini rate limit reached. Sleeping for {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            # After sleeping, clean again
            now = time.time()
            while self._request_times and now - self._request_times[0] > window_seconds:
                self._request_times.popleft()
        self._request_times.append(time.time())
    
    @staticmethod
    def _retry_sleep_seconds(exc: ResourceExhausted, attempt: int) -> float:
        """Determine how long to sleep before retrying after 429"""
        fallback_seconds = min(5 * attempt, 30)
        retry_delay = getattr(exc, "retry_delay", None)
        if retry_delay:
            seconds = getattr(retry_delay, "seconds", 0)
            nanos = getattr(retry_delay, "nanos", 0)
            computed = seconds + nanos / 1e9
            if computed > 0:
                return max(computed, fallback_seconds)
        return fallback_seconds
    
    def get_index(self) -> VectorStoreIndex:
        """Get or create VectorStoreIndex"""
        if self._index is None:
            llm, embed_model = self._get_llm_and_embed()
            
            # Configure global settings
            Settings.llm = llm
            Settings.embed_model = embed_model
            Settings.chunk_size = self.config['indexing']['chunk_size']
            Settings.chunk_overlap = self.config['indexing']['chunk_overlap']
            
            vector_store = self._init_chroma()
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store
            )
            
            # Create index
            try:
                # Try to load from existing vector store
                self._index = VectorStoreIndex.from_vector_store(
                    vector_store=vector_store
                )
                print("✓ Loaded existing index from ChromaDB")
            except Exception as e:
                # Create new empty index
                self._index = VectorStoreIndex.from_documents(
                    documents=[],
                    storage_context=storage_context
                )
                print("✓ Created new empty index")
        
        return self._index
    
    def get_chat_engine(self, reset: bool = False):
        """Get chat engine with memory"""
        if self._chat_engine is None or reset:
            index = self.get_index()
            llm, _ = self._get_llm_and_embed()
            
            base_engine = index.as_chat_engine(
                chat_mode="condense_question",
                llm=llm,
                verbose=False
            )
            self._chat_engine = _ThrottledChatEngine(self, base_engine)
        
        return self._chat_engine
    
    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten metadata to be ChromaDB compatible.
        Converts complex types (dict, list) to JSON strings.
        ChromaDB only supports: str, int, float, None
        """
        flattened = {}
        for key, value in metadata.items():
            if value is None or isinstance(value, (str, int, float)):
                # Simple types - store as-is
                flattened[key] = value
            elif isinstance(value, (dict, list)):
                # Complex types - serialize to JSON string
                flattened[key] = json.dumps(value)
            else:
                # Fallback: convert to string
                flattened[key] = str(value)
        return flattened

    def _unflatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to restore metadata that may have been JSON-serialized."""
        restored: Dict[str, Any] = {}
        for key, value in (metadata or {}).items():
            if isinstance(value, str):
                try:
                    restored[key] = json.loads(value)
                    continue
                except (TypeError, json.JSONDecodeError):
                    pass
            restored[key] = value
        return restored

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Add documents to the index with metadata"""
        # Flatten metadata to be ChromaDB compatible
        flattened_metadatas = [self._flatten_metadata(m) for m in metadatas]

        
        documents = [
            Document(text=text, metadata=metadata)
            for text, metadata in zip(texts, flattened_metadatas)
        ]
        
        index = self.get_index()
        for doc in documents:
            index.insert(doc)
        print(f"✓ Added {len(documents)} document(s) to index")

    def overwrite_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Replace existing documents with provided ones."""
        self.reset()
        self.add_documents(texts, metadatas)

    def query(self, query: str, filters: Optional[Dict] = None) -> str:
        """Query the index with optional metadata filters"""
        index = self.get_index()
        
        if filters:
            query_engine = index.as_query_engine(
                filters=filters,
                similarity_top_k=5
            )
        else:
            query_engine = index.as_query_engine(
                streaming=False,
                similarity_top_k=3
            )
        attempt = 0
        while True:
            try:
                self._throttle_llm()
                response = query_engine.query(query)
                return str(response)
            except ResourceExhausted as exc:
                attempt += 1
                if attempt >= self._max_retry_attempts:
                    print("⚠️  Gemini quota exceeded. Falling back to retrieved context.")
                    nodes = query_engine.retrieve(query)
                    if not nodes:
                        return "Unable to answer right now due to quota limits. Please try again later."
                    fallback = " ".join(node.get_text() for node in nodes[:3])
                    return fallback[:500]
                wait_seconds = self._retry_sleep_seconds(exc, attempt)
                print(f"⚠️  Gemini rate limited (attempt {attempt}/{self._max_retry_attempts}). Retrying in {wait_seconds:.1f}s...")
                time.sleep(wait_seconds)
    
    def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return stored documents and metadata from the vector store."""
        self.get_index()
        if self._collection is None:
            return []

        results = self._collection.get(
            include=["documents", "metadatas"],
            limit=limit
        )
        documents: List[Dict[str, Any]] = []
        for text, metadata in zip(results.get("documents", []), results.get("metadatas", [])):
            documents.append({
                "text": text,
                "metadata": self._unflatten_metadata(metadata or {})
            })
        return documents

    def search_documents(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents whose content contains the keyword."""
        if not keyword:
            return []
        self.get_index()
        if self._collection is None:
            return []

        results = self._collection.get(
            where_document={"$contains": keyword},
            include=["documents", "metadatas"],
            limit=limit
        )
        documents: List[Dict[str, Any]] = []
        for text, metadata in zip(results.get("documents", []), results.get("metadatas", [])):
            documents.append({
                "text": text,
                "metadata": self._unflatten_metadata(metadata or {})
            })
        return documents

    def reset(self) -> None:
        """Reset the index and chat engine"""
        if self._chroma_client:
            self._chroma_client.reset()
        self._index = None
        self._chat_engine = None
        print("✓ Reset complete")


class _ThrottledChatEngine:
    """Wrap chat engine to add throttling and quota fallback"""
    def __init__(self, manager: LlamaIndexManager, base_engine):
        self._manager = manager
        self._base_engine = base_engine

    def chat(self, message: str):
        attempt = 0
        while True:
            try:
                self._manager._throttle_llm()
                return self._base_engine.chat(message)
            except ResourceExhausted as exc:
                attempt += 1
                if attempt >= self._manager._max_retry_attempts:
                    print("⚠️  Gemini quota exceeded during chat. Returning available context.")
                    # Attempt to answer using retrieval fallback
                    index = self._manager.get_index()
                    query_engine = index.as_query_engine(similarity_top_k=3)
                    nodes = query_engine.retrieve(message)
                    if not nodes:
                        return "I'm over capacity right now. Please try again shortly."
                    fallback = " ".join(node.get_text() for node in nodes[:3])
                    return fallback[:500]
                wait_seconds = self._manager._retry_sleep_seconds(exc, attempt)
                print(f"⚠️  Gemini rate limited (chat attempt {attempt}/{self._manager._max_retry_attempts}). Retrying in {wait_seconds:.1f}s...")
                time.sleep(wait_seconds)

# Global singleton instance
_manager_instance: Optional[LlamaIndexManager] = None


def get_manager() -> LlamaIndexManager:
    """Get singleton LlamaIndexManager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = LlamaIndexManager()
    return _manager_instance


def validate_environment() -> List[str]:
    """Run basic environment checks required for the assistant to operate."""
    errors: List[str] = []

    if not os.getenv("GEMINI_API_KEY"):
        errors.append("GEMINI_API_KEY is not set. Add it to your environment or .env file.")

    config_path = Path("config.yaml")
    if not config_path.exists():
        errors.append("config.yaml is missing at project root.")
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                yaml.safe_load(config_file)  # validate format
        except Exception as exc:  # pragma: no cover - defensive parsing check
            errors.append(f"config.yaml could not be parsed: {exc}")

    chroma_dir = Path("./data/chroma_db")
    try:
        chroma_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - environment specific
        errors.append(f"Unable to access ChromaDB directory {chroma_dir}: {exc}")

    return errors
