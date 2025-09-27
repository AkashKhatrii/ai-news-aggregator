from notion_client import Client
import logging

logger = logging.getLogger(__name__)

class NotionClient:
    def __init__(self, notion_token, parent_page_id):
        self.client = Client(auth=notion_token)
        self.parent_page_id = parent_page_id

    def find_daily_page(self, date_str):
        """Search for a child page of parent with title == date_str, return page_id or None"""
        try:
            response = self.client.search(
                query=date_str,
                filter={"property": "object", "value": "page"},
                sort={"direction": "ascending", "timestamp": "last_edited_time"}
            )
            for result in response.get('results', []):
                # Confirm parent matches
                parents = result.get('parent', {})
                if parents.get('type') == 'page_id' and parents.get('page_id') == self.parent_page_id:
                    title = self._extract_title(result.get('properties', {}))
                    if title == date_str:
                        return result.get('id')
            return None
        except Exception as e:
            logger.error(f"Error searching daily page: {e}")
            return None

    def create_daily_page(self, date_str):
        """Create a new child page titled date_str under the parent page"""
        try:
            new_page = self.client.pages.create(
                parent={"type": "page_id", "page_id": self.parent_page_id},
                properties={
                    "title": [
                        {
                            "text": {
                                "content": date_str
                            }
                        }
                    ]
                }
            )
            logger.info(f"Created new daily page: {date_str}")
            return new_page.get('id')
        except Exception as e:
            logger.error(f"Error creating daily page: {e}")
            return None

    def append_summary_to_daily_page(self, page_id, title, summary):
        try:
            blocks = [
                {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": title  # Make sure 'title' is a non-empty string
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary  # Make sure 'summary' is a non-empty string
                            }
                        }
                    ]
                }
            }

            ]

            response = self.client.blocks.children.append(
                block_id=page_id,
                children=blocks
            )
            logger.info(f"Appended summary to page {page_id}: {title}")
            return response
        except Exception as e:
            logger.error(f"Error appending summary: {e}")
            return None


    def _extract_title(self, properties):
        """Helper to extract the title text from page properties"""
        # Title property shape depends on database schema, assuming single title property
        # For simplicity, find first title text
        for key, value in properties.items():
            if 'title' in value:
                titles = value['title']
                if titles and len(titles) > 0:
                    return titles[0]['text']['content']
        return None
