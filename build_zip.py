#!/usr/bin/env python3
import os
import zipfile
import sys

def build_zip():
    print("="*60)
    print("        SSII PAI5 RedTeamPro - DELIVERABLE PACKAGER          ")
    print("="*60)
    
    # Get Security Team number from command line, environment, or prompt
    team_num = "10"
    if len(sys.argv) > 1:
        team_num = sys.argv[1].strip()
    else:
        try:
            team_input = input("Ingrese el número de su Security Team [por defecto: 10]: ").strip()
            if team_input:
                team_num = team_input
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Entorno no interactivo detectado, usando valor por defecto: 10")
            team_num = "10"
            
    zip_name = f"PA5-ST{team_num}.zip"
    
    # Files to include
    files_to_pack = [
        ("run_audit.py", "run_audit.py"),
        ("build_zip.py", "build_zip.py"),
        ("README.md", "README.md"),
        ("src/target/vulnerable_server.py", "src/target/vulnerable_server.py"),
        ("src/redteam/redteam_tool.py", "src/redteam/redteam_tool.py"),
        ("evidence/redteam_execution.log", "evidence/redteam_execution.log"),
        ("docs/Informe_Tecnico.md", "docs/Informe_Tecnico.md"),
        ("docs/Informe_Tecnico.html", "docs/Informe_Tecnico.html"),
        ("docs/Informe_Tecnico.tex", "docs/Informe_Tecnico.tex"),
        ("docs/Informe_Tecnico.pdf", "docs/Informe_Tecnico.pdf")
    ]
    
    # Check if files exist
    missing_files = []
    for real_path, _ in files_to_pack:
        if not os.path.exists(real_path):
            missing_files.append(real_path)
            
    if missing_files:
        print("[!] Advertencia: Los siguientes archivos no existen en el espacio de trabajo:")
        for f in missing_files:
            print(f"  - {f}")
        print("[*] Por favor, ejecute './run_audit.py' primero para generar las evidencias.")
        
        try:
            proceed = input("¿Desea empaquetar de todas formas sin estos archivos? (s/n): ").strip().lower()
            if proceed != 's' and proceed != 'si':
                print("[*] Empaquetado cancelado.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\n[!] Operación cancelada.")
            sys.exit(1)
            
    print(f"[*] Creando archivo comprimido {zip_name}...")
    
    try:
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for real_path, archive_path in files_to_pack:
                if os.path.exists(real_path):
                    zipf.write(real_path, archive_path)
                    print(f"  [+] Añadido: {archive_path}")
                    
        print(f"\n[+] ¡Éxito! Archivo {zip_name} creado correctamente.")
        print(f"[*] Ubicación: {os.path.abspath(zip_name)}")
        print("="*60)
        
    except Exception as e:
        print(f"[!] Error al crear el archivo comprimido: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_zip()
