<p align="center">
  <img src="MAi-RAG.png" alt="MAi-RAG-PA Personal Assistant" width="150">
</p>

<h1 align="center">MAi-RAG-PA</h1>
<h3 align="center">Your Offline Privacy, Self-Healing, Personal Assistant</h3>

<p align="center">
  <strong>MAi-RAG-PA (Memory-Augmented Intelligence with Retrieval-Augmented Generation - Personal Assistant)</strong> is a privacy-focused personal AI assistant that runs entirely on your local machine. No cloud. No subscriptions. No data leaving your computer.
</p>

<p align="center">
  <a href="README.md">Home</a> •
  <a href="MAi-README.md">Full Documentation</a> •
  <a href="MAi-INSTALLATION.md">Installation</a> •
  <a href="MAi-OLLAMA-MODELS.md">Models</a> •
  <a href="MAi-SSH-SETUP.md">SSH & LAN</a> •
  <a href="SELF-HEALING-SYSTEM-USER-WORKFLOW.md">Self-Healing System</a> •
  <a href="CHANGELOG.md">Changelog</a> •
  <a href="MAi-LICENCE-LEGAL-NOTICE.md">License</a>
</p>

<p align="center">
  <strong>Version 1.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

<h3 align="center">MAi-RAG-PA Model Recommendations</h3>

-----------------------------------------------------------------------------------

MAi-RAG-PA is **completely model-agnostic**. You can use any model available in Ollama. However, because MAi-RAG-PA relies heavily on **tool-calling, JSON formatting, and agentic workflows**, we recommend models with strong instruction-following and function-calling capabilities.

## Understanding Model Types

### Dense Models (Non-MoE)

**Dense models use all their parameters for every token. They are:**
- Highly consistent
- Reliable for complex logic
- Generally the safest choice for agentic workflows
- Require more RAM for larger models

### MoE Models (Mixture of Experts)

**MoE models only activate a fraction of their total parameters per token. This allows them to:**
- Achieve "large model" intelligence on "small model" hardware
- Run faster than dense models of equivalent total size
- Excellent for high-end agentic tasks on consumer hardware
- May be less consistent than dense models for some tasks

-----------------------------------------------------------------------------------

## Non-MoE (Dense) Models

| Model | Ollama Command | Active Params | Min System RAM | Best Use Case / Notes |
|-------|----------------|---------------|----------------|----------------------|
| **Qwen 2.5 Coder 1.5B** | `ollama pull qwen2.5-coder:1.5b` | 1.5B | 2 GB+ | **Micro-Size** Ultra-low-end PCs. Surprisingly capable for its size. Fast, but may struggle with highly complex, multi-step reasoning. |
| **Qwen 2.5 Coder 7B** | `ollama pull qwen2.5-coder:7b` | 7B | 6 GB+ | **The Sweet Spot.** Best balance of speed and capability. Highly recommended for everyday coding, file generation, and tool-calling. |
| **Qwen 2.5 Coder 14B** | `ollama pull qwen2.5-coder:14b` | 14B | 10 GB+ | **Top-Tier Coding.** Ideal for generating full applications, complex debugging, & long document synthesis. Excellent tool-calling. |
| **Qwen 2.5 Coder 32B** | `ollama pull qwen2.5-coder:32b` | 32B | 20 GB+ | **Heavy Lifter.** Exceptional for complex code generation and architectural planning. Requires 20GB+ RAM. |
| **Llama 3.2 3B** | `ollama pull llama3.2:3b` | 3B | 3 GB+ | **Ultra-Low End.** Great for older hardware, Raspberry Pi, or quick, simple chat and basic tool calls. |
| **Llama 3.3 70B** | `ollama pull llama3.3:70b` | 70B | 42 GB+ | **Maximum Intelligence.** Meta's latest flagship. Best for complex architectural planning, deep reasoning, and heavy agentic loops. |
| **Mistral Nemo 12B** | `ollama pull mistral-nemo:12b` | 12B | 9 GB+ | **The All-Rounder.** Exceptional reasoning & instruction following. Slightly slower than 7B but more reliable on complex tasks. |
| **Gemma 3 27B** | `ollama pull gemma3:27b` | 27B | 18 GB+ | **Google's Powerhouse.** Excellent at nuanced language, summarization, and general knowledge retrieval. |

