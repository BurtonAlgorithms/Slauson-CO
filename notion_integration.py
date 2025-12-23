"""
Notion API integration for portfolio company management.
"""
from notion_client import Client
from typing import Dict, List, Optional
from config import Config
import uuid


class NotionIntegration:
    """Handle Notion API operations."""
    
    def __init__(self):
        """Initialize Notion client."""
        if not Config.NOTION_API_KEY:
            raise ValueError("NOTION_API_KEY not configured. Notion integration is optional when using Zapier.")
        self.client = Client(auth=Config.NOTION_API_KEY)
    
    def create_portfolio_company_entry(self, company_data: Dict) -> str:
        """
        Create a new entry in the Portfolio Companies database.
        
        Args:
            company_data: Dictionary containing company information
            
        Returns:
            Page ID of created entry
        """
        if not Config.NOTION_DATABASE_ID:
            raise ValueError("NOTION_DATABASE_ID not configured")
        
        properties = self._format_company_properties(company_data)
        
        response = self.client.pages.create(
            parent={"database_id": Config.NOTION_DATABASE_ID},
            properties=properties
        )
        
        return response["id"]
    
    def _format_company_properties(self, data: Dict) -> Dict:
        """
        Format company data into Notion properties format.
        
        Args:
            data: Raw company data
            
        Returns:
            Formatted properties dictionary
        """
        properties = {}
        
        # Text fields
        if "name" in data:
            properties["Name"] = {"title": [{"text": {"content": data["name"]}}]}
        
        if "website" in data:
            properties["Website"] = {"url": data["website"]}
        
        if "description" in data:
            properties["Description"] = {"rich_text": [{"text": {"content": data["description"]}}]}
        
        if "address" in data:
            properties["Address"] = {"rich_text": [{"text": {"content": data["address"]}}]}
        
        # Date fields
        if "birthday" in data:
            properties["Birthday"] = {"date": {"start": data["birthday"]}}
        
        if "investment_date" in data:
            properties["Investment Date"] = {"date": {"start": data["investment_date"]}}
        
        # Multi-select fields
        if "co_investors" in data:
            if isinstance(data["co_investors"], list):
                properties["Co-Investors"] = {
                    "multi_select": [{"name": investor} for investor in data["co_investors"]]
                }
        
        # Number fields
        if "num_employees" in data:
            properties["Number of Employees"] = {"number": data["num_employees"]}
        
        # Checkbox fields
        if "first_time_founder" in data:
            properties["First Time Founder"] = {"checkbox": data["first_time_founder"]}
        
        # URL fields
        if "investment_memo_link" in data:
            properties["Investment Memo"] = {"url": data["investment_memo_link"]}
        
        return properties
    
    def create_company_folder(self, company_name: str, template_page_id: Optional[str] = None) -> str:
        """
        Create a company subfolder with pre-filled sections.
        
        Args:
            company_name: Name of the company
            template_page_id: Optional template page to duplicate
            
        Returns:
            Page ID of created folder
        """
        if template_page_id or Config.NOTION_TEMPLATE_PAGE_ID:
            # Duplicate template
            template_id = template_page_id or Config.NOTION_TEMPLATE_PAGE_ID
            response = self.client.pages.create(
                parent={"page_id": template_id},
                properties={
                    "title": {"title": [{"text": {"content": company_name}}]}
                }
            )
            return response["id"]
        else:
            # Create new page with basic structure
            parent_id = Config.NOTION_DATABASE_ID
            response = self.client.pages.create(
                parent={"page_id": parent_id},
                properties={
                    "title": {"title": [{"text": {"content": company_name}}]}
                },
                children=[
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"text": {"content": "Notes"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"text": {"content": "Updates"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"text": {"content": "Contacts"}}]
                        }
                    }
                ]
            )
            return response["id"]
    
    def add_granola_note(self, company_page_id: str, note_content: str, meeting_title: str) -> str:
        """
        Add a Granola meeting note to a company's Notion page.
        
        Args:
            company_page_id: Notion page ID of the company
            note_content: Content of the meeting note
            meeting_title: Title of the meeting
            
        Returns:
            Block ID of created note
        """
        response = self.client.blocks.children.append(
            block_id=company_page_id,
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": meeting_title}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": note_content}}]
                    }
                }
            ]
        )
        return response["results"][0]["id"] if response["results"] else None
    
    def get_company_by_name(self, company_name: str) -> Optional[Dict]:
        """
        Find a company in the database by name.
        
        Args:
            company_name: Name of the company to find
            
        Returns:
            Company page data or None if not found
        """
        if not Config.NOTION_DATABASE_ID:
            return None
        
        response = self.client.databases.query(
            database_id=Config.NOTION_DATABASE_ID,
            filter={
                "property": "Name",
                "title": {
                    "equals": company_name
                }
            }
        )
        
        if response["results"]:
            return response["results"][0]
        return None
    
    def update_company_record(
        self,
        page_id: str,
        google_drive_link: Optional[str] = None,
        docsend_link: Optional[str] = None,
        canva_design_id: Optional[str] = None,
        canva_design_url: Optional[str] = None,
        status: str = "completed"
    ) -> bool:
        """
        Update a company record with Google Drive link, DocSend link, and status.
        
        Args:
            page_id: Notion page ID of the company record
            google_drive_link: Optional Google Drive shareable link
            docsend_link: Optional DocSend shareable link
            status: Status to set (default: "completed")
            
        Returns:
            True if update successful
        """
        properties = {}
        
        # Update Google Drive link if provided
        if google_drive_link:
            # Try different possible property names
            for prop_name in ["Google Drive Link", "Drive Link", "PDF Link", "Slide Link"]:
                try:
                    properties[prop_name] = {"url": google_drive_link}
                    break
                except:
                    pass
        
        # Update DocSend link if provided
        if docsend_link:
            # Try different possible property names
            for prop_name in ["DocSend Link", "DocSend", "Presentation Link"]:
                try:
                    properties[prop_name] = {"url": docsend_link}
                    break
                except:
                    pass
        
        # Update Canva Design ID if provided
        if canva_design_id:
            for prop_name in ["Canva Design ID", "Design ID", "Canva ID"]:
                try:
                    properties[prop_name] = {"rich_text": [{"text": {"content": canva_design_id}}]}
                    break
                except:
                    pass
        
        # Update Canva Design URL if provided
        if canva_design_url:
            for prop_name in ["Canva Design URL", "Design URL", "Canva URL"]:
                try:
                    properties[prop_name] = {"url": canva_design_url}
                    break
                except:
                    pass
        
        # Update status
        if status:
            # Try different possible property names
            for prop_name in ["Status", "Slide Status", "Processing Status", "Completion Status"]:
                try:
                    # Status could be a select or text field
                    properties[prop_name] = {"select": {"name": status}}
                    break
                except:
                    try:
                        properties[prop_name] = {"rich_text": [{"text": {"content": status}}]}
                        break
                    except:
                        pass
        
        if not properties:
            print("Warning: No properties to update in Notion")
            return False
        
        try:
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            return True
        except Exception as e:
            print(f"Error updating Notion record: {e}")
            # Try updating properties one by one
            for prop_name, prop_value in properties.items():
                try:
                    self.client.pages.update(
                        page_id=page_id,
                        properties={prop_name: prop_value}
                    )
                except Exception as e2:
                    print(f"Warning: Could not update property '{prop_name}': {e2}")
            return False
    
    def get_company_by_page_id(self, page_id: str) -> Optional[Dict]:
        """
        Get company record by page ID and extract relevant data.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Dictionary with company data including google_drive_link and canva_design_id, or None if not found
        """
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            properties = response.get("properties", {})
            
            # Extract relevant fields
            company_data = {}
            
            # Extract Google Drive link
            for prop_name in ["Google Drive Link", "Drive Link", "PDF Link", "Slide Link"]:
                if prop_name in properties:
                    prop = properties[prop_name]
                    if prop.get("type") == "url":
                        company_data["google_drive_link"] = prop.get("url")
                        break
            
            # Extract Canva Design ID
            for prop_name in ["Canva Design ID", "Design ID", "Canva ID"]:
                if prop_name in properties:
                    prop = properties[prop_name]
                    if prop.get("type") == "rich_text":
                        rich_text = prop.get("rich_text", [])
                        if rich_text:
                            company_data["canva_design_id"] = " ".join([text.get("plain_text", "") for text in rich_text])
                            break
            
            # Extract Canva Design URL
            for prop_name in ["Canva Design URL", "Design URL", "Canva URL"]:
                if prop_name in properties:
                    prop = properties[prop_name]
                    if prop.get("type") == "url":
                        company_data["canva_design_url"] = prop.get("url")
                        break
            
            return company_data if company_data else None
        except Exception as e:
            print(f"Error retrieving Notion page: {e}")
            return None

