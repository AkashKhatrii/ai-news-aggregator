import anthropic
import os
import json
import logging

logger = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.getenv("CLAUDE_API_KEY")
        self.client = anthropic.Client(api_key=api_key)

    def summarize(self, text):
        SYSTEM_PROMPT = (
            "You are an expert news analyst. Summarize text in a way that covers all significant points, facts, "
            "and data presented, without omitting important details. "
            "Your summary should be accurate, detailed, and capture every key argument, event, and nuance from the original text—not just a superficial gist. "
            "Do not skip technical, contextual, or numerical information. Structure the summary in well-organized paragraphs "
            "or use bullet points where appropriate. Include names, dates, figures, reasons, and the sequence of events or arguments as presented."
            "Finally, keep the response under 2000 characters."
        )
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=600,  
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [{
                            "type": "text",
                            "text":
                                f"Text to summarize:\n---\n{text}\n---\nDetailed, accurate summary:"
                        }]
                    }
                ]
            )
            content = response.content[0].text
            return content.strip()
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None


    def generate_page_title(self, titles):
        """
        titles: list of strings (email subjects)
        Returns: concise, meaningful title summarizing the day's content
        """
        prompt = (
            "You are an expert headline writer. Generate a short, descriptive title "
            "summarizing the common themes or main topics from the following email subjects:\n\n"
            + "\n".join(f"- {t}" for t in titles) +
            "\n\nGenerate a concise, catchy page title as a single sentence or phrase:"
        )
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=50,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }]
            )
            title = response.content[0].text.strip()
            return title
        except Exception as e:
            logger.error(f"Claude generate_page_title error: {e}")
            return None