-----------------------------------------------------------------------------------

## MoE (Mixture of Experts) Models

| Model | Ollama Command | Active / Total Params | Min System RAM | Best Use Case / Notes |
|-------|----------------|----------------------|----------------|----------------------|
| **Granite 3.1 MoE 3B** | `ollama pull granite3.1-moe:3b` | 1B / 3B | 4 GB+ | **Low-Latency Edge.** IBM's smallest MoE. Extremely fast, low latency, great for simple tool routing on weak hardware. |
| **Granite 3.3 8B** | `ollama pull granite3.3:8b` | 1B / 8B | 4 GB+ | **Enhanced Edge.** Similar to 3.1 MoE but with larger parameters. Fine-tuned for reasoning, supports tools. |
| **LFM2.5 8B-A1B** | `ollama pull lfm2.5:8b-a1b` | 1B / 8B | 4 GB+ | **Edge Tool-Calling.** Built for fast tool calling on consumer hardware. |
| **Qwen 3 30B-A3B** | `ollama pull qwen3:30b-a3b` | 3B / 30B | 20 GB+ | **Agentic King.** Only uses 3B active params, but has 30B total knowledge. Incredible tool-calling and MCP compliance. |
| **Qwen 3.6 35B-A3B** | `ollama pull qwen3.6:35b-a3b` | 3B / 35B | 20 GB+ | **Best for Agentic Coding.** 37% MCPMark, 73.4% SWE-Bench. State-of-the-art for code generation. |
| **Qwen 2.5 MoE 57B** | `ollama pull qwen2.5-moe:57b-a14b` | 14B / 57B | 32 GB+ | **The Reliable MoE.** Excellent coding and math capabilities. Very stable for long agentic loops. |
| **Qwen 3 235B-A22B** | `ollama pull qwen3:235b-a22b` | 22B / 235B | 128 GB+ | **Enterprise MoE.** Massive intelligence rivaling GPT-4, but only uses 22B active params. Requires high-end workstation. |
| **Gemma 4 31B-A4B** | `ollama pull gemma4:31b-a4b` | 4B / 31B | 20 GB+ | **Google's MoE.** Strong tool calling and reasoning. |
| **Nemotron-3-Super** | `ollama pull nemotron-3-super` | 12B / 120B | 64 GB+ | **1M Context.** 50% faster token generation, multi-agent optimized. |
| **DeepSeek R1 671B** | `ollama pull deepseek-r1:671b` | 37B / 671B | 400 GB+ | **Deep Reasoning.** The ultimate reasoning model. *Requires multi-GPU server or Mac Studio Ultra.* |


-----------------------------------------------------------------------------------

## Protected System Models

MAi-RAG-PA designates certain models as Protected System Models.
These are automatically installed during setup and are critical for optimal system performance.

**codeqwen:7b (Protected)**

**Purpose: Core system functionality**
- STM (Short-Term Memory) parsing fallback when regex fails
- Self-healing operations
- Basic chat and file creation
- Text-to-SQL queries

**Why It's Protected:**
- Optimized for consumer hardware (8-12GB RAM)
- Fast response times (~4.5GB RAM requirement)
- Reliable for system operations
- Ensures core features work even if primary model fails

**Installation:**
Automatically installed during setup:

**Warning System:**
If codeqwen:7b is missing, MAi-RAG-PA displays a warning in the WebUI under the model selector:

**codeqwen:7b is not installed. Optimized for consumer hardware. Required for optimal system performance.**


