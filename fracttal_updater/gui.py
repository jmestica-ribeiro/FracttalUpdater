"""
Modern PyQt6 GUI for the Fracttal Odometer Updater application.
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QIcon

from .api import FracttalAPI
from .processing import load_excel, calculate_value_to_add, get_interno_and_categoria, mark_status


# Modern light color palette
COLORS = {
    "bg_dark": "#f5f5f7",       # Light gray background
    "bg_card": "#ffffff",        # White cards
    "bg_input": "#e5e5e5",       # Light gray inputs
    "accent": "#6366f1",         # Indigo
    "accent_hover": "#4f46e5",   # Darker indigo on hover
    "success": "#16a34a",        # Green
    "warning": "#d97706",        # Amber
    "error": "#dc2626",          # Red
    "text_primary": "#1f2937",   # Dark gray text
    "text_secondary": "#6b7280", # Medium gray text
    "border": "#e5e7eb",         # Light border
}


class UpdateWorker(QThread):
    """Worker thread to perform the update process without blocking the UI."""

    log_message = pyqtSignal(str, str)  # message, color
    progress_update = pyqtSignal(int, int)  # current, total
    stats_update = pyqtSignal(int, int, int, int)  # success, failed, skipped, already_processed
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, api: FracttalAPI, filepath: str):
        super().__init__()
        self.api = api
        self.filepath = filepath

    def run(self):
        """Execute the update process."""
        try:
            self.log_message.emit("Autenticando con Fracttal...", COLORS["text_secondary"])
            if not self.api.authenticate():
                self.finished_signal.emit(False, "Error de autenticación")
                return

            self.log_message.emit("✓ Autenticación exitosa", COLORS["success"])

            self.log_message.emit(f"Cargando archivo...", COLORS["text_secondary"])
            df = load_excel(self.filepath)
            total_rows = len(df)
            self.log_message.emit(f"✓ {total_rows} registros encontrados", COLORS["success"])

            successful = 0
            failed = 0
            skipped = 0
            already_processed = 0

            for idx, row in df.iterrows():
                current = idx + 1
                self.progress_update.emit(current, total_rows)

                interno, categoria = get_interno_and_categoria(row)

                if not interno or interno == "nan":
                    continue

                self.stats_update.emit(successful, failed, skipped, already_processed)

                # Check if already processed (check "Estado" column)
                estado = str(row.get("Estado", "")).strip().upper()
                if estado == "OK":
                    self.log_message.emit(f"⏭ {interno} - Ya procesado", COLORS["text_secondary"])
                    already_processed += 1
                    self.stats_update.emit(successful, failed, skipped, already_processed)
                    continue

                self.log_message.emit(f"→ {interno} ({categoria})", COLORS["text_primary"])

                contador_actual = self.api.get_meter_value(interno)

                if contador_actual is None:
                    self.log_message.emit(f"  ✗ No se encontró contador", COLORS["error"])
                    failed += 1
                    self.stats_update.emit(successful, failed, skipped, already_processed)
                    continue

                valor_a_sumar, unidad = calculate_value_to_add(row)

                if valor_a_sumar == 0:
                    self.log_message.emit(f"  ⊘ Valor 0, omitido", COLORS["warning"])
                    skipped += 1
                    self.stats_update.emit(successful, failed, skipped, already_processed)
                    continue

                nuevo_valor = contador_actual + valor_a_sumar

                self.log_message.emit(
                    f"  {contador_actual:.1f} + {valor_a_sumar:.1f} = {nuevo_valor:.1f} {unidad}",
                    COLORS["text_secondary"]
                )

                success, message = self.api.update_meter(interno, nuevo_valor)

                if success:
                    self.log_message.emit(f"  ✓ Actualizado", COLORS["success"])
                    successful += 1
                    # Mark status in Excel immediately
                    mark_status(self.filepath, idx, "OK")
                else:
                    self.log_message.emit(f"  ✗ {message}", COLORS["error"])
                    failed += 1

                self.stats_update.emit(successful, failed, skipped, already_processed)

            self.log_message.emit("", COLORS["text_primary"])
            self.log_message.emit("━" * 40, COLORS["border"])
            self.log_message.emit(f"Completado: {successful} exitosos, {failed} fallidos, {skipped} omitidos, {already_processed} ya procesados", COLORS["accent"])

            self.finished_signal.emit(True, f"{successful} exitosos, {failed} fallidos")

        except Exception as e:
            self.log_message.emit(f"Error: {e}", COLORS["error"])
            self.finished_signal.emit(False, str(e))


class StatCard(QFrame):
    """A minimal stat card widget."""

    def __init__(self, title: str, value: str = "0", color: str = COLORS["text_primary"]):
        super().__init__()
        self.color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 28px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class FracttalUpdaterApp(QMainWindow):
    """Main application window with modern minimal design."""

    def __init__(self, api_key: str, api_secret: str):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.selected_file = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        """Initialize the modern user interface."""
        self.setWindowTitle("Fracttal Updater")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS["bg_dark"]};
            }}
            QWidget {{
                font-family: 'Poppins', 'Montserrat', 'Inter', 'Segoe UI', sans-serif;
            }}
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("Actualizador de Odómetros")
        title_label.setStyleSheet(f"""
            color: {COLORS["text_primary"]};
            font-size: 24px;
            font-weight: 600;
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Status indicator
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        header_layout.addWidget(self.status_dot)

        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.stat_success = StatCard("Exitosos", "0", COLORS["success"])
        self.stat_failed = StatCard("Fallidos", "0", COLORS["error"])
        self.stat_skipped = StatCard("Omitidos", "0", COLORS["warning"])
        self.stat_already = StatCard("Ya procesados", "0", COLORS["text_secondary"])

        stats_layout.addWidget(self.stat_success)
        stats_layout.addWidget(self.stat_failed)
        stats_layout.addWidget(self.stat_skipped)
        stats_layout.addWidget(self.stat_already)

        layout.addLayout(stats_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS["bg_input"]};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["accent"]};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # File selection card
        file_card = QFrame()
        file_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["bg_card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
            }}
        """)
        file_layout = QHBoxLayout(file_card)
        file_layout.setContentsMargins(16, 16, 16, 16)

        file_icon = QLabel("📄")
        file_icon.setStyleSheet("font-size: 20px; border: none;")
        file_layout.addWidget(file_icon)

        self.file_label = QLabel("Seleccionar archivo Excel...")
        self.file_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; border: none;")
        file_layout.addWidget(self.file_label, stretch=1)

        self.select_btn = QPushButton("Explorar")
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.clicked.connect(self.select_file)
        self.select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_primary"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS["border"]};
            }}
        """)
        file_layout.addWidget(self.select_btn)

        layout.addWidget(file_card)

        # Log header with clear button
        log_header = QHBoxLayout()
        log_title = QLabel("Terminal")
        log_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 500;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.clear_btn = QPushButton("Limpiar")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_log)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS["text_secondary"]};
                border: none;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {COLORS["text_primary"]};
            }}
        """)
        log_header.addWidget(self.clear_btn)

        layout.addLayout(log_header)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS["bg_card"]};
                color: {COLORS["text_primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 13px;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(self.log_area, stretch=1)

        # Action button
        self.start_btn = QPushButton("Iniciar Actualización")
        self.start_btn.setEnabled(False)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_update)
        self.start_btn.setFixedHeight(48)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent_hover"]};
            }}
            QPushButton:disabled {{
                background-color: {COLORS["bg_input"]};
                color: {COLORS["text_secondary"]};
            }}
        """)
        layout.addWidget(self.start_btn)

    def select_file(self):
        """Open file dialog to select an Excel file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo Excel",
            "",
            "Archivos Excel (*.xlsx *.xls)",
        )

        if filepath:
            self.selected_file = filepath
            self.file_label.setText(Path(filepath).name)
            self.file_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; border: none;")
            self.start_btn.setEnabled(True)
            self.append_log(f"Archivo: {Path(filepath).name}", COLORS["text_secondary"])

    def start_update(self):
        """Start the update process."""
        if not self.selected_file:
            return

        # Reset stats
        self.stat_success.set_value("0")
        self.stat_failed.set_value("0")
        self.stat_skipped.set_value("0")
        self.stat_already.set_value("0")
        self.progress_bar.setValue(0)

        # Update status
        self.set_status("Procesando...", COLORS["warning"])

        # Disable buttons
        self.start_btn.setEnabled(False)
        self.select_btn.setEnabled(False)

        # Create API client and start worker
        api = FracttalAPI(self.api_key, self.api_secret)
        self.worker = UpdateWorker(api, self.selected_file)
        self.worker.log_message.connect(self.append_log)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.stats_update.connect(self.update_stats)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, message: str, color: str = COLORS["text_primary"]):
        """Append a colored message to the log area."""
        self.log_area.append(f'<span style="color: {color};">{message}</span>')
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current: int, total: int):
        """Update the progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def update_stats(self, success: int, failed: int, skipped: int, already: int):
        """Update the stat cards."""
        self.stat_success.set_value(str(success))
        self.stat_failed.set_value(str(failed))
        self.stat_skipped.set_value(str(skipped))
        self.stat_already.set_value(str(already))

    def clear_log(self):
        """Clear the log area."""
        self.log_area.clear()

    def set_status(self, text: str, color: str):
        """Update the status indicator."""
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px;")

    def on_finished(self, success: bool, message: str):
        """Handle completion."""
        self.start_btn.setEnabled(True)
        self.select_btn.setEnabled(True)

        if success:
            self.set_status("Completado", COLORS["success"])
        else:
            self.set_status("Error", COLORS["error"])
            QMessageBox.critical(self, "Error", message)
