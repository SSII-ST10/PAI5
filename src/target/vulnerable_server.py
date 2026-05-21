#!/usr/bin/env python3
import socket
import threading
import sys
import time
import urllib.parse

# Configurable Ports
SSH_PORT = 2222
HTTP_PORT = 8080
MYSQL_PORT = 3306

# Virtual Filesystem in memory
VFS = {
    "/etc/passwd": (
        "root:x:0:0:root:/root:/bin/bash\n"
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
        "sync:x:4:65534:sync:/bin:/bin/sync\n"
        "games:x:5:60:games:/usr/games:/usr/sbin/nologin\n"
        "man:x:6:12:man:/var/cache/man:/usr/sbin/nologin\n"
        "lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin\n"
        "mail:x:8:8:mail:/var/mail:/usr/sbin/nologin\n"
        "news:x:9:9:news:/var/spool/news:/usr/sbin/nologin\n"
        "uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin\n"
        "proxy:x:13:13:proxy:/bin:/usr/sbin/nologin\n"
        "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
        "backup:x:34:34:backup:/var/backups:/usr/sbin/nologin\n"
        "list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin\n"
        "irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin\n"
        "gnats:x:41:41:Gnats Database Admin:/var/lib/gnats:/usr/sbin/nologin\n"
        "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
        "libuuid:x:100:101::/var/lib/libuuid:\n"
        "syslog:x:101:103::/home/syslog:/bin/false\n"
        "mysql:x:102:104:MySQL Server,,,:/nonexistent:/bin/false\n"
        "redteam:x:1000:1000:RedTeamPro User,,,:/home/redteam:/bin/bash\n"
    ),
    "/var/www/html/index.php": (
        "<html>\n<head><title>Gobierno de Andalucia - Portal de Transparencia</title></head>\n"
        "<body>\n<h1>Portal de Transparencia (Interno)</h1>\n"
        "<p>Bienvenido al portal de transparencia administrativa.</p>\n"
        "<!-- Powered by Drupal 8.5.0 -->\n"
        "</body>\n</html>"
    ),
    "/home/redteam/flag.txt": "FLAG{REDTEAMPRO_SYSTEM_OWNED_NIST_800_115_SUCCESS}",
    "/root/flag_root.txt": "FLAG{ROOT_LEVEL_PRIVILEGE_ESCALATION_COMPLETED_CVE_2018_7600}"
}

# Mutex for VFS modifications
vfs_lock = threading.Lock()

# --- SSH SERVICE SIMULATOR ---
def handle_ssh_client(client_socket, addr):
    print(f"[*] SSH: Connection from {addr[0]}:{addr[1]}")
    try:
        # Send standard SSH banner and wait for client to respond or disconnect
        client_socket.sendall(b"SSH-2.0-OpenSSH_7.2p2 Ubuntu-4ubuntu2.10\r\n")
        client_socket.recv(1024)
    except Exception as e:
        pass
    finally:
        client_socket.close()

def start_ssh_server():
    ssh_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssh_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        ssh_server.bind(("127.0.0.1", SSH_PORT))
        ssh_server.listen(5)
        print(f"[+] SSH Service running on port {SSH_PORT} (Simulating OpenSSH 7.2p2)")
        while True:
            client, addr = ssh_server.accept()
            t = threading.Thread(target=handle_ssh_client, args=(client, addr), daemon=True)
            t.start()
    except Exception as e:
        print(f"[!] SSH Bind Error on port {SSH_PORT}: {e}")