## Can I Remove It?

**Yes, but:**

- STM parsing will be slower (regex-only fallback)
- Self-healing may not work optimally
- Basic chat will use your primary model (slower on low-end hardware)
- System will show persistent warnings

**Recommendation: Keep it installed unless you're critically low on disk space.**

-----------------------------------------------------------------------------------

## Self-Healing System Requirements

MAi-RAG-PA includes a self-healing capability that allows capable AI models to fix their own code in a safe sandbox environment.
Not all models support this feature/capability.

### Self-Healing Capable Models

**Dense Models:**
- Qwen 2.5 Coder 32B
- Qwen 2.5 Coder 14B
- CodeQwen 7B
- Devstral 24B
- Mistral Small 24B
- Qwen3 Coder 30B
- Gemma 3 27B

**MoE Models:**

- Qwen 3 235B-A22B
- Qwen 3 30B-A3B
- Qwen 3.6 35B-A3B
- Mixtral 8x7B
- Mixtral 8x22B
- DeepSeek V2

**How Self-Healing Works**

- System detects errors or receives fix requests
- Capable AI models analyze the issue
- Code modifications made in isolated sandbox (~/MAi-RAG-PA/dev-sandbox/MAi-RAG-DEV/)
- User reviews changes before deployment
- Instant rollback if issues arise

**Safety Features**

- Isolated sandbox prevents damage to main codebase
- Path validation prevents infinite loops
- File operation limits (max 50 files, 10 depth levels)
- User approval required for all changes
- Instant revert capability

**Note: If your model is not in the self-healing capable list, the self-healing protocol will not be injected into the system prompt, and the feature will be disabled.**

## Hardware-Aware Auto-Detection

MAi-RAG-PA automatically detects your hardware and recommends appropriate settings.

### Hardware Tiers

**High-End (32GB+ RAM, 8+ CPU Cores):**
- Recommended: Qwen3-235B-A22B (MoE), Mixtral-8x22B
- num_predict: 16384
- Context length: 8192
- Max concurrent requests: 3

**Mid-Range (16GB RAM, 4+ CPU Cores):**
- Recommended: Qwen3-30B-A3B (MoE), Qwen2.5-Coder-14B
- num_predict: 8192
- Context length: 4096
- Max concurrent requests: 2

**Consumer (8-12GB RAM, 2-4 CPU Cores):**
- Recommended: Qwen2.5-Coder-7B, CodeQwen-7B
- num_predict: 4096
- Context length: 2048
- Max concurrent requests: 1

**Minimal (<8GB RAM, 1-2 CPU Cores):**
- Recommended: Qwen2.5-3B, Phi-3-mini
- num_predict: 2048
- Context length: 1024
- Max concurrent requests: 1

**Check Your Hardware:**

    curl http://localhost:8000/api/system/hardware -H "X-API-Key: YOUR_KEY"

**Manual API Key Retrieval:**
    curl http://localhost:8000/api/auth/auto-key

-----------------------------------------------------------------------------------

# How to Choose the Right Model
**(FOR Tool Calling Models capable of Knowledge Base Integration)**

## How to Check Tool Calling Support:

**IMPORTANT Before pulling any model, verify it supports tool calling:**

    ollama run qwen2.5-coder:7b "List 3 tools you can call"


### For General Daily Use (Chat, Notes, Simple Tasks)

**Recommended:** qwen2.5-coder:7b   qwen2.5:7b  mistral-nemo:12b   phi4:14b

**Why:**
- Fast and responsive even on modest hardware
- Strong and reliable tool-calling performance
- Handles MAi-RAG-PA structured outputs and function calling well
- Good balance of speed and capability
- Works effectively on 8GB–16GB RAM systems

**Installation:**

    ollama pull qwen2.5-coder:7b
    ollama pull qwen2.5:7b
	ollama pull mistral-nemo:12b
	ollama pull phi4:14b


