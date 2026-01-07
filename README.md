# Fracttal Odometer Updater

Aplicación de escritorio para automatizar la actualización de contadores (kilómetros u horas) de activos en **Fracttal** a partir de reportes de actividad en Excel.

## 🚀 Características

- **Automatización Completa**: Lee un archivo Excel (`Resumen-de-actividad.xlsx`) y actualiza los medidores en Fracttal vía API.
- **Interfaz Moderna**: UI limpia y minimalista construida con **PyQt6**, con tema claro y fuentes modernas.
- **Prevención de Duplicados Inteligente**: Verifica automáticamente si un registro ya fue procesado mirando la columna **"Estado"** en el propio archivo Excel.
- **Feedback en Tiempo Real**: Tarjetas de estadísticas (Exitosos, Fallidos, Omitidos/Ya procesados) y terminal de logs con colores.
- **Seguridad**: Manejo de credenciales mediante variables de entorno (`.env`).
- **Soporte de Categorías**: Detecta automáticamente si debe sumar **Km** (para Flota/Camiones) u **Horas** (para Maquinaria).

## 🛠️ Requisitos

- Python 3.10 o superior
- Dependencias (listadas en `requirements.txt`):
  - `PyQt6`
  - `pandas`
  - `openpyxl`
  - `requests`
  - `python-dotenv`

## ⚙️ Instalación

1.  **Clonar el repositorio** (o descargar el código):
    ```bash
    git clone https://tu-repo/fracttal-updater.git
    cd fracttal-updater
    ```

2.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configurar credenciales:**
    Crea un archivo `.env` en la raíz del proyecto (puedes copiar `.env.example`) y agrega tus claves de API de Fracttal:
    ```ini
    FRACTTAL_API_KEY=tu_api_key_aqui
    FRACTTAL_API_SECRET=tu_api_secret_aqui
    ```

## ▶️ Uso

1.  **Ejecutar la aplicación:**
    ```bash
    python -m fracttal_updater.main
    ```

2.  **En la interfaz:**
    - Haz clic en **"Explorar"** y selecciona tu archivo de reporte Excel.
    - Haz clic en **"Iniciar Actualización"** para comenzar el proceso.
    - Puedes usar el botón **"Limpiar"** para borrar el log de la terminal.

3.  **Funcionamiento del Excel (Control de Estado):**
    - La aplicación busca (o crea) una columna llamada **"Estado"** en el Excel.
    - Cuando un activo se actualiza correctamente en Fracttal, la app escribe **"OK"** en la celda de "Estado" correspondiente.
    - Si intentas procesar el mismo archivo nuevamente, la app omitirá automáticamente las filas que tengan "OK", evitando duplicar las sumas de contadores.
    - **Para reprocesar:** Simplemente borra el contenido de la columna "Estado" o la celda específica en el Excel y guarda el archivo.

## 📂 Estructura del Proyecto

```
Actialización RSV/
├── fracttal_updater/       # Paquete principal
│   ├── main.py             # Punto de entrada
│   ├── gui.py              # Interfaz gráfica (PyQt6)
│   ├── api.py              # Comunicación con API Fracttal
│   └── processing.py       # Lógica de Excel y escritura de estados
├── .env                    # Credenciales (NO subir a GitHub)
├── .gitignore              # Archivos ignorados por Git
├── requirements.txt        # Dependencias de Python
└── README.md               # Documentación
```
