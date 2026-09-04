# General Setup Guide

This guide covers the basic setup for esp32-flashcards project.

## Requirements

- Python 3.8 or higher
- pip (Python package manager)
- Git
- ESP32 microcontroller with SD card slot
- USB cable for ESP32 (for Arduino IDE upload)
- EPUB files to extract from
- Optionally: Ollama instance (see OLLAMA_SETUP.md)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/silasmaynord/esp32-flashcards.git
cd esp32-flashcards
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Dependencies include:
- `ebooklib` - EPUB parsing
- `beautifulsoup4` - HTML parsing
- `lxml` - XML processing
- `pyyaml` - Configuration files
- `pandas` - Data processing
- `requests` - HTTP requests for Ollama
- `loguru` - Logging
- `click` - CLI support

### 4. (Optional) Set Up Ollama

For LLM-powered enhancement of flashcards:

```bash
# See docs/OLLAMA_SETUP.md for detailed instructions
# Quick setup:
# 1. Install Ollama: https://ollama.ai
# 2. Pull a model: ollama pull mistral
# 3. Copy and edit config: cp llm/config.example.yml llm/config.yml
```

## Quick Start

### 1. Extract Flashcards from EPUB

```bash
python3 extraction/flashcard_generator.py your_book.epub output_cards.json mixed
```

Options:
- `your_book.epub` - Path to your EPUB file
- `output_cards.json` - Where to save the generated flashcards
- `mixed` - Generation strategy (options: `definition`, `summary`, `qa`, `mixed`)

### 2. (Optional) Enhance with Ollama

```bash
python3 -c "
import json
from llm.ollama_client import OllamaClient

client = OllamaClient(config_path='llm/config.yml')

with open('output_cards.json') as f:
    data = json.load(f)

enhanced = client.batch_enhance(data['flashcards'], batch_size=5)

with open('output_cards_enhanced.json', 'w') as f:
    json.dump({'flashcards': enhanced}, f, indent=2)
"
```

### 3. Prepare for ESP32

```bash
# Compress the JSON file for SD card
gzip output_cards.json

# Copy to SD card
# The file should be at: /flashcards/cards.json.gz (on SD card)
```

### 4. Upload to ESP32

See `esp32/flashcard_reader.ino` for the Arduino sketch:

1. Install Arduino IDE
2. Install ESP32 board support
3. Open `esp32/flashcard_reader.ino`
4. Configure for your ESP32 board
5. Upload sketch to device

## Project Structure

```
esp32-flashcards/
├── extraction/           # EPUB parsing and card generation
│   ├── epub_parser.py
│   ├── flashcard_generator.py
│   └── templates/
├── llm/                  # LLM integration
│   ├── ollama_client.py
│   ├── prompt_templates.py
│   └── config.example.yml
├── esp32/                # ESP32 firmware
│   ├── flashcard_reader.ino
│   └── sd_utils.h
├── data/                 # Sample outputs
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
└── README.md
```

## Common Tasks

### Process Multiple EPUBs

```bash
for epub in books/*.epub; do
  echo "Processing $epub..."
  python3 extraction/flashcard_generator.py "$epub" "output/$(basename $epub .epub).json" mixed
done
```

### Batch Enhance Cards

```bash
python3 -c "
import json
import glob
from llm.ollama_client import OllamaClient

client = OllamaClient(config_path='llm/config.yml')

for json_file in glob.glob('output/*.json'):
    print(f'Enhancing {json_file}...')
    with open(json_file) as f:
        data = json.load(f)
    
    enhanced = client.batch_enhance(data['flashcards'], batch_size=5)
    
    output_file = json_file.replace('.json', '_enhanced.json')
    with open(output_file, 'w') as f:
        json.dump({'flashcards': enhanced}, f, indent=2)
    
    print(f'Saved to {output_file}')
"
```

### Extract Statistics

```bash
python3 -c "
import json
from pathlib import Path

for json_file in Path('output').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
    
    cards = data.get('flashcards', [])
    print(f'{json_file.name}:')
    print(f'  Total cards: {len(cards)}')
    print(f'  Avg question length: {sum(len(c[\"question\"]) for c in cards) // len(cards)}')
    print()
"
```

## Configuration

### Ollama Configuration

See `llm/config.example.yml` for all options:

```yaml
ollama:
  host: http://localhost:11434
  model: mistral
  timeout: 300
  temperature: 0.7
  top_p: 0.9

enhancement:
  enabled: true
  batch_size: 5
  assess_difficulty: true
```

## Troubleshooting

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Ollama Connection Error

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### EPUB Parsing Errors

```bash
# Some EPUBs may have encoding issues
# Try converting with Calibre or similar tool
```

### Memory Issues

```bash
# If processing large books, process in chunks
# Modify flashcard_generator.py to limit items processed
```

## Next Steps

1. **Process Your Books**: Extract flashcards from your EPUB collection
2. **Enhance Quality**: Use Ollama to improve card clarity and accuracy
3. **Deploy to ESP32**: Follow esp32/README.md for device setup
4. **Customize**: Adjust prompts and settings in llm/prompt_templates.py
5. **Contribute**: Submit improvements and new features!

## Support

For issues, questions, or suggestions:
- Check existing GitHub issues
- Open a new issue with details
- See README.md for more information

## License

MIT License - See LICENSE file