### For Creative Writing, Heavy Coding & File Generation

**Best tool-calling models Recommended:** Qwen2.5-Coder 14B / 32B, Qwen2.5 32B, Qwen 3 30B-A3B, or Command-R-Plus

**Why:**
- Excellent tool-calling & code generation reliability (critical for file generation and agent workflows)
- Strong at complex multi-step file creation tasks and structured outputs
- Good context understanding when using tools
- More consistent than most fine-tunes when function calling is required

**Installation:**

**Dense model (more consistent):**

    ollama pull qwen2.5-coder:7b
    ollama pull qwen2.5-coder:14b
    ollama pull qwen2.5-coder:32b
    ollama pull qwen2.5:32b
    ollama pull qwen2.5:72b			# 72B Best open-weight prose. Nuanced, literary, avoids clichés
    ollama pull command-r-plus		# 104B Best for long-form (novels, essays). Huge context
    ollama pull llama3.1-8B			# 8B lightweight
    ollama pull llama3.1:70b		# 70B Reliable, great tone control, huge community
    ollama pull gemma2:27b
    ollama pull codestral:22B

**OR  Qwen 3 30B-A3B MoE model (faster if you have RAM):**

    ollama pull qwen3:30b-a3b		# MoE Model, Well rounded fast responses if you have RAM

**Others**

    ollama pull qwen3-*				# All variants
    ollama pull deepseek-r1-*		# All variants
    ollama pull deepSeek-coder-v2*	# All variants

## Best Combo Picks (Writing + Code)

| Your RAM | Writing	Coding | Both |
| 8GB | llama3.1:8b	qwen2.5-coder:3b | phi4:14b |
| 16GB | qwen2.5:32b (Q4) | qwen2.5-coder:7b | qwen2.5:32b |
| 24GB | qwen2.5:32b | qwen2.5-coder:32b | qwen2.5:32b  |
| 32GB+ | qwen2.5:72b | qwen2.5-coder:32b | qwen2.5:72b |
| 64GB+/Mac Ultra | midnightmiqu:70b | deepseek-r1:70b | command-r-plus |

### Recommendations by Hardware:

| Your Hardware | Best Coding Model | Best Writing Model | Best All-Rounder |
| 16 GB RAM	qwen2.5-coder:7b | qwen2.5:7b | qwen2.5:7b |
|24–32 GB RAM | qwen2.5-coder:14b / 32b | qwen2.5:32b | qwen2.5:32b |
|40–48 GB RAM | qwen2.5-coder:32b | qwen2.5:32b / 72b | qwen2.5:32b |
|64+ GB RAM | deepseek-coder-v2:236b | qwen2.5:72b | qwen2.5:72b|

### Quick Recommendation
| You want... | Run this |
| Best writing | ollama pull qwen2.5:72b |
| Best coding | ollama pull qwen2.5-coder:32b |
| Best both (limited RAM) | ollama pull qwen2.5:32b |
| Best fiction/RP | ollama pull midnightmiqu:70b |
| Best complex reasoning | ollama pull deepseek-r1:70b |
| Best on laptop (8GB) | ollama pull phi4:14b |
| Best free/tiny | ollama pull qwen2.5-coder:3b |

**To install a model open a terminal and type: ollama pull modelnamehere**
*Replace "modelnamehere" with the full modelname and size: qwen2.5:7b


### For Complex Agentic Workflows (Multi-step tool calling, RAG, Planning)

**Recommended:** Llama 3.3 70B or Qwen 3 235B-A22B

**Why:**
- Rarely hallucinates tool calls
- Follows strict JSON schemas flawlessly
- Handles complex multi-step reasoning
- Excellent for long agentic loops

**Installation:**

**If you have 48GB+ RAM:**

    ollama pull llama3.3:70b

**If you have 128GB+ RAM:**

    ollama pull qwen3:235b-a22b

