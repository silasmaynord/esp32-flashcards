# Ollama Setup Guide for Proxmox LXC

This guide explains how to set up Ollama in a Proxmox LXC container and configure it for use with esp32-flashcards.

## Prerequisites

- Proxmox VE host with LXC container support
- 16GB+ RAM available (8GB minimum for smaller models)
- Sufficient disk space (20GB+ for models)
- Optional: GPU support (NVIDIA/AMD) for faster inference

## Step 1: Create an LXC Container

### Option A: Via Proxmox UI

1. Go to Proxmox Web Interface → Datacenter → Create CT
2. Choose a Linux template (Ubuntu 22.04 LTS recommended)
3. Allocate resources:
   - **Cores**: 4-8
   - **RAM**: 8-16 GB
   - **Storage**: 30-50 GB (depends on models)
4. Complete creation and start the container

### Option B: Via Command Line

```bash
# SSH into Proxmox host
ssh root@proxmox-host

# Create container
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

pct create 100 \
  local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname ollama-lxc \
  --cores 4 \
  --memory 8192 \
  --swap 2048 \
  --storage local \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp

# Start container
pct start 100
```

## Step 2: Install Ollama in the Container

### Enter the Container

```bash
# From Proxmox host
pct shell 100

# OR SSH into container (after getting its IP)
ssh root@<container-ip>
```

### Install Dependencies

```bash
apt update
apt install -y curl wget git build-essential
```

### Install Ollama

```bash
# Download and install Ollama
curl https://ollama.ai/install.sh | sh

# Verify installation
ollama --version
```

### Start Ollama Service

```bash
# Start ollama as a service
systemctl start ollama
systemctl enable ollama

# Verify it's running
systemctl status ollama

# Check if API is responding
curl http://localhost:11434/api/tags
```

## Step 3: Download Models

### Pull Models into Ollama

```bash
# Download Mistral (recommended for flashcards - smaller, faster)
ollama pull mistral

# OR download Llama 2 (larger, more capable)
ollama pull llama2

# OR download Neural Chat (optimized for conversations)
ollama pull neural-chat

# List available models
ollama list
```

Model recommendations for flashcard generation:
- **Mistral**: Fast, efficient, good for Q&A (7B params)
- **Neural Chat**: Optimized for conversations, good quality (7B params)
- **Llama 2**: More capable but slower (7B or 13B params)

## Step 4: Install OpenWebUI (Optional but Recommended)

OpenWebUI provides a web interface for managing models and testing prompts.

### Option A: In Same Container

```bash
# Install Docker (if not already installed)
apt install -y docker.io docker-compose

# Start Docker
systemctl start docker
systemctl enable docker

# Pull and run OpenWebUI
docker pull ghcr.io/open-webui/open-webui:latest

docker run -d \
  --name open-webui \
  -p 8080:8080 \
  --network host \
  ghcr.io/open-webui/open-webui:latest

# Access at http://<container-ip>:8080
```

### Option B: Separate Container (Recommended)

Create another LXC container and follow the same docker installation, then run OpenWebUI pointing to the Ollama container.

```bash
docker run -d \
  --name open-webui \
  -p 8080:8080 \
  -e OLLAMA_BASE_URL=http://<ollama-container-ip>:11434 \
  ghcr.io/open-webui/open-webui:latest
```

## Step 5: Configure for esp32-flashcards

### Set Up Python Environment (on Host or Another Container)

```bash
# Clone the repository
git clone https://github.com/silasmaynord/esp32-flashcards.git
cd esp32-flashcards

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Create Configuration File

```bash
# Copy and edit the example config
cp llm/config.example.yml llm/config.yml

# Edit with your container's IP
nano llm/config.yml
```

Update these fields:
```yaml
ollama:
  host: http://<ollama-container-ip>:11434
  model: mistral  # or your chosen model
  timeout: 300
```

Find container IP:
```bash
# From Proxmox host
pct exec 100 hostname -I
```

## Step 6: Test the Setup

### Test Ollama Connection

```bash
python3 -c "
from llm.ollama_client import OllamaClient
client = OllamaClient()
print('Connected successfully!')
print(f'Available models: {client.get_available_models()}')

