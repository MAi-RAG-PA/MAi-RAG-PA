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

    ```bash
    cd ~/MAi-RAG-PA
    ./start.sh
    ```

   3. **Note the port: MAi-RAG-PA runs on port 8000 by default**

   **On Your Tablet/Phone:**

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

    ```bash
    ssh -L 8000:localhost:8000 username@192.168.1.XX
    ```

   **Replace username with your actual username and 192.168.1.XX with your computer's IP.**

   3. Access in browser:
        - Open browser on tablet/phone
        - Go to: http://localhost:8000

## SSH Key Setup (Password-less Login)

   **On your tablet/phone SSH client:**

   1. Generate SSH key (most apps have a "Generate Key" option)
   2. Copy the public key
   
   **On your computer, run:**

    ```bash
    mkdir -p ~/.ssh
    nano ~/.ssh/authorized_keys
    ```
   3. Paste the public key and save
   4. Set permissions:

    ```bash
    chmod 600 ~/.ssh/authorized_keys
    chmod 700 ~/.ssh
    ```

--------------------------------------------------------

## Troubleshooting

   **Can't connect?**

   **Check firewall:**

    ```bash
    sudo ufw allow 22        #SSH
    sudo ufw allow 8000      #MAi-RAG-PA
    ```

   **Verify IP:**

    ```bash
    ip addr show
    ```
    **Test from another computer on same network first**

   **Connection drops?**
   - SSH into router and reserve static IP for your computer
   - Or use a dynamic DNS service

   **Slow performance?**
   - Use SSH tunnel for compression:

    ```bash
    ssh -C -L 8000:localhost:8000 username@192.168.1.XX
    ```
   **Replace username with your actual username and 192.168.1.XX with your computer's IP.**

--------------------------------------------------------

## Advanced: Permanent SSH Tunnel

   **Linux/macOS (systemd service)**

   **Create a systemd service to maintain a persistent SSH tunnel:**

    ```bash
    sudo nano /etc/systemd/system/mai-rag-ssh-tunnel.service
    ```

    **Add this content:**

    ```ini
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
    ```
   Ctrl + o 
   Ctrl + x

   **Enable and start:**

    ```bash
    sudo systemctl enable mai-rag-ssh-tunnel
    sudo systemctl start mai-rag-ssh-tunnel
    ```

--------------------------------------------------------

## Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "When the computer starts"
4. Set action: "Start a program"
5. Program: `ssh`
6. Arguments: `-N -L 8000:localhost:8000 username@remote-server`

--------------------------------------------------------

## Security Best Practices

**1. Use SSH Keys Instead of Passwords**

   - Generate strong SSH keys (4096-bit RSA or Ed25519)
   - Disable password authentication in: /etc/ssh/sshd_config

    ```bash
    sudo nano /etc/ssh/sshd_config
    ```

   **Find and change to;**

    ```config
    PasswordAuthentication no
    PubkeyAuthentication yes
    ```
   Ctrl + o 
   Ctrl + x


   **2. Restrict SSH Access**
   - Use AllowUsers in: /etc/ssh/sshd_config

    ```bash
    sudo nano /etc/ssh/sshd_config
    ```

   **Add your "username" next to "AllowUsers":**

    ```config
    AllowUsers yourusername
    ```
   Ctrl + o 
   Ctrl + x


   **3. Change Default SSH Port**

   **Edit /etc/ssh/sshd_config**

   ```bash
   sudo nano /etc/ssh/sshd_config
   ```

   **Change to:**

    ```config
    Port 2222
    ```
   Ctrl + o 
   Ctrl + x


   **4. Use Fail2Ban**

   **Install and configure Fail2Ban to block brute force attempts:**

    ```bash
    sudo apt install fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    ```


   **5. Regular Updates**

   **Keep your system and SSH server updated:**

    ```bash
    sudo apt update && sudo apt upgrade -y
    ```

--------------------------------------------------------

## Network Configuration

   **Static IP Setup (Recommended)**

   **Linux (Netplan):** If you choose this configuration, you may need to install netplan on your system.

    ```bash
    sudo nano /etc/netplan/01-netcfg.yaml
    ```

   **Example configuration:**

    ```yaml
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
    ```
   **Note: The above configuration uses Quad9 for DNS name servers [https://quad9.net/](https://quad9.net/)**

   Ctrl + o 
   Ctrl + x

   **Apply changes:**

    ```bash
    sudo netplan apply
    ```

--------------------------------------------------------

## macOS

   **System Preferences → Network → Advanced → TCP/IP**

   - Configure IPv4: Manually
   - IP Address: 192.168.1.100
   - Subnet Mask: 255.255.255.0
   - Router: 192.168.1.1

   **Port Forwarding (For External Access)**

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

--------------------------------------------------------

## Alternative: VPN Access

### For secure remote access, consider setting up a VPN:

   **Option 1: WireGuard (Recommended)**

   **On Server:**
  
    ```bash
    sudo apt install wireguard
    ```

   **Follow WireGuard setup guide for your distribution.**

   **On Client:**

   **Install WireGuard app and import configuration.**


   **Option 2: OpenVPN**

   **On Server:**

    ```bash
    sudo apt install openvpn easy-rsa
    ```

   **Follow OpenVPN setup guide.**

   **On Client:**

   **Install OpenVPN client and import configuration.**

--------------------------------------------------------

## Performance Optimization

   **1. Enable TCP BBR Congestion Control**

    ```bash
    echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
    ```

   **2. Optimize SSH Configuration**

   **Edit /etc/ssh/sshd_config:**

    ```bash
    sudo nano /etc/ssh/sshd_config
    ```

   **Change to:**

    ```config
    Compression yes
    TCPKeepAlive yes
    ClientAliveInterval 60
    ClientAliveCountMax 3
    ```
   Ctrl + o 
   Ctrl + x

   **3. Use HTTP/2 (if using reverse proxy)**
   If you set up Nginx or Apache as a reverse proxy, enable HTTP/2 for better performance.

## Monitoring and Logs

   **Check SSH Connections**

    ```bash
    sudo last | grep ssh
    ```

### View SSH Logs

    ```bash
    sudo tail -f /var/log/auth.log    # Debian/Ubuntu
    sudo tail -f /var/log/secure      # RHEL/CentOS
    ```

### Monitor Network Traffic

    ```bash
    sudo netstat -an | grep :8000
    ```

--------------------------------------------------------

   **Documentation:**

   <a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
   <a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
   <a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
   <a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
   <a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

   **Support & Contact:**

   **Issues**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues">GitHub Issues</a>
   **Discussions**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions">GitHub Discussions</a>
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