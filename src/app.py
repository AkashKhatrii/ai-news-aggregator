from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
from datetime import datetime, time, timedelta
import pytz
import logging

from email_client.gmail_client import GmailClient
from summarization.claude_api import ClaudeClient
from notion.notion_client import NotionClient

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI()

def get_yesterday_9am_to_today_859am_pst():
    pst = pytz.timezone("America/Los_Angeles")
    now_pst = datetime.now(pst)
    today_9am = datetime.combine(now_pst.date(), time(9, 0), pst)
    if now_pst < today_9am:
        today_9am -= timedelta(days=1)
    start_time = today_9am - timedelta(days=1)
    end_time = today_9am - timedelta(seconds=1)
    return start_time, end_time

def generate_page_title(claude_client, titles):
    prompt = (
        "You are an expert headline writer. Generate a short, descriptive title "
        "summarizing the common themes or main topics from the following email subjects:\n\n"
        + "\n".join(f"- {t}" for t in titles) +
        "\n\nGenerate a concise, catchy page title as a single sentence or phrase:"
    )
    try:
        response = claude_client.client.messages.create(
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

def run_summary_job():
    notion_token = os.getenv("NOTION_API_TOKEN")
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    claude_api_key = os.getenv("CLAUDE_API_KEY")

    if not notion_token or not parent_page_id or not claude_api_key:
        logger.error("API keys or notion IDs missing in environment variables.")
        return {"error": "Missing environment variables"}

    notion_client = NotionClient(notion_token, parent_page_id)
    gmail_client = GmailClient()
    gmail_client.authenticate()
    claude_client = ClaudeClient(claude_api_key)

    start_time, end_time = get_yesterday_9am_to_today_859am_pst()
    query = f'after:{int(start_time.timestamp())} before:{int(end_time.timestamp())}'

    emails = gmail_client.list_recent_emails(max_results=100, query=query)
    if not emails:
        logger.info("No emails found for the specified time window.")
        return {"status": "No emails found"}

    summaries = []
    email_titles = []

    for email in emails:
        email_titles.append(email['subject'])
        body = gmail_client.get_email_body(email['id'])
        if not body:
            continue
        summary = claude_client.summarize(body)
        if summary:
            summaries.append({'title': email['subject'], 'summary': summary})

    if not summaries:
        logger.info("No summaries generated.")
        return {"status": "No summaries generated"}

    page_title_text = generate_page_title(claude_client, email_titles)
    date_str = datetime.now(pytz.timezone("America/Los_Angeles")).strftime("%b %d, %Y")
    full_page_title = f"{page_title_text} - {date_str}" if page_title_text else date_str

    page_id = notion_client.find_daily_page(full_page_title)
    if not page_id:
        page_id = notion_client.create_daily_page(full_page_title)

    if not page_id:
        logger.error("Could not find/create Notion page.")
        return {"error": "Failed to create/find Notion page"}

    for item in summaries:
        notion_client.append_summary_to_daily_page(page_id, item['title'], item['summary'])

    logger.info(f"Saved {len(summaries)} summaries to Notion page '{full_page_title}'")
    return {"status": f"Saved {len(summaries)} summaries to Notion", "page_title": full_page_title}

@app.get("/")
def root():
    return {"message": "AI Newsletter Summarizer backend is running."}

@app.get("/run-summary")
def run_summary_endpoint():
    result = run_summary_job()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result