-----------------------------------------------------------------------------------

### For Low-End Hardware (4GB - 12GB RAM)

**Recommended:** Qwen 2.5 Coder 1.5B, Llama 3.2 3B, Granite 3.1 MoE 3B, or Granite 3.3 8B

**Why:**
- Keep MAi-RAG-PA UI responsive
- Handle basic memory tasks
- Work on older hardware
- Fast inference times

**Installation:**

**Smallest option:**

    ollama pull qwen2.5-coder:1.5b

**OR slightly better:**

    ollama pull llama3.2:3b

**OR MoE option:**

    ollama pull granite3.1-moe:3b

| Model	Size | Notes |
| qwen2.5-coder:1.5b | 1.5b | Tiny, Performs ok for its size |
| qwen2.5-coder:3b | 3B | Best tiny coder for quick scripts |
| qwen2.5:7b | 7B | Good balance of speed and tool use |
| llama3.2:3b | 3B | Lightweight with basic tool support |
| deepseek-r1-6.7b | 6.7B | Older but still solid |
| codegemma:7B | 7B | Google's coder, good for Python |

-----------------------------------------------------------------------------------

## Understanding RAM Requirements

**Important Notes**

**"Min System RAM" assumes:**
- Running the model at default Ollama 4-bit quantization (Q4_K_M)
- No other major applications running
- Linux/macOS operating system

**If you use 8-bit quantization:**
- Double the RAM requirement
- Better quality but slower

**Always leave 2-4GB of RAM free for:**
- Your operating system
- MAi-RAG-PA backend (FastAPI, Qdrant)
- Browser and other applications

---

## GPU Acceleration

**If you have a dedicated NVIDIA GPU:**
- VRAM is the limiting factor instead of System RAM
- A 32B model requires ~20GB of VRAM to run entirely on GPU
- GPU inference is significantly faster than CPU
- Ollama automatically uses GPU if available

**Check your GPU VRAM:**

    nvidia-smi

-----------------------------------------------------------------------------------

## RAM Usage Examples

| System RAM | Recommended Models | Notes |
|------------|-------------------|-------|
| 8 GB | 1.5B, 3B, 7B | Leave 2-3GB free for OS |
| 12 GB | 3B, 7B, 12B | Can run 7B comfortably |
| 16 GB | 7B, 12B, 14B | Sweet spot for most users |
| 20 GB | 14B, 32B, MoE 30B | Can run larger models |
| 32 GB | 32B, MoE 57B | Good for heavy workloads |
| 42 GB+ | 70B | Maximum dense models |
| 64 GB+ | MoE 120B | Enterprise-grade |
| 128 GB+ | MoE 235B | Ultimate performance |

-----------------------------------------------------------------------------------

## Switching Models in MAi-RAG-PA

**Via Web UI:**
- Open MAi-RAG-PA in your browser
- Go to Chat Console
- Click the Model Selector dropdown
- Select your desired model
- (Optional) Check "Set as default" to make it permanent

**Via Command Line:**

**List available models:**

    ollama list

**Pull a new model:**

    ollama pull qwen2.5-coder:14b

**Remove a model:**

    ollama rm qwen2.5-coder:7b

### Hot-Swapping

**You can switch models mid-conversation without restarting MAi-RAG-PA:**
1. Start a conversation with one model
2. Change the model in the dropdown
3. Continue the conversation with the new model

**Note: The new model won't have context from the previous model's responses.**

-----------------------------------------------------------------------------------

## Performance Expectations

**CPU-Only Systems (Intel i3-1215U example)**

| Model | Tokens/Second | Response Time (100 tokens) |
|-------|---------------|---------------------------|
| 1.5B | 20-30 | 3-5 seconds |
| 3B | 15-25 | 4-7 seconds |
| 7B | 8-15 | 7-12 seconds |
| 14B | 4-8 | 12-25 seconds |
| 32B | 2-5 | 20-50 seconds |

