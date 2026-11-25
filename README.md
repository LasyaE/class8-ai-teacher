# Class 8 AI Teacher

## Purpose
A conversational AI assistant for 8th-grade students, providing subject-specific knowledge from curated textbooks.

## Supported Subjects
1. Mathematics
2. Science
3. Social Studies
4. English Language Arts
5. Computer Science
6. Environmental Studies
7. Physical Education

## Windows Setup Requirements
- Python 3.9+ (with virtual environment)
- Ollama 0.3.8+ (with Qwen3 model)
- SQLite for user storage

## Project Structure
- `webapp/` - Flask application
- `data/` - Textbook extracts and user data
- `tests/` - Security and functional tests

## Environment Variables
```ini
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:500a1f067a9f
```

## Startup Instructions
1. Activate the virtual environment:
   ```bash
   .\venv\Scripts\activate
   ``
2. Start Ollama:
   ```bash
   ollama serve
   ``
3. Run the application:
   ```bash
   python webapp/app.py
   ``

## User Management
- Register at `/register`
- Login at `/login`
- Logout at `/logout`

## Chat Usage
1. Select a subject
2. Ask questions about textbook content
3. View source document metadata

## Data Storage
- Textbooks: `data/extracted/raw/`
- Conversations: `data/users/{user_id}/`

## Running Tests
```bash
python -m pytest tests/test_security.py
python -m pytest tests/test_functional.py
```

## Common Errors
- `Ollama connection failed`: Ensure Ollama is running
- `No such file or directory`: Verify model exists in Ollama
- `Unauthorized`: Login required for chat functionality