# MAi-RAG Model Recommendations

MAi-RAG is **completely model-agnostic**. You can use any model available in Ollama. However, because MAi-RAG relies heavily on **tool-calling, JSON formatting, and agentic workflows**, we recommend models with strong instruction-following and function-calling capabilities.

-----------------------------------------------------------------------------------

## Understanding Model Types

### Dense Models (Non-MoE)

Dense models use **all their parameters for every token**. They are:

- ✅ Highly consistent
- ✅ Reliable for complex logic
- ✅ Generally the safest choice for agentic workflows
- ❌ Require more RAM for larger models

### MoE Models (Mixture of Experts)

MoE models only **activate a fraction of their total parameters per token**. This allows them to:

- ✅ Achieve "large model" intelligence on "small model" hardware
- ✅ Run faster than dense models of equivalent total size
- ✅ Excellent for high-end agentic tasks on consumer hardware
- ❌ May be less consistent than dense models for some tasks

-----------------------------------------------------------------------------------

### Non-MoE (Dense) Models

| Model 		  | Ollama Command 			| Active Params | Min System RAM | Best Use Case / Notes 
|-------------------------|-------------------------------------|---------------|----------------|-------------------------------------------------------------------------------------------------------------------------
| **Qwen 2.5 Coder 1.5B** | ollama pull qwen2.5-coder:1.5b	| 1.5B 		| 2 GB+ 	 | **Micro-Size** Ultra-low-end PCs. Surprisingly capable for its size. Fast, but may struggle with highly complex, multi-step reasoning.
| **Qwen 2.5 Coder 7B**   | ollama pull qwen2.5-coder:7b	| 7B 		| 6 GB+ 	 | **The Sweet Spot.** Best balance of speed and capability. Highly recommended for everyday coding, file generation, and tool-calling.
| **Qwen 2.5 Coder 14B**  | ollama pull qwen2.5-coder:14b	| 14B 		| 10 GB+ 	 | **Top-Tier Coding.** Ideal for generating full applications, complex debugging, & long document synthesis. Excellent tool-calling.
| **Qwen 2.5 Coder 32B**  | ollama pull qwen2.5-coder:32b	| 32B 		| 20 GB+ 	 | **Heavy Lifter.** Exceptional for complex code generation and architectural planning. Requires 20GB+ RAM.
| **Llama 3.2 3B** 	  | ollama pull llama3.2:3b		| 3B 		| 3 GB+ 	 | **Ultra-Low End.** Great for older hardware, Raspberry Pi, or quick, simple chat and basic tool calls.
| **Llama 3.3 70B** 	  | ollama pull llama3.3:70b		| 70B 		| 42 GB+ 	 | **Maximum Intelligence.** Meta's latest flagship. Best for complex architectural planning, deep reasoning, and heavy agentic loops.
| **Mistral Nemo 12B** 	  | ollama pull mistral-nemo:12b	| 12B 		| 9 GB+ 	 | **The All-Rounder.** Exceptional reasoning & instruction following. Slightly slower than 7B but more reliable on complex tasks.
| **Gemma 3 27B** 	  | ollama pull gemma3:27b		| 27B 		| 18 GB+ 	 | **Google's Powerhouse.** Excellent at nuanced language, summarization, and general knowledge retrieval.
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### MoE (Mixture of Experts) Models

