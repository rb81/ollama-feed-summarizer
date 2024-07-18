import os
import feedparser
from datetime import datetime
import json
import logging
from ollama import Client, ResponseError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Initialize Ollama client
ollama_client = Client(host=f"http://{config['ollama_ip']}:{config['ollama_port']}")

def read_feeds(file_path):
    """Read feed URLs from a file."""
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def write_feeds(file_path, feeds):
    """Write feed URLs to a file."""
    with open(file_path, 'w') as file:
        for feed in feeds:
            file.write(f"{feed}\n")

def fetch_and_validate_feed(url, num_articles):
    """Fetch content from an RSS feed, validate and standardize its content."""
    feed = feedparser.parse(url)
    valid_entries = []
    
    for entry in feed.entries[:num_articles]:
        content = (entry.get('summary') or 
                   entry.get('description') or 
                   entry.get('content', [{}])[0].get('value', '') or 
                   entry.get('title', ''))
        
        if content.strip():  # Check if there's any non-whitespace content
            valid_entries.append({
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', 'No URL available'),
                'content': content
            })
    
    return valid_entries if valid_entries else None

def ensure_model_available(model):
    """Ensure the specified model is available, attempting to pull if not."""
    try:
        ollama_client.chat(model=model, messages=[{"role": "user", "content": "Test"}])
    except ResponseError as e:
        if e.status_code == 404:
            logging.warning(f"Model '{model}' not found. Attempting to pull...")
            try:
                ollama_client.pull(model)
                logging.info(f"Successfully pulled model '{model}'")
            except Exception as pull_error:
                logging.error(f"Failed to pull model '{model}': {str(pull_error)}")
                raise
        else:
            logging.error(f"Unexpected error when checking model availability: {str(e)}")
            raise

def summarize_article(article):
    """Summarize an article using Ollama."""
    user_prompt = f"""## INSTRUCTION
    
    Respond with 1-2 sentences that summarize the key message of this article:

    ## ARTICLE
    
    {article['content']}

    ## RULES

    - DO NOT INCLUDE ANYTHING OTHER THAN THE SUMMARY IN YOUR RESPONSE
    - DO NOT ADD ANY TEXT BEFORE OR AFTER THE SUMMARY
    - ONLY RESPOND WITH THE ARTICLE SUMMARY
    """

    try:
        response = ollama_client.chat(model=config['ollama_model'], messages=[
            {
                'role': 'user',
                'content': user_prompt,
            }
        ])
        summary = response['message']['content']
        # Remove any empty lines and ensure proper formatting
        summary_lines = [line.strip() for line in summary.split('\n') if line.strip()]
        formatted_summary = '\n'.join(summary_lines)
        return formatted_summary
    except ResponseError as e:
        logging.error(f"Ollama API error: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error during summarization: {str(e)}")
        return None

def main():
    feeds_file = config['feeds_file']
    removed_feeds_file = config['removed_feeds_file']
    output_folder = os.path.expanduser(config['output_folder'])
    num_articles = config['num_articles']

    os.makedirs(output_folder, exist_ok=True)

    try:
        ensure_model_available(config['ollama_model'])
    except Exception:
        logging.error("Failed to ensure model availability. Exiting.")
        return

    feeds = read_feeds(feeds_file)
    removed_feeds = []
    summaries = []

    for feed_url in feeds:
        logging.info(f"Processing feed: {feed_url}")
        articles = fetch_and_validate_feed(feed_url, num_articles)

        if articles:
            for article in articles:
                summary = summarize_article(article)
                if summary:
                    summaries.append(f"## {article['title']}\n\n{summary}\n\n{article['link']}\n\n")
                else:
                    logging.warning(f"Failed to summarize article: {article['title']}")
        else:
            logging.warning(f"No valid content found for feed: {feed_url}")
            removed_feeds.append(feed_url)

    # Update feeds files
    write_feeds(feeds_file, [f for f in feeds if f not in removed_feeds])
    write_feeds(removed_feeds_file, removed_feeds)

    # Get current date and format it
    current_date = datetime.now()
    formatted_date = current_date.strftime("%A, %B %d, %Y")
    
    # Write summaries to file
    output_file = os.path.join(output_folder, f"{current_date.strftime('%Y-%m-%d')}_feed-summaries.md")
    with open(output_file, 'w') as file:
        file.write(f"# News for {formatted_date}\n\n")
        file.write("\n".join(summaries))

    logging.info(f"Summaries written to {output_file}")
    if removed_feeds:
        logging.info(f"Removed {len(removed_feeds)} feed(s) due to lack of content")

if __name__ == "__main__":
    main()