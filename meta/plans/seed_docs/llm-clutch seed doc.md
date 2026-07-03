## **Document Context: Project Blueprint for Ticket Generation**

**To the AI Assistant receiving this document:**  
This is the technical blueprint for a new open-source Python package. Your task is to ingest this architecture, combine it with the user's provided repository template, and generate a comprehensive set of development tickets (Epics and Issues) to build, test, and publish this project to PyPI.

## **Project Overview: llm-clutch**

**Elevator Pitch:** A hardware-aware, local LLM orchestration package that safely hot-swaps massive neural networks in memory across a local cluster.  
**The Problem:** Running a local multi-node AI cluster (e.g., using Exo) presents a tradeoff. A fast, efficient model (like Qwen3-Next-80B) is great for daily tasks, but occasionally an agentic workflow (via OpenClaw) requires a heavyweight reasoning model (like GPT-OSS-120B). Copying 75GB+ model weights across standard networks or reading them from slow NAS drives takes 15+ minutes, stalling the agent.  
**The Solution:** llm-clutch manages a high-speed "hot swap" using a centralized NVMe drive shared over an IP-over-Thunderbolt bridge (NFS). More importantly, it acts as a traffic cop (a "synchromesh") that verifies network topology and available unified memory *before* dropping the current model and loading the new one, preventing cluster crashes.

## **Nomenclature & The Transmission Metaphor**

The package uses a manual transmission metaphor to make the state management intuitive. The architecture should be built around these core concepts:

* **rev\_match(required\_ram: int):** The pre-flight safety check. It pings the worker nodes on the Thunderbolt subnet (e.g., 10.0.0.x) and queries the backend to ensure the cluster is online and has enough pooled VRAM/RAM to accept the new model.  
* **disengage():** Calls the backend API to unload the currently active model weights from memory.  
* **engage(model\_name: str):** Calls the backend API to load the target model weights into the cluster's memory.  
* **upshift(heavy\_model: str):** The macro-function called by an agent to move from the daily driver to the high-reasoning model. It triggers rev\_match(), disengage(), and engage().  
* **downshift(light\_model: str):** The macro-function to return the cluster to the fast, lightweight daily driver model once the heavy task is complete.

## **Technical Architecture & Modules**

The codebase must be abstracted so it isn't hardcoded to one specific LLM runner, though Exo is the primary target for v1.0.

### **1\. Abstract Backend Provider (backend/base.py)**

An abstract base class (ModelBackend) that defines the required methods: unload\_model(), load\_model(), and get\_available\_memory().

### **2\. Exo Backend Implementation (backend/exo.py)**

An implementation of ModelBackend specifically for the Exo API.

* Must interface with Exo's topology/health endpoints to get available RAM across the cluster.  
* Must hit Exo's load/unload endpoints to manage the model lifecycle.

### **3\. Infrastructure Manager (core/infra.py)**

Handles the hardware-level checks.

* Requires a configuration of target IPs (the Thunderbolt bridge addresses of the worker nodes).  
* Executes ICMP pings or socket checks to verify the nodes are awake and reachable before a shift is attempted.

### **4\. The Clutch Engine (core/clutch.py)**

The main orchestrator class (LLMClutch) that ties the Infrastructure Manager and the Backend together. This exposes the upshift() and downshift() methods to the end user or agent.

### **5\. OpenClaw Tool Wrapper (integrations/openclaw.py)**

A pre-formatted tool definition (e.g., a JSON schema or Python callable) that allows llm-clutch to be directly injected into an OpenClaw agent as an executable tool. This allows the agent to self-escalate when it detects a complex task.

## **Required Ticket Generation Scope**

Please break this project down into logical tickets. The tickets should cover:

1. **Project Initialization:** Setting up pyproject.toml, Ruff/MyPy linting, and standard project structure based on the repo template. Note that I am explicitly requesting you to propose an edit/superseding doc to ADR-003, as I want to use uv over poetry. The ecosystem has matured, as noted on the original doc.  
2. **Core Logic Implementation:** Tickets for the Backend interfaces, Infra Manager, and the main Clutch orchestrator.  
3. **Hardware Mocking/Testing:** Tickets to build pytest fixtures that mock Exo API responses and Thunderbolt network pings, so the package can be tested without the physical hardware.  
4. **Agent Integration:** Building the OpenClaw tool schema.  
5. **Documentation & Publishing:** Writing the README (explaining the Thunderbolt/NFS hardware setup required to use the package effectively), setting up GitHub Actions for CI, and PyPI publishing workflows. Refer to the existing Hardware Guide as an example of my specific instance’s setup, and the secret-sauce that makes it work; it’s not required for the package to function though.