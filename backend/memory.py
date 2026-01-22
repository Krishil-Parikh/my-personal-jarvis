import chromadb
from chromadb.config import Settings
import uuid
from datetime import datetime
import os

class ConversationMemory:
    def __init__(self, persist_directory="./chroma_db"):
        """
        Initialize ChromaDB for conversation memory
        
        Args:
            persist_directory: Directory to persist the database
        """
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collections
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "User conversations and queries"}
        )
        
        self.web_context = self.client.get_or_create_collection(
            name="web_context",
            metadata={"description": "Web search results and crawled content"}
        )
        
        print(f"ChromaDB initialized at {persist_directory}")
    
    def add_conversation(self, user_query, assistant_response, metadata=None):
        """
        Store a conversation turn
        
        Args:
            user_query: User's query
            assistant_response: Assistant's response
            metadata: Additional metadata
        """
        if metadata is None:
            metadata = {}
        
        metadata.update({
            "timestamp": datetime.now().isoformat(),
            "type": "conversation"
        })
        
        conversation_text = f"User: {user_query}\nAssistant: {assistant_response}"
        
        self.conversations.add(
            documents=[conversation_text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
    
    def add_web_context(self, query, url, content):
        """
        Store web search context
        
        Args:
            query: Search query
            url: Website URL
            content: Crawled content
        """
        metadata = {
            "query": query,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "type": "web_search"
        }
        
        self.web_context.add(
            documents=[content],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
    
    def get_relevant_context(self, query, n_results=5):
        """
        Retrieve relevant context for a query
        
        Args:
            query: Query to search for
            n_results: Number of results to return
        
        Returns:
            List of relevant documents
        """
        try:
            # Search in conversations
            conv_results = self.conversations.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Search in web context
            web_results = self.web_context.query(
                query_texts=[query],
                n_results=n_results
            )
            
            return {
                "conversations": conv_results,
                "web_context": web_results
            }
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return {"conversations": None, "web_context": None}
    
    def get_recent_conversations(self, n=5):
        """
        Get recent conversation history
        
        Args:
            n: Number of recent conversations
        
        Returns:
            List of recent conversations
        """
        try:
            results = self.conversations.get(
                limit=n,
                include=["documents", "metadatas"]
            )
            return results
        except Exception as e:
            print(f"Error getting recent conversations: {e}")
            return None
