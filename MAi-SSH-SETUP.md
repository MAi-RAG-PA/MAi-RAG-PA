# Accessing MAi-RAG from Tablet/Phone via SSH

## Quick Setup (5 minutes)

### On Your Main Computer Where MAi-RAG is Running (Server):

1. **Find your IP address:**
   ip addr show | grep "inet " | grep -v 127.0.0.1

   Look for something like 192.168.1.100


2. **Ensure MAi-RAG is running:**

   cd ~/MAi-RAG
   ./start.sh


3. **Note the port: MAi-RAG runs on port 8000 by default**

On Your Tablet/Phone:

Option 1: Direct LAN Access (Same WiFi Network)

    Connect tablet/phone to the same WiFi as your computer
    Open browser and go to: http://192.168.1.XX:8000 (replace XX with your IP)
    That's it! No SSH needed for local network access.


Option 2: SSH Tunnel (Remote Access)
If you want to access from outside your network or need encryption:

    Install SSH client:
        iOS: Termius, Blink Shell
        Android: JuiceSSH, Termius
    Create SSH tunnel:

ssh -L 8000:localhost:8000 username@192.168.1.XX

#Replace username with your actual username and 192.168.1.XX with your computer's IP.

   3. Access in browser:
        Open browser on tablet/phone
        Go to: http://localhost:8000


SSH Key Setup (Password-less Login):
On your tablet/phone SSH client:

    Generate SSH key (most apps have a "Generate Key" option)
    Copy the public key
    On your computer, run:

mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys

4. Paste the public key and save
5. Set permissions:

chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh


Troubleshooting:
Can't connect?

    Check firewall: sudo ufw allow 22 (SSH) and sudo ufw allow 8000 (MAi-RAG)
    Verify IP: ip addr show
    Test from another computer on same network first

Connection drops?

    SSH into router and reserve static IP for your computer
    Or use a dynamic DNS service

Slow performance?

    Use SSH tunnel for compression: ssh -C -L 8000:localhost:8000 username@192.168.1.XX

    #Replace username with your actual username and 192.168.1.XX with your computer's IP.
