

#######################################################################################################
#######################################################################################################

Self-Healing System

Since you already have the "Generate → Verify → Fix → Save" workflow established (with ast.parse verification), your system is perfectly primed for self-healing and feature expansion.
However, to do this safely and effectively, you need to configure a few guardrails and provide the agent with the right instructions. Here is the exact blueprint to enable this:

 Step 1: Update the System Prompt for "Project Self-Healing"
Your current prompt restricts the AI to ~/MAi-RAG/workspace/ (which is for user files). To let it fix the app itself, you must grant it scoped access to the project root, with strict safety rules.
Add this section to your System Prompt:

## PROJECT SELF-HEALING & EXPANSION PROTOCOL
You have read/write access to the entire project root: ~/MAi-RAG/
You are authorized to debug, refactor, and add features to the codebase, subject to these NON-NEGOTIABLE rules:

1. SAFETY FIRST: Before modifying any file, instruct the user to create a Git checkpoint (`git add . && git commit -m "Pre-AI-refactor checkpoint"`).
2. TARGETED CHANGES: Due to CPU inference constraints, do NOT attempt to rewrite entire files or the whole codebase at once. Read the specific file, identify the exact lines to change, and output only the necessary diff or targeted replacement.
3. VERIFY BEFORE SAVE: 
   - For Python: You must mentally simulate or request execution of `python -m py_compile <filepath>` to ensure zero syntax errors before providing the final code.
   - For TypeScript/React: Ensure all imports match, hooks are inside components, and JSX syntax is valid.
4. EXPLAIN THE FIX: Always briefly explain *why* the error occurred and *how* your fix resolves it before providing the code.
5. RESPECT ARCHITECTURE: Maintain the existing separation of concerns (e.g., Pydantic models in `main.py`, DB logic in `sqlite_memory.py`, UI in `frontend/src/`).




Step 2: Equip the Agent with the Right "Tools"
For the agent to self-fix, it needs to be able to read the code it's trying to fix. Ensure your agent's tool-calling schema includes:

    read_file: {"path": "app/database/sqlite_memory.py"}
    write_file: {"path": "app/database/sqlite_memory.py", "content": "..."}
    run_shell_command (Optional but highly recommended): {"command": "python -m py_compile app/database/sqlite_memory.py"} or {"command": "cd ~/MAi-RAG/frontend && npm run build"}

    💡 If your current agent doesn't have a run_shell_command tool, you can act as the "Verifier" in the loop. The AI generates the fix, you paste it, and if it fails, you paste the terminal error back to the AI. It is exceptionally good at iterating on its own errors.




🔄 Step 3: The "Self-Healing" Prompting Workflow
When you encounter a bug (like the recent SQLite location column error) or want to add a feature, prompt the agent like this:
Example Prompt for Self-Fixing:

    "I am getting this error in the backend: sqlite3.OperationalError: no such column: location when calling /api/memory/sqlite/events/upcoming. 

        Read app/database/sqlite_memory.py and app/main.py.
        Identify why the events table is missing the location column or why the query is failing.
        Generate the exact code fix.
        Verify the Python syntax is valid.
        Provide the updated file content or the exact terminal command I should run to fix the database schema."

Example Prompt for Feature Addition:

    "I want to add a 'Dark Mode' toggle to the Header. 

        Read frontend/src/components/layout/Header.tsx and frontend/src/globals.css.
        Add a state variable for dark mode and a toggle button.
        Ensure it saves to localStorage and applies a data-theme="dark" attribute to the <html> tag.
        Output the updated Header.tsx code, ensuring no existing functionality (like nav scrolling) is broken."

⚠️ Step 4: Critical Safety Nets (Do Not Skip)
Because the AI will be modifying its own codebase, you must protect against infinite loops or catastrophic rewrites:

    1. Use Git: Before asking the AI to make a major change, run:


cd ~/MAi-RAG
git add .
git commit -m "Checkpoint before AI self-healing"


