Here is the draft for your HARDWARE\_GUIDE.md. You can drop this directly into the root of your llm-clutch repo or put it in a GitHub Wiki. It acts as the companion piece to the software, explaining how to set up the physical environment that makes the code sing.

# **The 60-Second Hot-Swap: Building a Thunderbolt AI Fabric**

**llm-clutch** is the software orchestrator that shifts your local AI cluster from a fast daily driver to a heavy reasoning model. But to make hot-swapping a 75GB+ model (like GPT-OSS-120B) viable without grinding your workflow to a halt, you need the right physical infrastructure.  
If you try to load a massive model across a standard 1 Gigabit Ethernet network, your cluster will sit idle for 10-15 minutes while the weights transfer. If you use this Thunderbolt/NFS architecture, you can load the same model into unified memory across multiple machines in **under 60 seconds**.  
This guide details how to turn a primary Mac Studio into a high-speed storage fabric for smaller worker Macs (MacBooks, Mac Minis).

## **🏗️ The Architecture**

* **Node 1 (Primary):** M1 Mac Studio (Contains the physical NVMe SSD with the model weights).  
* **Node 2 (Worker):** M2 MacBook  
* **Node 3 (Worker):** M4 Mac Mini

Instead of forcing the worker nodes to store massive model weights on their constrained internal SSDs, they will pull their assigned model slices directly from the Mac Studio's SSD. They do this over a dedicated **IP-over-Thunderbolt Bridge**, which negotiates at 10-20 Gbps (1,250 \- 2,500 MB/s), bypassing standard network switches completely.

## **Step 1: The Physical Connection**

Connect all three machines using high-quality **Thunderbolt 4** cables. You can either daisy-chain them (if you have the ports) or connect the workers directly to the Mac Studio in a star topology.

## **Step 2: The Thunderbolt Network (IP Subnet)**

We need to create an isolated, ultra-fast local network strictly for model weight transfers.  
On **all three Macs**:

1. Open **System Settings \> Network**.  
2. Locate the **Thunderbolt Bridge** interface.  
3. Click **Details...** and change "Configure IPv4" to **Manually**.  
4. Assign the following static IP addresses (using Subnet Mask 255.255.255.0):  
   * **Node 1 (Studio):** 10.0.0.1  
   * **Node 2 (MacBook):** 10.0.0.2  
   * **Node 3 (Mini):** 10.0.0.3

*Test it:* Open terminal on the MacBook and run ping 10.0.0.1. You should see response times of \< 1.0 ms.

## **Step 3: The Storage Fabric (NFS)**

We use NFS (Network File System) instead of standard Mac File Sharing (SMB) because NFS has significantly lower overhead, allowing us to saturate the Thunderbolt bandwidth.

### **On Node 1 (The Mac Studio):**

1. Download your heavy models (e.g., via Exo or huggingface-cli) into a dedicated shared directory. For this guide, we use /Users/Shared/exo\_models.  
2. Open Terminal and edit the NFS exports file:  
   Bash  
   sudo nano /etc/exports

3. Add the following line. This shares the directory **read-only**, strictly bound to the Thunderbolt subnet, preventing worker nodes from accidentally writing hidden .DS\_Store files or messing with the weights:  
   Plaintext  
   /Users/Shared/exo\_models \-network 10.0.0.0 \-mask 255.255.255.0 \-ro \-mapall=nobody

4. Start the NFS daemon:  
   Bash  
   sudo nfsd enable  
   sudo nfsd update

### **On Nodes 2 & 3 (The Workers):**

1. Create a local empty directory to act as the mount point:  
   Bash  
   sudo mkdir \-p /mnt/tb\_studio\_models

2. Mount the Studio's NFS share over the Thunderbolt IP:  
   Bash  
   sudo mount \-t nfs \-o ro 10.0.0.1:/Users/Shared/exo\_models /mnt/tb\_studio\_models

*(Pro-tip: If you reboot the worker nodes frequently, you can add this mount to your /etc/fstab to automatically mount on boot).*

## **Step 4: Configuring Exo**

Exo needs to know to look at this new high-speed network mount instead of trying to download the models from the internet.  
On **Nodes 2 and 3**, set the following environment variable before starting Exo:

Bash  
export EXO\_MODELS\_READ\_ONLY\_DIRS="/mnt/tb\_studio\_models"  
uv run exo

*(Note: Node 1 just runs Exo normally, pointing to its local /Users/Shared/exo\_models directory).*

## **🚀 The Result**

When llm-clutch issues the command to load GPT-OSS-120B:

1. Exo calculates the topology and assigns layers to each node.  
2. The **Mac Studio** reads its layers locally at \~2,000 MB/s.  
3. The **MacBook** and **Mac Mini** read their layers over the Thunderbolt NFS mount. Because of the read-only NFS configuration and the raw speed of the Studio's internal NVMe drive, they will pull data at 1,500+ MB/s.  
4. The entire 75GB model populates across the cluster's unified RAM in under a minute, and OpenClaw resumes its agentic workflow with its "thinking cap" on.