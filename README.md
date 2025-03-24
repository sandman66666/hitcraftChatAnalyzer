# HitCraft Chat Analyzer

A web application that uses Claude AI to analyze chat logs from the HitCraft product and generate actionable insights for the product team.

## Features

- Upload and process large chat log files (TXT or RTF format)
- Automatically split large files into Claude-compatible chunks
- Analyze conversations using Claude AI
- Generate insights about:
  - Conversation categories
  - Top discussion topics
  - Response quality
  - Areas for improvement
  - User satisfaction
  - Unmet user needs
  - Product effectiveness
- Present results in an organized, actionable format

## Requirements

- Python 3.8 or higher
- Claude API key from Anthropic

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd hitcraftChatAnalyzer
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Claude API key:
   
   - Option 1: Set as an environment variable:
     ```
     export CLAUDE_API_KEY=your_api_key_here  # On Windows: set CLAUDE_API_KEY=your_api_key_here
     ```
   
   - Option 2: Enter it directly in the web interface when prompted

## Running the Application

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. Follow the on-screen instructions to upload and analyze your chat logs.

## How to Use

1. **Upload Chat Logs**:
   - Click the "Choose File" button and select your chat log file (.txt or .rtf)
   - Large files will be automatically chunked for processing

2. **Provide Claude API Key**:
   - Enter your Claude API key in the designated field
   - This key is used for analysis but is not stored on the server

3. **Analyze Chats**:
   - Click the "Analyze Chats" button to begin processing
   - The system will upload your file, chunk it if necessary, and send it to Claude for analysis
   - Progress will be displayed during the analysis

4. **Review Results**:
   - The analysis will be presented in several tabs:
     - **Overview**: Key insights and top discussion topics
     - **Categories**: Main categories of conversations
     - **Response Quality**: Examples of good responses and areas for improvement
     - **Improvements**: Suggested improvements and unmet user needs
     - **User Satisfaction**: Analysis of user satisfaction and engagement

## Getting a Claude API Key

To use this application, you'll need a Claude API key from Anthropic:

1. Visit [Anthropic's website](https://www.anthropic.com/)
2. Sign up for an account and request API access
3. Once approved, you can generate an API key from your dashboard
4. Use this key in the web application as described above

## File Format

The application expects chat logs in the following format:

```
========== THREAD: Thread Title ==========
ThreadId: unique-thread-id
Status: active/closed
Messages: count
Date Range: start-date to end-date

----- MESSAGES -----

[1] Role: user/assistant | Time: timestamp
UserId: user-id
Content Items: count
  Content #1 (type):
  "Message content here"

[2] Role: user/assistant | Time: timestamp
UserId: user-id
Content Items: count
  Content #1 (type):
  "Another message content here"

========== END THREAD ==========
```

A sample file is included in the `chats/` directory for reference.

## Interpreting the Results

The analysis results provide valuable insights for your product team:

- **Categories**: Shows what your users are primarily using the product for
- **Top Discussions**: Identifies the most common topics users are interested in
- **Response Quality**: Evaluates how well the assistant is addressing user needs
- **Improvement Areas**: Highlights specific features or responses that could be enhanced
- **User Satisfaction**: Gauges overall user experience and happiness with the product
- **Unmet Needs**: Identifies gaps in your product's capabilities
- **Product Effectiveness**: Assesses how well the product delivers on its promise

## Limitations

- The analysis quality depends on the Claude AI model being used
- Very large files may take longer to process
- The application currently only supports specific file formats (.txt and .rtf)

## License

This project is licensed under the MIT License - see the LICENSE file for details.