If the AI hallucinates and breaks everything, you can instantly run git reset --hard HEAD~1 to undo it.

	2. CPU Inference Reality Check: You are running qwen2.5-coder:32b on an i3-1215U CPU. It will take 10–30+ seconds per token generation. Do not ask it to "rewrite the whole app". Ask it to "fix this specific function" or "update this specific component". Targeted prompts = faster, more accurate results.
	3. Review Before Pasting: Always glance at the AI's output before pasting it into your files. Look for missing imports, truncated code blocks, or accidental deletions.




################################################################
Other Method of self repair:

You are essentially creating a Staging/Sandbox Environment, and yes, it is incredibly safe. If the AI destroys the code, you just rename the folders back. 
However, your "clunky" method has two fatal traps that will cause the AI to crash your system if you don't guard against them. 
Here is how to execute your idea safely, avoiding the traps.
⚠️ The Two Fatal Traps

    The "Inception" Loop (Infinite Recursion): If you tell the AI to "read the project and copy it to the workspace," it might copy the workspace folder into the new workspace folder, resulting in workspace/workspace/workspace... until your hard drive fills up and crashes.
    The "Bloat" Trap (Node Modules & Venv): Your project folder is mostly made of node_modules (50,000+ files) and venv. If the AI tries to read, analyze, or copy these, it will run out of context memory, take hours, or generate garbage code.

✅ The Safe Execution Plan (The "Staging" Workflow)
To make your idea work perfectly, use rsync to create a lightweight, clean copy, and then use a strict prompt.
Step 1: Create the Clean Sandbox
Stop your backend (Ctrl+C in the terminal), then run this command. It copies only the source code to the workspace, ignoring the massive dependency folders.

# 1. Create a backup of your current working app
cp -r ~/MAi-RAG ~/MAi-RAG.backup

# 2. Create a clean "staging" folder inside the workspace
# --exclude ignores the massive folders the AI doesn't need to rewrite
rsync -av --exclude='venv' --exclude='node_modules' --exclude='.git' --exclude='__pycache__' ~/MAi-RAG/ ~/MAi-RAG/workspace/staging/


Step 2: Give the AI the "Sandbox" Instructions
Now, ask Qwen to work. Use this exact prompt structure so it stays in the sandbox and doesn't cause an Inception loop:

    "I have created a staging environment at ~/MAi-RAG/workspace/staging/. 
    Your task is to refactor/fix the code located ONLY inside that staging directory.
    RULES:
    1. NEVER read, copy, or reference the workspace directory itself to avoid infinite loops.
    2. Do NOT rewrite venv or node_modules. Only modify .py, .tsx, .css, and .json files.
    3. When you are done, tell me you are ready to deploy."

Step 3: The "Flash" Swap (Testing Phase)
Once the AI finishes, you swap the live app with the AI's new version in 3 seconds.

Step 2: Give the AI the "Sandbox" Instructions
Now, ask Qwen to work. Use this exact prompt structure so it stays in the sandbox and doesn't cause an Inception loop:

    "I have created a staging environment at ~/MAi-RAG/workspace/staging/. 
    Your task is to refactor/fix the code located ONLY inside that staging directory.
    RULES:
    1. NEVER read, copy, or reference the workspace directory itself to avoid infinite loops.
    2. Do NOT rewrite venv or node_modules. Only modify .py, .tsx, .css, and .json files.
    3. When you are done, tell me you are ready to deploy."

Step 3: The "Flash" Swap (Testing Phase)
Once the AI finishes, you swap the live app with the AI's new version in 3 seconds.

# 1. Move the current live app out of the way
mv ~/MAi-RAG ~/MAi-RAG.live

# 2. Move the AI's new version into the live spot
mv ~/MAi-RAG/workspace/staging ~/MAi-RAG

# 3. Reinstall dependencies (since we didn't copy them)
cd ~/MAi-RAG
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install

# 4. Start the app and test!
cd ..
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload


Step 4: The Instant Revert (If it breaks)
If the AI broke the app, you don't need to do any complex fixes. Just run:


# 1. Stop the broken app (Ctrl+C)
# 2. Delete the AI's broken version
rm -rf ~/MAi-RAG

# 3. Instantly restore your backup
mv ~/MAi-RAG.backup ~/MAi-RAG

# 4. Restart the original, working app

Why this is better than Git for your specific use case:
If you use Git, and the AI messes up the database paths or environment variables, reverting the Git repo doesn't always cleanly revert the local .env or compiled files. Folder renaming is a hard, physical reset. It guarantees the environment is exactly as it was.
Summary of the Rules for the AI:
To make this work, your system prompt for the AI must include:


WORKING DIRECTORY: ~/MAi-RAG/workspace/staging/
FORBIDDEN DIRECTORIES: ~/MAi-RAG/workspace/workspace (NEVER create or read this), node_modules, venv.

This approach gives you 100% safety, utilizes the AI's existing workspace permissions, and keeps your filesystem clean. 

###########################################################

Final Method of Self Repair Mechanism

Here is the Ultimate Seamless Solution that combines your "Flash Revert" idea with a few minor technical tweaks to make it bulletproof.



Phase 1: The "Bulletproof" Backup & Stage
Instead of moving the original, we clone it. This gives you a pristine backup, and a sandbox for the AI.
Run these commands in your terminal:

# 1. Create the backup (The ultimate undo button)
cp -r ~/MAi-RAG ~/MAi-RAG.backup

# 2. Create the DEV folder
mkdir -p ~/MAi-RAG/workspace/MAi-RAG-DEV

# 3. Rsync ONLY the source code, excluding the workspace, heavy folders, and git
rsync -av \
  --exclude='workspace' \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  ~/MAi-RAG/ \
  ~/MAi-RAG/workspace/MAi-RAG-DEV/


Step 2: Copy the Dependencies (Without Recursion)
Now that the code is safely in the MAi-RAG-DEV folder, we copy the heavy dependencies directly into it. Because the destination folder is no longer inside the source, this won't cause a loop.

# Copy node_modules and venv into the new DEV folder
cp -r ~/MAi-RAG/node_modules ~/MAi-RAG/workspace/MAi-RAG-DEV/
cp -r ~/MAi-RAG/venv ~/MAi-RAG/workspace/MAi-RAG-DEV/

The venv Path Fix (Crucial):
Because we moved the venv to a new folder, we need to patch its hardcoded paths so it actually works in the new location. Run this quick sed command:

# Patch the activate scripts to point to the new DEV folder
find ~/MAi-RAG/workspace/MAi-RAG-DEV/venv/bin -type f -exec sed -i 's|/home/tony/MAi-RAG/venv|/home/tony/MAi-RAG/workspace/MAi-RAG-DEV/venv|g' {} +

(Now your copied venv and node_modules will work perfectly in the sandbox).



Phase 2: The "Project Architect" Prompt for Qwen
To stop the AI from creating orphaned files and duplicate logic, you need to change its persona. Don't just ask it to "fix code"; ask it to audit and architect.
SEE THE REWORKED STRICT RULES & PROTOCOLS (NON-NEGOTIABLE) BELOW.


Phase 3: The "Flash" Deploy (When the AI is done)
Once Qwen says it has finished cleaning and refactoring the code in MAi-RAG-DEV, you swap it into the live environment in 3 seconds.

# 1. Stop your backend if it's running (Ctrl+C)

# 2. Push the current live app out of the way (Instant Revert capability)
mv ~/MAi-RAG ~/MAi-RAG.old

# 3. Move the AI's new version into the live spot
mv ~/MAi-RAG/workspace/MAi-RAG-DEV ~/MAi-RAG

# 4. Start your app!
cd ~/MAi-RAG
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload



Phase 4: The Instant Revert (If the AI broke something)
If the app crashes or the UI is broken, you don't need to ask the AI to fix it. You just execute your "Flash Revert":

# 1. Stop the app (Ctrl+C)