| Model 		| Ollama Command 			| Active / Total Params | Min System RAM | Best Use Case / Notes |
|-----------------------|---------------------------------------|-----------------------|----------------|-----------------------------------------------------------------------------------------------------------------
| **Granite 3.1 MoE 3B**| ollama pull granite3.1-moe:3b 	| 1B / 3B 		| 4 GB+ 	 | **Low-Latency Edge.** IBM's smallest MoE. Extremely fast, low latency, great for simple tool routing on weak hardware.
| **Granite 3.3 8B** 	| ollama pull granite3.3:8b		| 1B / 8B 		| 4 GB+ 	 | **Enhanced Edge.** Similar to 3.1 MoE but with larger parameters. Fine-tuned for reasoning, supports tools.
| **LFM2.5 8B-A1B**	| ollama pull lfm2.5:8b-a1b 		| 1B / 8B		| 4 GB+ 	 | **Edge Tool-Calling.** Built for fast tool calling on consumer hardware.
| **Qwen 3 30B-A3B** 	| ollama pull qwen3:30b-a3b 		| 3B / 30B 		| 20 GB+ 	 | **Agentic King.** Only uses 3B active params, but has 30B total knowledge. Incredible tool-calling and MCP compliance.
| **Qwen 3.6 35B-A3B** 	| ollama pull qwen3.6:35b-a3b 		| 3B / 35B 		| 20 GB+ 	 | **Best for Agentic Coding.** 37% MCPMark, 73.4% SWE-Bench. State-of-the-art for code generation.
| **Qwen 2.5 MoE 57B** 	| ollama pull qwen2.5-moe:57b-a14b 	| 14B / 57B 		| 32 GB+ 	 | **The Reliable MoE.** Excellent coding and math capabilities. Very stable for long agentic loops.
| **Qwen 3 235B-A22B** 	| ollama pull qwen3:235b-a22b 		| 22B / 235B 		| 128 GB+	 | **Enterprise MoE.** Massive intelligence rivaling GPT-4, but only uses 22B active params. Requires high-end workstation.
| **Gemma 4 31B-A4B** 	| ollama pull gemma4:31b-a4b 		| 4B / 31B 		| 20 GB+ 	 | **Google's MoE.** Strong tool calling and reasoning.
| **Nemotron-3-Super** 	| ollama pull nemotron-3-super	 	| 12B / 120B 		| 64 GB+ 	 | **1M Context.** 50% faster token generation, multi-agent optimized.
| **DeepSeek R1 671B** 	| ollama pull deepseek-r1:671b	 	| 37B / 671B 		| 400 GB+* 	 | **Deep Reasoning.** The ultimate reasoning model. *Requires multi-GPU server or Mac Studio Ultra.
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

-----------------------------------------------------------------------------------

### How to Choose the Right Model

### For General Daily Use (Chat, Notes, Simple Tasks)

**Recommended:** Qwen 2.5 Coder 7B or Mistral Nemo 12B

**Why:**
- Fast and responsive
- Handle MAi-RAG system prompt perfectly
- Good balance of speed and capability
- Work well on 8GB-16GB RAM systems

**Installation:**

ollama pull qwen2.5-coder:7b

-----------------------------------------------------------------------------------

### For Writing, Heavy Coding & File Generation
Recommended: Qwen 2.5 Coder 14B, Qwen 2.5 Coder 32B, or Qwen 3 30B-A3B
Why:

    Excellent code generation capabilities
    Strong tool-calling performance
    Handle complex file creation tasks
    Good at understanding context

Installation:

# Dense model (more consistent)
ollama pull qwen2.5-coder:14b

# OR MoE model (faster if you have RAM)
ollama pull qwen3:30b-a3b

-----------------------------------------------------------------------------------

### For Complex Agentic Workflows (Multi-step tool calling, RAG, Planning)
Recommended: Llama 3.3 70B or Qwen 3 235B-A22B

Why:

    - Rarely hallucinate tool calls
    - Follow strict JSON schemas flawlessly
    - Handle complex multi-step reasoning
    - Excellent for long agentic loops

Installation:

# If you have 48GB+ RAM
ollama pull llama3.3:70b

# If you have 128GB+ RAM
ollama pull qwen3:235b-a22b

-----------------------------------------------------------------------------------

### For Low-End Hardware (4GB - 12GB RAM)

Recommended: Qwen 2.5 Coder 1.5B, Llama 3.2 3B, Granite 3.1 MoE 3B, or Granite 3.3 8B
Why:

    - Keep MAi-RAG UI responsive
    - Handle basic memory tasks
    - Work on older hardware
    - Fast inference times

Installation:

# Smallest option
ollama pull qwen2.5-coder:1.5b

# OR slightly better
ollama pull llama3.2:3b

# OR MoE option
ollama pull granite3.1-moe:3b

-----------------------------------------------------------------------------------

### Understanding RAM Requirements

Important Notes

"Min System RAM" assumes:

    - Running the model at default Ollama 4-bit quantization (Q4_K_M)
    - No other major applications running
    - Linux/macOS operating system

If you use 8-bit quantization:

    - Double the RAM requirement
    - Better quality but slower

Always leave 2-4GB of RAM free for:

    - Your operating system
    - MAi-RAG backend (FastAPI, Qdrant)
    - Browser and other applications

-----------------------------------------------------------------------------------

### GPU Acceleration

If you have a dedicated NVIDIA GPU:

    - VRAM is the limiting factor instead of System RAM
    - A 32B model requires ~20GB of VRAM to run entirely on GPU
    - GPU inference is significantly faster than CPU
    - Ollama automatically uses GPU if available

