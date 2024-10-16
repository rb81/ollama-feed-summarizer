# Ollama Feed Summarizer

![Feed Summarizer](/header.png)

Ollama Feed Summarizer is a Python application that loops through multiple RSS feeds, summarizing articles using a model running locally using [Ollama](https://github.com/ollama/ollama), and stores the summaries in a daily summary file for easy reading.

> Check out [Feed Summarizer](https://github.com/rb81/feed-summarizer) for a more powerful version that uses Claude for summarization, and a GitHub repository for storage.

## Features

- Fetches articles from multiple RSS feeds
- Summarizes articles using AI (Ollama)
- Compiles summaries into a single markdown file
- Handles unavailable feeds and updates the feed list
- Configurable via JSON file
- Outputs summaries with a date-stamped heading
- **NEW**: Converts summaries to audio using Text-to-Speech (TTS) with [OpenedAI Speech](https://github.com/matatonic/openedai-speech.git). (This script assumes that you have a local instance of OpenedAI Speech running.)

## Requirements

- Python 3.7+
- [Ollama](https://ollama.com/) installed and running locally
- [OpenedAI Speech](https://github.com/matatonic/openedai-speech.git) for TTS functionality

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/rb81/ollama-feed-summarizer.git
   cd ollama-feed-summarizer
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `config.json` file in the project directory with the following structure:
   ```json
   {
       "feeds_file": "feeds.txt",
       "removed_feeds_file": "removed_feeds.txt",
       "output_folder": "/path/to/your/output/folder",
       "num_articles": 5,
       "ollama_model": "llama3.2:3b",
       "ollama_ip": "localhost",
       "ollama_port": "11434",
       "text_to_speech": {
           "enabled": true,
           "endpoint_url": "http://localhost:8000/v1/audio/speech",
           "model": "tts-1",
           "voice": "alloy",
           "response_format": "mp3",
           "speed": 1.0
       }
   }
   ```

4. Create a `feeds.txt` file with one RSS feed URL per line.

## Usage

Run the script with:

```
python main.py
```

The script will:

1. Read RSS feeds from `feeds.txt`
2. Fetch and summarize the specified number of articles from each feed
3. Compile summaries into a markdown file in the specified output folder
4. Update `feeds.txt` and `removed_feeds.txt` if any feeds are unavailable or do not contain any content
5. **NEW**: Generate an audio summary of the articles if TTS is enabled

## Output

The script generates a markdown file named `YYYY-MM-DD_feed-summaries.md` in the specified output folder. The file contains:

- A heading with the current date (e.g., "News for Tuesday, January 1, 2024")
- Summaries of articles from the processed feeds
- **NEW**: A link to the audio summary if TTS is enabled

## Configuration

Adjust the `config.json` file to change:

- Input and output file locations
- Number of articles to summarize per feed
- Ollama model and connection details
- **NEW**: TTS settings such as model, voice, and speed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Transparency Disclaimer

[ai.collaboratedwith.me](https://ai.collaboratedwith.me) in creating this project.