# 2. Delete the AI's broken version
rm -rf ~/MAi-RAG

# 3. Restore the original, perfectly working version
mv ~/MAi-RAG.old ~/MAi-RAG

# 4. Restart
cd ~/MAi-RAG && source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Why this is the "Best Solution":

    1. Zero Bloat: By using rsync initially, you get a clean slate, but by keeping the venv and patching it, you save hours of npm install and pip install time.
    2. Zero Inception Loops: By explicitly naming the folder MAi-RAG-DEV and giving the AI a strict negative prompt ("Never create a folder containing 'workspace'"), the AI cannot accidentally copy the folder into itself.
    3. Zero Orphans: The "Phase 2" prompt forces the AI to act as a janitor before it acts as a developer. It will delete those duplicate .tsx files and old -bkup files before they cause import errors.
    4. Zero Downtime on Failure: The mv (move) command in Linux is virtually instantaneous. If the AI ruins the codebase, you are back to a working state in under 2 seconds.
    

we must expand the STRICT RULES into a comprehensive protocol. 
Here is the fully elaborated, bulletproof STRICT RULES section. You can copy and paste this directly into your System Prompt or your initial prompt to Qwen.

🛡️ STRICT RULES & PROTOCOLS (NON-NEGOTIABLE)
1. OUTPUT & FORMATTING STANDARDS

    Zero Truncation: Never truncate code blocks. If a file is too long for a single response, output it in clearly labeled sequential chunks (e.g., // PART 1 of 3, // PART 2 of 3). Never use // ... rest of code remains the same.
    Complete Context: Always provide the full, runnable file content unless explicitly asked for a diff. Partial snippets cause import and scope errors.
    Explain Before Code: Before providing any code, briefly explain why the error occurred, what logic is being changed, and how it resolves the issue.

2. VERIFICATION BEFORE SAVE

    Python Verification: Mentally simulate or explicitly request execution of python -m py_compile <filepath> to ensure zero syntax errors. Ensure all Pydantic models match the data being passed.
    TypeScript/React Verification: 
        Ensure all imports match the actual file paths (case-sensitive).
        Ensure all JSX tags are properly closed and self-closing tags (<img />, <input />) have slashes.
        Ensure all generic types and interfaces are defined before use.
    Database Verification: Ensure all SQL queries use parameterized arguments (?) to prevent injection. Verify column names match the _create_tables() schema exactly.

3. REACT & STATE MANAGEMENT (CRITICAL)

    Infinite Loop Prevention: NEVER include state variables in a useEffect dependency array if that state is updated inside the useEffect. 
    Async State Locking: When handling form submissions or API saves, use a useRef boolean (e.g., isSavingRef) alongside useState to prevent duplicate clicks or auto-trigger loops.
    Cleanup Functions: Always return a cleanup function in useEffect if setting intervals, timeouts, or event listeners (e.g., return () => clearInterval(interval)).
    Hook Rules: NEVER call Hooks (useState, useEffect, etc.) inside loops, conditions, or nested functions. They must be at the top level of the component.

4. PYTHON & BACKEND ARCHITECTURE

    Database Safety: ALWAYS use context managers (with sqlite_manager.get_cursor() as cur:) for database transactions to ensure automatic commits and rollbacks on failure. Never leave raw connections open.
    Error Handling: NEVER use silent exceptions (except: pass). Always log errors using logger.error(f"Context: {e}", exc_info=True) and return proper HTTP status codes via FastAPI.
    Separation of Concerns: 
        main.py: API routing, Pydantic request/response models, and orchestration.
        sqlite_memory.py / qdrant_manager.py: All raw database logic and queries.
        agent_core.py: LLM invocation, prompt engineering, and tool routing.

5. FRONTEND ARCHITECTURE & STYLING

    Respect Existing Patterns: This project heavily relies on inline styles and CSS variables (e.g., var(--accent), var(--line)). DO NOT attempt to extract these into external CSS modules unless explicitly requested. Maintain the existing inline styling paradigm.
    Event Propagation: When nesting clickable elements (e.g., a button inside a clickable card), always use e.stopPropagation() to prevent the parent event from triggering.
    Accessibility: Maintain existing aria-label and role attributes. Do not strip accessibility features for visual styling.

6. FILESYSTEM & SECURITY (SANDBOX PROTOCOL)

    Working Directory: You are strictly confined to ~/MAi-RAG/workspace/MAi-RAG-DEV/. 
    Inception Prevention: NEVER read, write, copy, or create a directory inside the workspace that contains the word "workspace". 
    Protected Directories: NEVER modify, rewrite, or attempt to optimize venv/, node_modules/, .git/, or .venv/. 
    Path Traversal: If writing backend code that handles file paths, always use pathlib.Path.resolve() and verify the path is within the allowed root using .relative_to().

7. DEPENDENCY & LIBRARY USAGE

    No New Dependencies: Do not suggest or import new external libraries (e.g., npm install or pip install) unless absolutely necessary and explicitly approved. Use the existing tech stack (FastAPI, SQLite, React, native CSS).
    Standard Libraries: Prefer Python standard libraries (pathlib, json, uuid, logging) over custom implementations.

8. PROACTIVE REFINEMENT & APPROVAL PROTOCOL (CRITICAL)

    Audit & Suggest: Do not just fix broken code. Actively scan for anti-patterns, performance bottlenecks, UX friction, redundant logic, and "code smells." Propose concrete improvements to make development smoother and the app more robust.
    The "Propose First" Rule: NEVER silently overwrite working code to "improve" it. If you see a better way to do something, present a brief "Refactoring Proposal" first. 
    Mandatory Backup Command: Before you output the final replacement code for any file you intend to modify, you MUST provide a 1-line shell command for me to run to backup the original file. 
        Format: cp ~/MAi-RAG/workspace/MAi-RAG-DEV/path/to/original_file.tsx ~/MAi-RAG/workspace/MAi-RAG-DEV/path/to/original_file.tsx.bak
    Explicit Approval Gate: After providing the Refactoring Proposal and the Backup Command, you MUST end your response with: "Awaiting your approval and backup confirmation to generate the final code." 
    Execution Phase: Only output the full, final code blocks after I explicitly reply with "Approved", "Proceed", or "Yes".


How this workflow will look in practice:
When you ask the AI to "Review and improve the CalendarPlannerApp", the conversation will now flow like this:
1. The AI's Analysis (No code written yet):

    *"I've reviewed CalendarPlannerApp.tsx. I noticed the year centering logic is using a fragile absolute positioning hack. 
    Proposal: I suggest switching to CSS Grid for the header to make it natively responsive and remove the translate(-50%, -50%) hack. This will prevent alignment issues on smaller screens.
    Action Required: Before I rewrite the file, please run this command to backup the current version:
    cp ~/MAi-RAG/workspace/MAi-RAG-DEV/frontend/src/components/planner/CalendarPlannerApp.tsx ~/MAi-RAG/workspace/MAi-RAG-DEV/frontend/src/components/planner/CalendarPlannerApp.tsx.bak
    Awaiting your approval and backup confirmation to generate the final code."*

2. Your Action:
You copy/paste the cp command into your terminal, hit enter, and then reply to the AI: "Backup done. Approved, proceed."
3. The AI's Execution:
The AI then outputs the complete, verified, and improved file.
Why this is the perfect balance:

    It forces the AI to think: By making it "propose" first, the LLM has to articulate its reasoning. This drastically reduces hallucinations because it has to "show its work" before generating tokens for the actual code.
    Zero accidental destruction: It physically cannot overwrite a file in your sandbox without you giving it a specific shell command to run first.
    Ultimate safety net: If the AI's "improvement" actually breaks the UI, you still have the .bak file in the exact same directory, ready to be renamed back in one second.

Add this to your prompt, and your LLM will transform from a cautious code-generator into a collaborative, highly effective development partner!    
