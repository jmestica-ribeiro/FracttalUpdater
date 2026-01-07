"""
Entry point for the Fracttal Odometer Updater application.
"""

import sys
import os
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QMessageBox

from .gui import FracttalUpdaterApp


def main():
    """Main entry point."""
    # Load environment variables from .env file
    # Look for .env in the parent directory (Actualización RSV/)
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Get API credentials
    api_key = os.getenv("FRACTTAL_API_KEY")
    api_secret = os.getenv("FRACTTAL_API_SECRET")

    # Create application
    app = QApplication(sys.argv)

    # Validate credentials
    if not api_key or not api_secret:
        QMessageBox.critical(
            None,
            "Error de Configuración",
            "No se encontraron las credenciales de API.\n\n"
            "Por favor, cree un archivo .env en la carpeta del proyecto con:\n\n"
            "FRACTTAL_API_KEY=tu_api_key\n"
            "FRACTTAL_API_SECRET=tu_api_secret",
        )
        sys.exit(1)

    # Create and show main window
    window = FracttalUpdaterApp(api_key, api_secret)
    window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