# Test generation
response = client.generate('What is photosynthesis?')
print(f'\nTest response: {response[:200]}...')
"
```

### Test Card Enhancement

```bash
python3 -c "
from llm.ollama_client import OllamaClient
client = OllamaClient()

q = 'What is photosynthesis?'
a = 'Process where plants make energy from sunlight.'

q_enhanced, a_enhanced = client.enhance_flashcard(q, a)

print(f'Original Q: {q}')
print(f'Enhanced Q: {q_enhanced}')
print(f'\nOriginal A: {a}')
print(f'Enhanced A: {a_enhanced}')
"
```

## Step 7: Full Workflow Example

```bash
cd esp32-flashcards

# 1. Extract content from EPUB
python3 extraction/flashcard_generator.py your_book.epub output/cards.json mixed

# 2. Enhance with LLM (optional)
python3 -c "
import json
from llm.ollama_client import OllamaClient

client = OllamaClient(config_path='llm/config.yml')

with open('output/cards.json') as f:
    data = json.load(f)

# Enhance first 10 cards
enhanced = client.batch_enhance(data['flashcards'][:10], batch_size=5)

with open('output/cards_enhanced.json', 'w') as f:
    json.dump({'flashcards': enhanced}, f, indent=2)
"

# 3. Prepare for ESP32 (compress)
gzip output/cards.json

# 4. Copy to SD card
cp output/cards.json.gz /path/to/sd/flashcards/
```

## Troubleshooting

### Ollama not responding

```bash
# Check if service is running
systemctl status ollama

# Restart service
systemctl restart ollama

# Check logs
journalctl -u ollama -n 50
```

### Out of memory errors

```bash
# Reduce model size or increase container RAM
# Download a smaller model
ollama pull mistral

# Or increase LXC memory allocation from Proxmox UI
```

### Container can't reach Ollama

```bash
# Verify container's network
pct exec 100 hostname -I

# Test connection from host
curl http://<container-ip>:11434/api/tags

# Test from container
pct exec 100 curl http://localhost:11434/api/tags
```

### Models not visible

```bash
# List models
pct exec 100 ollama list

# Pull a model if needed
pct exec 100 ollama pull mistral
```

## Performance Tuning

### For Faster Inference

1. **Increase container resources**:
   - More CPU cores (8-16 recommended)
   - More RAM (16GB+ recommended)

2. **Use smaller models**:
   - Mistral (7B) - fastest
   - Neural Chat (7B)
   - Avoid Llama2 13B unless you have resources

3. **Enable GPU** (if available):
   - Requires NVIDIA GPU and proper drivers
   - Proxmox GPU passthrough setup
   - See [Ollama GPU Docs](https://github.com/ollama/ollama/blob/main/docs/gpu.md)

### For Better Quality

1. Use larger models (Llama2 13B)
2. Lower temperature for consistency (0.3-0.5)
3. Add more few-shot examples in prompts

## Security Considerations

```bash
# If exposing Ollama externally, use authentication
# Option 1: Firewall (recommended)
# Only allow access from trusted networks

# Option 2: Reverse proxy with auth
# Set up nginx with authentication
```

## Monitoring

```bash
# Monitor Ollama performance
pct exec 100 watch -n 1 'free -h && ps aux | grep ollama'

# Monitor via OpenWebUI dashboard
# Visit http://<container-ip>:8080
```

## Next Steps

1. Test with your EPUBs: see `docs/USAGE.md`
2. Adjust prompt templates in `llm/prompt_templates.py`
3. Fine-tune model selection and parameters
4. Scale to process multiple books

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [OpenWebUI GitHub](https://github.com/open-webui/open-webui)
- [Proxmox LXC Documentation](https://pve.proxmox.com/wiki/Linux_Container)
- [LLM Model Comparison](https://huggingface.co/models?pipeline_tag=text-generation&sort=downloads)