**GPU-Accelerated Systems (RTX 3060 example)**

| Model | Tokens/Second | Response Time (100 tokens) |
|-------|---------------|---------------------------|
| 7B | 50-80 | 1-2 seconds |
| 14B | 30-50 | 2-3 seconds |
| 32B | 15-25 | 4-7 seconds |

**Note: Performance varies based on:**
- CPU/GPU model
- RAM speed
- System load
- Model quantization
- Context length

-----------------------------------------------------------------------------------

## Troubleshooting Model Issues

### Model Not Appearing in Dropdown

**Check if Ollama is running:**

    curl http://localhost:11434/api/tags

**Pull the model:**

    ollama pull qwen2.5-coder:7b

**Restart MAi-RAG-PA:**

    cd ~/MAi-RAG-PA
    ./stop.sh
    ./start.sh

### Out of Memory Errors

**Symptoms:**
- Model fails to load
- System becomes unresponsive
- Ollama crashes

**Solutions:**
1. Use a smaller model
2. Close other applications
3. Increase swap space (Linux)
4. Upgrade RAM

### Slow Response Times

**Solutions:**
1. Use a smaller model (7B instead of 32B)
2. Reduce context window size in Ollama
3. Close RAM-intensive applications
4. Enable GPU acceleration if available

### Model Produces Poor Results

**Solutions:**
1. Try a different model
2. Adjust the system prompt in Assistant Settings
3. Provide more specific instructions
4. Use a model optimized for your task (coding vs. writing)

### Advanced: Custom Models

**You can use any model compatible with Ollama:**

1. **Create a Modelfile:**

    FROM ./path/to/your/model.bin
    PARAMETER temperature 0.7
    SYSTEM "You are a helpful assistant."

2. **Create the model:**

    ollama create my-custom-model -f Modelfile

3. **Use in MAi-RAG-PA:**
   Select "my-custom-model" from the dropdown menu in MAi-RAG-PA WebUI

### Quantization Options

**Ollama supports different quantization levels:**
- Q4_K_M (default): 4-bit, good balance of speed and quality
- Q5_K_M: 5-bit, better quality, slower
- Q8_0: 8-bit, best quality, slowest

**Specify quantization:**

    ollama pull qwen2.5-coder:7b-q5_k_m

### Getting Help

**Model Recommendations:**
- [Check Ollama Library](https://ollama.com/library)
- Review model benchmarks
- Test different models for your use case

**Performance Issues:**
- Run System Doctor from Assistant Settings
- Check system resources in Chat Console
- Review Ollama logs: `ollama logs`

**Community Support:**
- [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)
- [Ollama Discord](https://discord.gg/ollama)

-----------------------------------------------------------------------------------

## Documentation

<a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
<a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
<a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
<a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
<a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

## Support & Contact

**Issues**: [GitHub Issues](https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues)
**Discussions**: [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)
**Email**: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

## Documentation

<a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
<a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
<a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
<a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
<a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

## Support & Contact

**Issues**: [GitHub Issues](https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues)
**Discussions**: [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)
**Email**: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

## 💝 Support MAi-RAG-PA

MAi-RAG-PA is a labor of love developed over thousands of hours. If this software brings value to your life or work, **donations are deeply appreciated** and help fund continued development.

MAi-RAG-PA is free for personal use. If you find it valuable, donations are greatly appreciated:

- **PayPal**: <a href="https://www.paypal.com/ncp/payment/GSTCK29MSGCH4">Grateful for your Contributions</a>

Every donation helps keep MAi-RAG-PA free and continuously improving.

**Commercial Licensing**: For business deployments or enterprise support, please contact: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

<p align="center">
  <strong>MAi-RAG-PA — Your Personal Assistant, Your Data, Your Machine, No Subscriptions!</strong>
</p>

<p align="center">
  Version 1.0.0 | Released June 2026
</p>