Check your GPU VRAM:
  nvidia-smi

-----------------------------------------------------------------------------------

### RAM Usage Examples

System RAM	Recommended Models		Notes
8 GB		1.5B, 3B, 7B			Leave 2-3GB free for OS
12 GB		3B, 7B, 12B			Can run 7B comfortably
16 GB		7B, 12B, 14B			Sweet spot for most users
20 GB		14B, 32B, MoE 30B		Can run larger models
32 GB		32B, MoE 57B			Good for heavy workloads
42 GB+		70B				Maximum dense models
64 GB+		MoE 120B			Enterprise-grade
128 GB+		MoE 235B			Ultimate performance

-----------------------------------------------------------------------------------

### Switching Models in MAi-RAG

Via Web UI

    - Open MAi-RAG in your browser
    - Go to Chat Console
    - Click the Model Selector dropdown
    - Select your desired model
    - (Optional) Check "Set as default" to make it permanent

Via Command Line

   # List available models
   ollama list

   # Pull a new model
   ollama pull qwen2.5-coder:14b

   # Remove a model
   ollama rm qwen2.5-coder:7b

### Hot-Swapping

You can switch models mid-conversation without restarting MAi-RAG:

    1. Start a conversation with one model
    2. Change the model in the dropdown
    3. Continue the conversation with the new model

    Note: The new model won't have context from the previous model's responses.

-----------------------------------------------------------------------------------

### Performance Expectations

CPU-Only Systems (Intel i3-1215U example)

Model		Tokens/Second		Response Time (100 tokens)
1.5B		20-30			3-5 seconds
3B		15-25			4-7 seconds
7B		8-15			7-12 seconds
14B		4-8			12-25 seconds
32B		2-5			20-50 seconds


GPU-Accelerated Systems (RTX 3060 example)

Model		Tokens/Second		Response Time (100 tokens)
7B		50-80			1-2 seconds
14B		30-50			2-3 seconds
32B		15-25			4-7 seconds

Note: Performance varies based on:

    - CPU/GPU model
    - RAM speed
    - System load
    - Model quantization
    - Context length

-----------------------------------------------------------------------------------

### Troubleshooting Model Issues

### Model Not Appearing in Dropdown

    # Check if Ollama is running
    curl http://localhost:11434/api/tags

    # Pull the model
    ollama pull qwen2.5-coder:7b

    # Restart MAi-RAG
    cd ~/MAi-RAG
    ./stop.sh
    ./start.sh


### Out of Memory Errors

Symptoms:

    - Model fails to load
    - System becomes unresponsive
    - Ollama crashes

Solutions:

    1. Use a smaller model
    2. Close other applications
    3. Increase swap space (Linux)
    4. Upgrade RAM

### Slow Response Times

Solutions:

    1. Use a smaller model (7B instead of 32B)
    2. Reduce context window size in Ollama
    3. Close RAM-intensive applications
    4. Enable GPU acceleration if available


### Model Produces Poor Results

Solutions:

    1. Try a different model
    2. Adjust the system prompt in Assistant Settings
    3. Provide more specific instructions
    4. Use a model optimized for your task (coding vs. writing)


### Advanced: Custom Models

  Using Custom Models

   You can use any model compatible with Ollama:

    1. Create a Modelfile:
    FROM ./path/to/your/model.bin
    PARAMETER temperature 0.7
    SYSTEM "You are a helpful assistant."

    2. Create the model:
    ollama create my-custom-model -f Modelfile

    3. Use in MAi-RAG:
    Select "my-custom-model" from the dropdown


### Quantization Options

Ollama supports different quantization levels:

    - Q4_K_M (default): 4-bit, good balance of speed and quality
    - Q5_K_M: 5-bit, better quality, slower
    - Q8_0: 8-bit, best quality, slowest

    Specify quantization:
    ollama pull qwen2.5-coder:7b-q5_k_m

### Getting Help

Model Recommendations:

    - Check Ollama Library
    - Review model benchmarks
    - Test different models for your use case

Performance Issues:

    - Run System Doctor from Assistant Settings
    - Check system resources in Chat Console
    - Review Ollama logs: ollama logs

Community Support:

    - GitHub Discussions
    - Ollama Discord

<p align="center">
  <strong>Find the perfect model for your needs and hardware!</strong>
</p>
