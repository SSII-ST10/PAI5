# PAI-5 RedTeamPro: Evaluación de Seguridad (NIST 800-115)

Este proyecto contiene una suite completa y autocontenida de Red Team desarrollada por el **Security Team 10** (INSEGUS) para llevar a cabo una auditoría de seguridad informática sobre una organización pública, siguiendo la metodología estándar de la guía técnica **NIST SP 800-115**.

## Estructura del Proyecto

El entregable está estructurado de la siguiente forma para facilitar la reproducibilidad de todas las pruebas realizadas:

- **`src/target/`**: Servidor vulnerable interactivo en memoria (`vulnerable_server.py`) que simula múltiples puertos abiertos y vulnerabilidades conocidas de un servidor corporativo (SSH, Apache con Drupal vulnerable, y MySQL expuesto).
- **`src/redteam/`**: Herramienta de auditoría automatizada (`redteam_tool.py`) encargada del escaneo de puertos (discovery), banner grabbing, mapeo de CVEs, explotación activa y escalada de privilegios a root.
- **`evidence/`**: Logs detallados generados durante la auditoría (`redteam_execution.log`) como evidencia técnica de reproducibilidad exigida en las normas de entrega.
- **`docs/`**: Informe técnico detallado en formatos Markdown (`Informe_Tecnico.md`), HTML interactivo (`Informe_Tecnico.html`), código fuente LaTeX (`Informe_Tecnico.tex`) y PDF compilado listo para entregar (`Informe_Tecnico.pdf`).
- **`run_audit.py`**: Script orquestador principal que levanta el entorno vulnerable, ejecuta el ataque de Red Team, graba la salida en tiempo real en la carpeta de evidencias y limpia el sistema al finalizar.
- **`build_zip.py`**: Herramienta interactiva para empaquetar automáticamente todos los archivos requeridos en el formato zip `PA5-ST<NUM>.zip`.

---

## Instrucciones de Ejecución (Reproducibilidad)

Para ejecutar la prueba de concepto completa y reproducir el informe técnico en cualquier sistema Linux/macOS sin necesidad de instalar hipervisores pesados (como VirtualBox, Vagrant o Docker), siga estos pasos:

1. **Clonar/Descargar** el repositorio.
2. Dar permisos de ejecución a los scripts:
   ```bash
   chmod +x run_audit.py src/target/vulnerable_server.py src/redteam/redteam_tool.py
   ```
3. Ejecutar el orquestador principal de la auditoría:
   ```bash
   ./run_audit.py
   ```
4. Revise el archivo `evidence/redteam_execution.log` donde se almacenarán automáticamente todas las evidencias técnicas estructuradas de la explotación.

---