#!/usr/bin/env python3
import subprocess
import time
import os
import sys

def main():
    print("[*] Starting SSII PAI5 RedTeamPro Audit Pipeline...")
    
    # Ensure evidence directory exists
    evidence_dir = "evidence"
    if not os.path.exists(evidence_dir):
        os.makedirs(evidence_dir)
        
    log_file_path = os.path.join(evidence_dir, "redteam_execution.log")
    print(f"[*] Execution logs will be written to: {log_file_path}")
    
    # Paths to files
    server_path = os.path.join("src", "target", "vulnerable_server.py")
    client_path = os.path.join("src", "redteam", "redteam_tool.py")
    
    # Start target server in the background
    print("[*] Launching vulnerable server...")
    server_process = subprocess.Popen(
        [sys.executable, server_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for services to bind
    time.sleep(2)
    
    # Run the Red Team scanner and exploiter
    print("[*] Running Red Team penetration testing suite...")
    
    with open(log_file_path, "w") as log_file:
        client_process = subprocess.Popen(
            [sys.executable, client_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Read output in real-time, print to console, and write to log file
        for line in client_process.stdout:
            sys.stdout.write(line)
            log_file.write(line)
            log_file.flush()
            
        client_process.wait()
        
    print(f"\n[*] Penetration testing completed with exit code: {client_process.returncode}")
    
    # Stop background server
    print("[*] Stopping vulnerable server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
        
    print("[+] Audit pipeline execution completed successfully.")

if __name__ == "__main__":
    main()
