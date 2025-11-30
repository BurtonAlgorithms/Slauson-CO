"""
Configuration management for Slauson automation suite.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for API keys and settings."""
    
    # Notion
    NOTION_API_KEY = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    NOTION_TEMPLATE_PAGE_ID = os.getenv("NOTION_TEMPLATE_PAGE_ID")
    
    # Canva
    CANVA_API_KEY = os.getenv("CANVA_API_KEY")
    CANVA_TEMPLATE_ID = os.getenv("CANVA_TEMPLATE_ID")
    
    # DocSend
    DOCSEND_API_KEY = os.getenv("DOCSEND_API_KEY")
    DOCSEND_INDIVIDUAL_DECK_ID = os.getenv("DOCSEND_INDIVIDUAL_DECK_ID")
    DOCSEND_MASTER_DECK_ID = os.getenv("DOCSEND_MASTER_DECK_ID")
    
    # Image Processing
    REMOVEBG_API_KEY = os.getenv("REMOVEBG_API_KEY")
    
    # LLM
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Granola (Future)
    GRANOLA_API_KEY = os.getenv("GRANOLA_API_KEY")
    
    @classmethod
    def validate(cls, require_notion=False):
        """Validate that required configuration is present."""
        if require_notion:
            required = [
                ("NOTION_API_KEY", cls.NOTION_API_KEY),
                ("NOTION_DATABASE_ID", cls.NOTION_DATABASE_ID),
            ]
            
            missing = [name for name, value in required if not value]
            if missing:
                raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True

