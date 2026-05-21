#!/usr/bin/env python3
import socket
import threading
import sys
import time
import urllib.parse

# Configurable Ports
FTP_PORT = 2121
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
        "<!-- TODO: Deshabilitar debug.php en produccion -->\n"
        "</body>\n</html>"
    ),
    "/var/www/html/debug.php": (
        "<?php\n"
        "// Script de diagnostico interno\n"
        "if (isset($_GET['cmd'])) {\n"
        "    system($_GET['cmd']);\n"
        "}\n"
        "?>"
    ),
    "/home/redteam/flag.txt": "FLAG{REDTEAMPRO_SYSTEM_OWNED_NIST_800_115_SUCCESS}",
    "/root/flag_root.txt": "FLAG{ROOT_LEVEL_PRIVILEGE_ESCALATION_COMPLETED_CVE_2015_3306}"
}

# State variables for FTP mod_copy simulation
ftp_cpfr_source = None

# Mutex for VFS modifications
vfs_lock = threading.Lock()

# --- FTP SERVICE SIMULATOR ---
def handle_ftp_client(client_socket, addr):
    global ftp_cpfr_source
    print(f"[*] FTP: Connection from {addr[0]}:{addr[1]}")
    try:
        client_socket.sendall(b"220 ProFTPD 1.3.5 Server (ProFTPD Default Installation)\r\n")
        
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            
            cmd_line = data.decode("utf-8", errors="ignore").strip()
            if not cmd_line:
                continue
            
            parts = cmd_line.split(" ", 1)
            cmd = parts[0].upper()
            args = parts[1] if len(parts) > 1 else ""
            
            print(f"[FTP LOG] Recv: {cmd_line}")
            
            if cmd == "USER":
                client_socket.sendall(b"331 Password required for user.\r\n")
            elif cmd == "PASS":
                client_socket.sendall(b"230 User logged in, proceed.\r\n")
            elif cmd == "SYST":
                client_socket.sendall(b"215 UNIX Type: L8\r\n")
            elif cmd == "PORT" or cmd == "PASV":
                client_socket.sendall(b"200 Command okay.\r\n")
            elif cmd == "SITE":
                site_parts = args.split(" ", 1)
                site_cmd = site_parts[0].upper()
                site_args = site_parts[1] if len(site_parts) > 1 else ""
                
                if site_cmd == "CPFR":
                    if site_args in VFS:
                        ftp_cpfr_source = site_args
                        client_socket.sendall(b"350 File or directory exists, ready for destination name\r\n")
                    else:
                        client_socket.sendall(b"550 No such file or directory\r\n")
                elif site_cmd == "CPTO":
                    if not ftp_cpfr_source:
                        client_socket.sendall(b"503 Bad sequence of commands\r\n")
                    else:
                        with vfs_lock:
                            VFS[site_args] = VFS[ftp_cpfr_source]
                        print(f"[FTP EXPLOIT] Copied {ftp_cpfr_source} to {site_args}")
                        ftp_cpfr_source = None
                        client_socket.sendall(b"250 Copy successful\r\n")
                else:
                    client_socket.sendall(b"500 SITE Command not understood\r\n")
            elif cmd == "QUIT":
                client_socket.sendall(b"221 Goodbye.\r\n")
                break
            else:
                client_socket.sendall(b"500 Command not understood\r\n")
    except Exception as e:
        print(f"[!] FTP Error: {e}")
    finally:
        client_socket.close()

def start_ftp_server():
    ftp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ftp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        ftp_server.bind(("127.0.0.1", FTP_PORT))
        ftp_server.listen(5)
        print(f"[+] FTP Service running on port {FTP_PORT} (Simulating ProFTPD 1.3.5)")
        while True:
            client, addr = ftp_server.accept()
            t = threading.Thread(target=handle_ftp_client, args=(client, addr), daemon=True)
            t.start()
    except Exception as e:
        print(f"[!] FTP Bind Error on port {FTP_PORT}: {e}")

# --- HTTP SERVICE SIMULATOR ---
def simulate_command_execution(cmd_str):
    # Simulate a few Linux commands securely to make the PoC look realistic
    cmd_str = cmd_str.strip()
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
    elif cmd_str == "sudo python3 -c \"import os; os.system('cat /root/flag_root.txt')\"":
        return VFS["/root/flag_root.txt"] + "\n"
    elif cmd_str == "sudo python3 -c 'import os; os.system(\"cat /root/flag_root.txt\")'":
        return VFS["/root/flag_root.txt"] + "\n"
    elif "cat /root/flag_root.txt" in cmd_str:
        # Check privilege escalation
        return VFS["/root/flag_root.txt"] + "\n"
    else:
        return f"/bin/sh: 1: {cmd_str}: not found\n"

def handle_http_client(client_socket, addr):
    try:
        request = client_socket.recv(2048).decode("utf-8", errors="ignore")
        if not request:
            return
        
        # Simple HTTP request parser
        lines = request.split("\r\n")
        req_line = lines[0]
        parts = req_line.split(" ")
        if len(parts) < 2:
            return
        
        method, full_path = parts[0], parts[1]
        
        parsed_url = urllib.parse.urlparse(full_path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        print(f"[HTTP LOG] {method} {full_path} from {addr[0]}")
        
        # Check if the path exists in VFS or is a virtual endpoint
        response_body = ""
        status_code = "200 OK"
        content_type = "text/html; charset=utf-8"
        
        # Handle backdoor execution on files dynamically created by FTP
        if path == "/backdoor.php" or path == "/var/www/html/backdoor.php":
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
        elif path == "/debug.php" or path == "/var/www/html/debug.php":
            # Native vulnerability (RCE in debug.php)
            cmd_param = query.get("cmd", [""])[0]
            if cmd_param:
                response_body = simulate_command_execution(cmd_param)
                content_type = "text/plain"
            else:
                response_body = "Debug diagnostics. Specify ?cmd="
        elif path == "/" or path == "/index.php":
            response_body = VFS["/var/www/html/index.php"]
        else:
            # Let's search if it's in the VFS directly
            vfs_path = path
            if vfs_path in VFS:
                response_body = VFS[vfs_path]
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
        print(f"[+] HTTP Web Service running on port {HTTP_PORT} (Simulating Apache 2.4.7)")
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
        
        # Keep connection open for client commands or close gracefully
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
    
    t_ftp = threading.Thread(target=start_ftp_server, daemon=True)
    t_http = threading.Thread(target=start_http_server, daemon=True)
    t_mysql = threading.Thread(target=start_mysql_server, daemon=True)
    
    t_ftp.start()
    t_http.start()
    t_mysql.start()
    
    print("[*] Target system started. Press Ctrl+C to stop.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down vulnerable server.")
        sys.exit(0)
