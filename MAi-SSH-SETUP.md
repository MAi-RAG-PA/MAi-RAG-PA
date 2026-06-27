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
  <a href="MAi-LICENCE-LEGAL-NOTICE.md">License</a>
</p>

<p align="center">
  <strong>Version 1.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

<h3 align="center">Complete guide for accessing your MAi-RAG-PA instance from other devices on your network or remotely via SSH tunnel.</h3>

-----------------------------------------------------------------------------------

## Quick Setup (5 minutes)

### On Your Main Computer Where MAi-RAG-PA is Running (Server):

1. **Find your IP address:**

```bash
    ip addr show | grep "inet " | grep -v 127.0.0.1
```

   **Look for something like 192.168.1.100**

2. **Ensure MAi-RAG-PA is running:**

    cd ~/MAi-RAG-PA
    ./start.sh

3. **Note the port: MAi-RAG-PA runs on port 8000 by default**

### On Your Tablet/Phone:

**Option 1: Direct LAN Access (Same WiFi Network)**

1. Connect tablet/phone to the same WiFi as your computer
2. Open browser and go to: http://192.168.1.XX:8000 (replace XX with the IP running MAi-RAG-PA)
3. That's it! No SSH needed for local network access.

**Option 2: SSH Tunnel (Remote Access)**

**If you want to access from outside your network or need encryption:**

1. Install SSH client:
   - iOS: Termius, Blink Shell
   - Android: JuiceSSH, Termius

2. Create SSH tunnel:

    ssh -L 8000:localhost:8000 username@192.168.1.XX

   **Replace username with your actual username and 192.168.1.XX with your computer's IP.**

3. Access in browser:
   - Open browser on tablet/phone
   - Go to: http://localhost:8000

-----------------------------------------------------------------------------------

## SSH Key Setup (Password-less Login)

**On your tablet/phone SSH client:**

1. Generate SSH key (most apps have a "Generate Key" option)
2. Copy the public key

**On your computer, run:**

    mkdir -p ~/.ssh
    nano ~/.ssh/authorized_keys

3. Paste the public key and save
4. Set permissions:

    chmod 600 ~/.ssh/authorized_keys
    chmod 700 ~/.ssh

-----------------------------------------------------------------------------------

## Firewall Configuration

**MAi-RAG-PA requires specific ports to be open for full functionality. Configure your firewall according to your needs:**

### Required Ports

| Port | Service | Protocol | Purpose | Required For |
|------|---------|----------|---------|--------------|
| 8000 | MAi-RAG-PA Web UI | TCP | Web interface access | LAN/Remote access |
| 8001 | Watchdog Service | TCP | Start/Stop control | Web UI control buttons |
| 11434 | Ollama | TCP | LLM inference API | Local operation |
| 6333 | Qdrant | TCP | Vector database API | RAG features |
| 22 | SSH | TCP | Remote access | SSH tunnel (optional) |

### UFW (Ubuntu/Debian)

**Allow MAi-RAG-PA web interface (LAN access):**

    sudo ufw allow 8000/tcp
    
**Allow Watchdog service (for WebUI control buttons)**

    sudo ufw allow 8001/tcp

**Allow Ollama (only needed if accessing from other machines):**

    sudo ufw allow 11434/tcp

**Allow Qdrant (only needed if accessing from other machines):**

    sudo ufw allow 6333/tcp

**Allow SSH (for remote access):**

    sudo ufw allow 22/tcp

**Enable firewall if not already enabled:**

    sudo ufw enable

**Check status:**

    sudo ufw status

### Firewalld (Fedora/RHEL/CentOS)

**Allow MAi-RAG-PA web interface:**

    sudo firewall-cmd --permanent --add-port=8000/tcp

**Allow Ollama:**

    sudo firewall-cmd --permanent --add-port=11434/tcp

**Allow Qdrant:**

    sudo firewall-cmd --permanent --add-port=6333/tcp

**Allow SSH:**

    sudo firewall-cmd --permanent --add-service=ssh

**Reload firewall:**

    sudo firewall-cmd --reload

**Check status:**

    sudo firewall-cmd --list-all

### Security Recommendation

**For local-only use, you can restrict access to localhost:**

**Only allow local connections (more secure):**

    sudo ufw allow from 127.0.0.1 to any port 8000
    sudo ufw allow from 127.0.0.1 to any port 11434
    sudo ufw allow from 127.0.0.1 to any port 6333

-----------------------------------------------------------------------------------

## Troubleshooting

**Can't connect?**

**Check firewall:**

    sudo ufw allow 22        #SSH
    sudo ufw allow 8000      #MAi-RAG-PA

**Verify IP:**

    ip addr show

**Test from another computer on same network first**

**Connection drops?**
- SSH into router and reserve static IP for your computer
- Or use a dynamic DNS service

**Slow performance?**
- Use SSH tunnel for compression:

    ssh -C -L 8000:localhost:8000 username@192.168.1.XX

**Replace username with your actual username and 192.168.1.XX with your computer's IP.**

-----------------------------------------------------------------------------------

## Advanced: Permanent SSH Tunnel

### Linux/macOS (systemd service)

**Create a systemd service to maintain a persistent SSH tunnel:**

    sudo nano /etc/systemd/system/mai-rag-ssh-tunnel.service

**Add this content:**

    [Unit]
    Description=MAi-RAG-PA SSH Tunnel
    After=network.target
        
    [Service]
    Type=simple
    User=yourusername
    ExecStart=/usr/bin/ssh -N -L 8000:localhost:8000 username@remote-server
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target

**Save and exit (Ctrl+O, Ctrl+X)**

**Enable and start:**

    sudo systemctl enable mai-rag-ssh-tunnel
    sudo systemctl start mai-rag-ssh-tunnel