# --- COMMAND EXECUTION ENGINE ---
def simulate_command_execution(cmd_str):
    cmd_str = cmd_str.strip()
    if not cmd_str:
        return ""
    
    if cmd_str == "whoami":
        return "www-data\n"
    elif cmd_str == "id":
        return "uid=33(www-data) gid=33(www-data) groups=33(www-data)\n"
    elif cmd_str == "uname -a":
        return "Linux public-agency-server 4.15.0-142-generic #146-Ubuntu SMP Tue Apr 13 01:11:19 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux\n"
    elif cmd_str.startswith("cat "):
        filepath = cmd_str.split(" ", 1)[1].strip()
        # Clean paths for simulated environment
        if filepath in VFS:
            return VFS[filepath] + "\n"
        else:
            return f"cat: {filepath}: No such file or directory\n"
    elif cmd_str == "ls -la /var/www/html":
        files = list(VFS.keys())
        out = "total 16\ndrwxr-xr-x 2 www-data www-data 4096 May 21 16:00 .\ndrwxr-xr-x 3 root     root     4096 May 21 15:50 ..\n"
        for f in files:
            if f.startswith("/var/www/html/"):
                name = f.replace("/var/www/html/", "")
                out += f"-rw-r--r-- 1 www-data www-data {len(VFS[f])} May 21 16:05 {name}\n"
        return out
    elif cmd_str == "sudo -l":
        return (
            "Matching Defaults entries for www-data on public-agency-server:\n"
            "    env_reset, mail_badpass, secure_path=/usr/local/sbin\\:/usr/local/bin\\:/usr/sbin\\:/usr/bin\\:/sbin\\:/bin\n\n"
            "User www-data may run the following commands on public-agency-server:\n"
            "    (root) NOPASSWD: /usr/bin/python3\n"
        )
    elif "flag_root.txt" in cmd_str:
        return VFS["/root/flag_root.txt"] + "\n"
    elif ">" in cmd_str:
        # Handle file creation (e.g. echo 'content' > /var/www/html/backdoor.php)
        parts = cmd_str.rsplit(">", 1)
        content_part = parts[0].strip()
        dest_part = parts[1].strip()
        
        if content_part.startswith("echo "):
            val = content_part[5:].strip()
            if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
        else:
            val = content_part
            
        dest_path = dest_part.replace('"', '').replace("'", "").strip()
        with vfs_lock:
            VFS[dest_path] = val
        print(f"[DRUPAL EXPLOIT] File written: {dest_path}")
        return f"File written: {dest_path}\n"
    else:
        return f"/bin/sh: 1: {cmd_str}: not found\n"