-----------------------------------------------------------------------------------

## Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "When the computer starts"
4. Set action: "Start a program"
5. Program: `ssh`
6. Arguments: `-N -L 8000:localhost:8000 username@remote-server`

-----------------------------------------------------------------------------------

## Security Best Practices

### 1. Use SSH Keys Instead of Passwords

- Generate strong SSH keys (4096-bit RSA or Ed25519)
- Disable password authentication in: /etc/ssh/sshd_config

    sudo nano /etc/ssh/sshd_config

**Find and change to:**

    PasswordAuthentication no
    PubkeyAuthentication yes

**Save and exit (Ctrl+O, Ctrl+X)**

### 2. Restrict SSH Access

- Use AllowUsers in: /etc/ssh/sshd_config

    sudo nano /etc/ssh/sshd_config

**Add your "username" next to "AllowUsers":**

    AllowUsers yourusername

**Save and exit (Ctrl+O, Ctrl+X)**

### 3. Change Default SSH Port

**Edit /etc/ssh/sshd_config:**

    sudo nano /etc/ssh/sshd_config

**Change to:**

    Port 2222

**Save and exit (Ctrl+O, Ctrl+X)**

### 4. Use Fail2Ban

**Install and configure Fail2Ban to block brute force attempts:**

    sudo apt install fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban

### 5. Regular Updates

**Keep your system and SSH server updated:**

    sudo apt update && sudo apt upgrade -y

-----------------------------------------------------------------------------------

## Network Configuration

### Static IP Setup (Recommended)

**Linux (Netplan):** If you choose this configuration, you may need to install netplan on your system.

    sudo nano /etc/netplan/01-netcfg.yaml

**Example configuration:**

    network:
      version: 2
      renderer: networkd
      ethernets:
        eth0:
          dhcp4: no
          addresses: [192.168.1.100/24]
          gateway4: 192.168.1.1
          nameservers:
            addresses: [9.9.9.9, 149.112.112.112]

**Note: The above configuration uses Quad9 for DNS name servers [https://quad9.net/](https://quad9.net/)**

**Save and exit (Ctrl+O, Ctrl+X)**

**Apply changes:**

    sudo netplan apply

-----------------------------------------------------------------------------------

## macOS

**System Preferences → Network → Advanced → TCP/IP**

- Configure IPv4: Manually
- IP Address: 192.168.1.100
- Subnet Mask: 255.255.255.0
- Router: 192.168.1.1

### Port Forwarding (For External Access)

If you want to access MAi-RAG-PA from outside your network:

1. Access your router admin panel (usually 192.168.1.1)
2. Find Port Forwarding section
3. Create new rule:
   - Service Name: MAi-RAG-PA
   - External Port: 8000 (or custom port)
   - Internal IP: 192.168.1.100 (your computer's IP)
   - Internal Port: 8000
   - Protocol: TCP

**Security Warning:** Exposing MAi-RAG-PA to the internet is not recommended. Use SSH tunnel or VPN instead.

-----------------------------------------------------------------------------------

## HTTPS/SSL for Remote Access

**For secure remote access over the internet, you should use HTTPS instead of HTTP.**

### Quick Overview

**Option 1: SSH Tunnel (Recommended)**
- Most secure method
- No certificate management needed
- Encrypted connection
- See SSH Tunnel section above

**Option 2: Reverse Proxy with SSL**
- Use Nginx or Apache as reverse proxy
- Obtain SSL certificate from Let's Encrypt
- Requires domain name
- More complex setup

**Option 3: Self-Signed Certificate**
- Quick setup for testing
- Browser will show security warning
- Not recommended for production

**Security Warning**: Never expose MAi-RAG-PA directly to the internet over HTTP. Always use SSH tunnel or HTTPS.

### Setting Up Nginx Reverse Proxy with SSL

**Install Nginx and Certbot:**

    sudo apt update
    sudo apt install nginx certbot python3-certbot-nginx

**Create Nginx configuration:**

    sudo nano /etc/nginx/sites-available/mai-rag

**Add this content:**

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

**Enable the site:**

    sudo ln -s /etc/nginx/sites-available/mai-rag /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx

**Obtain SSL certificate:**

    sudo certbot --nginx -d your-domain.com

**Auto-renewal is configured automatically by Certbot.**

-----------------------------------------------------------------------------------

## Alternative: VPN Access

### For secure remote access, consider setting up a VPN:

**Option 1: WireGuard (Recommended)**

**On Server:**

    sudo apt install wireguard

**Follow WireGuard setup guide for your distribution.**

**On Client:**

**Install WireGuard app and import configuration.**

**Option 2: OpenVPN**

**On Server:**

    sudo apt install openvpn easy-rsa

**Follow OpenVPN setup guide.**

**On Client:**

**Install OpenVPN client and import configuration.**

-----------------------------------------------------------------------------------

## Performance Optimization

### 1. Enable TCP BBR Congestion Control

    echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p

### 2. Optimize SSH Configuration

**Edit /etc/ssh/sshd_config:**

    sudo nano /etc/ssh/sshd_config

**Change to:**

    Compression yes
    TCPKeepAlive yes
    ClientAliveInterval 60
    ClientAliveCountMax 3

**Save and exit (Ctrl+O, Ctrl+X)**

### 3. Use HTTP/2 (if using reverse proxy)

If you set up Nginx or Apache as a reverse proxy, enable HTTP/2 for better performance.

-----------------------------------------------------------------------------------

## Monitoring and Logs

### Check SSH Connections

    sudo last | grep ssh

### View SSH Logs

    sudo tail -f /var/log/auth.log    # Debian/Ubuntu
    sudo tail -f /var/log/secure      # RHEL/CentOS

### Monitor Network Traffic

    sudo netstat -an | grep :8000

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