# --- HTTP SERVICE SIMULATOR (Drupal 8.5.0) ---
def handle_http_client(client_socket, addr):
    try:
        request_data = client_socket.recv(4096)
        if not request_data:
            return
        
        request = request_data.decode("utf-8", errors="ignore")
        lines = request.split("\r\n")
        req_line = lines[0]
        parts = req_line.split(" ")
        if len(parts) < 2:
            return
        
        method, full_path = parts[0], parts[1]
        parsed_url = urllib.parse.urlparse(full_path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Read the request body for POST requests
        body = ""
        if method == "POST":
            header_body_split = request.split("\r\n\r\n", 1)
            if len(header_body_split) > 1:
                body = header_body_split[1]
            
            content_length = 0
            for line in lines:
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
                    break
            
            already_read = len(header_body_split[1].encode("utf-8")) if len(header_body_split) > 1 else 0
            if already_read < content_length:
                remaining = content_length - already_read
                body += client_socket.recv(remaining).decode("utf-8", errors="ignore")
                
        print(f"[HTTP LOG] {method} {full_path} from {addr[0]}")
        
        response_body = ""
        status_code = "200 OK"
        content_type = "text/html; charset=utf-8"
        
        # Drupalgeddon2 (CVE-2018-7600) endpoint
        if path == "/user/register" or "user/register" in path:
            if method == "POST":
                parsed_body = urllib.parse.parse_qs(body)
                mail_markup = parsed_body.get("mail[#markup]", [""])[0]
                if mail_markup:
                    cmd_output = simulate_command_execution(mail_markup)
                    # Simulate Drupal AJAX insert command response
                    response_body = (
                        '[{"command":"insert","method":"replaceWith","selector":null,'
                        f'"data":"{cmd_output.strip()}","settings":null}}]'
                    )
                    content_type = "application/json; charset=utf-8"
                else:
                    response_body = "<h1>Registration form</h1>"
            else:
                response_body = "<h1>Drupal User Registration Portal</h1>"
                
        # Accessing the written backdoor web shell
        elif path == "/backdoor.php" or path == "/var/www/html/backdoor.php":
            if "/var/www/html/backdoor.php" in VFS or "/backdoor.php" in VFS:
                cmd_param = query.get("cmd", [""])[0]
                if cmd_param:
                    response_body = simulate_command_execution(cmd_param)
                    content_type = "text/plain"
                else:
                    response_body = "PHP Backdoor active. Use ?cmd=command"
            else:
                status_code = "404 Not Found"
                response_body = "<h1>404 Not Found</h1>"
                
        elif path == "/" or path == "/index.php":
            response_body = VFS["/var/www/html/index.php"]
        else:
            if path in VFS:
                response_body = VFS[path]
                content_type = "text/plain"
            elif f"/var/www/html{path}" in VFS:
                response_body = VFS[f"/var/www/html{path}"]
                content_type = "text/plain"
            else:
                status_code = "404 Not Found"
                response_body = "<h1>404 Not Found</h1>"
        
        # Format HTTP response
        response = (
            f"HTTP/1.1 {status_code}\r\n"
            f"Server: Apache/2.4.7 (Ubuntu)\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(response_body.encode('utf-8'))}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{response_body}"
        )
        client_socket.sendall(response.encode("utf-8"))
    except Exception as e:
        print(f"[!] HTTP Error: {e}")
    finally:
        client_socket.close()

def start_http_server():
    http_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        http_server.bind(("127.0.0.1", HTTP_PORT))
        http_server.listen(5)
        print(f"[+] HTTP Web Service running on port {HTTP_PORT} (Simulating Apache 2.4.7 running Drupal 8.5.0)")
        while True:
            client, addr = http_server.accept()
            t = threading.Thread(target=handle_http_client, args=(client, addr), daemon=True)
            t.start()
    except Exception as e:
        print(f"[!] HTTP Bind Error on port {HTTP_PORT}: {e}")

# --- MYSQL SERVICE SIMULATOR ---
def handle_mysql_client(client_socket, addr):
    print(f"[*] MySQL: Connection from {addr[0]}:{addr[1]}")
    try:
        # Send a mock MySQL handshake packet
        handshake_packet = (
            b"\x4a\x00\x00\x00\x0a" # Packet length & Proto version 10
            b"5.5.47-0ubuntu0.14.04.1-log\x00" # Vulnerable MySQL version
            b"\x0b\x00\x00\x00" # Thread ID
            b"auth_salt_bytes\x00" # Salt
            b"\xff\xf7\x08\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" # Server capabilities
        )
        client_socket.sendall(handshake_packet)
        data = client_socket.recv(1024)
        print(f"[MySQL LOG] Client Auth Received ({len(data)} bytes)")
        # Reply with login success (OK packet: 7 bytes)
        client_socket.sendall(b"\x07\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00")
        time.sleep(1)
    except Exception as e:
        print(f"[!] MySQL Error: {e}")
    finally:
        client_socket.close()

def start_mysql_server():
    mysql_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mysql_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        mysql_server.bind(("127.0.0.1", MYSQL_PORT))
        mysql_server.listen(5)
        print(f"[+] MySQL Database Service running on port {MYSQL_PORT} (Simulating MySQL 5.5.47)")
        while True:
            client, addr = mysql_server.accept()
            t = threading.Thread(target=handle_mysql_client, args=(client, addr), daemon=True)
            t.start()
    except Exception as e:
        print(f"[!] MySQL Bind Error on port {MYSQL_PORT}: {e}")

# --- MAIN ---
if __name__ == "__main__":
    print("="*60)
    print("      VULNERABLE PUBLIC ORGANIZATION SERVER (SIMULATOR)      ")
    print("          NIST 800-115 TARGET ENVIRONMENT SETUP              ")
    print("="*60)
    
    t_ssh = threading.Thread(target=start_ssh_server, daemon=True)
    t_http = threading.Thread(target=start_http_server, daemon=True)
    t_mysql = threading.Thread(target=start_mysql_server, daemon=True)
    
    t_ssh.start()
    t_http.start()
    t_mysql.start()
    
    print("[*] Target system started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down vulnerable server.")
        sys.exit(0)
