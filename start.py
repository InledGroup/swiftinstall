import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Gio, Gdk, Adw
import subprocess
import os
import threading
import webbrowser
import requests
from packaging import version

# Versión actual de la aplicación
CURRENT_VERSION = "8.0"  # Esto se cambia según haya una nueva release
GITHUB_REPO = "Inled-Group/swiftinstall"

# Aplicar CSS para un estilo GNOME moderno
def load_css():
    css_provider = Gtk.CssProvider()
    
    # CSS moderno integrado para GNOME
    css_data = """
    .main-window {
        background: @window_bg_color;
    }
    
    .header-bar {
        background: @headerbar_bg_color;
        color: @headerbar_fg_color;
    }
    
    .card {
        background: @card_bg_color;
        border-radius: 12px;
        padding: 24px;
        margin: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .title-label {
        font-size: 1.2em;
        font-weight: bold;
        color: @window_fg_color;
    }
    
    .subtitle-label {
        font-size: 0.9em;
        color: @insensitive_fg_color;
    }
    
    .action-button {
        background: @accent_bg_color;
        color: @accent_fg_color;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: bold;
    }
    
    .secondary-button {
        border-radius: 8px;
        padding: 12px 24px;
    }
    
    .destructive-button {
        background: @error_bg_color;
        color: @error_fg_color;
        border-radius: 8px;
    }
    
    .search-entry {
        border-radius: 8px;
        padding: 8px 12px;
    }
    
    .progress-bar {
        border-radius: 4px;
    }
    
    .status-label {
        color: @insensitive_fg_color;
    }
    
    .list-row {
        border-radius: 8px;
        margin: 2px;
    }
    
    .file-chooser-button {
        border: 2px dashed @borders;
        border-radius: 12px;
        padding: 32px;
        background: @view_bg_color;
    }
    
    .file-chooser-button:hover {
        background: @view_hover_bg_color;
        border-color: @accent_bg_color;
    }
    """
    
    try:
        css_provider.load_from_string(css_data)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    except Exception as e:
        print(f"Error al cargar el CSS: {e}")

def safe_open_url(url):
    """Opens a URL safely with better error handling."""
    try:
        # Use subprocess instead of webbrowser for better control
        if os.name == 'posix':  # Linux/Unix
            subprocess.Popen(['xdg-open', url])
        else:  # Fallback to webbrowser
            webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Error opening URL: {str(e)}")
        return False

def get_safe_window_size(default_width, default_height, scale_factor=0.8):
    """Obtiene un tamaño de ventana seguro que no exceda los límites de la pantalla."""
    try:
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_monitors().get_item(0)
            if monitor:
                geometry = monitor.get_geometry()
                # Usar el factor de escala del ancho y altura de la pantalla
                max_width = int(geometry.width * scale_factor)
                max_height = int(geometry.height * scale_factor)
                
                # Asegurar un tamaño mínimo
                min_width = min(400, geometry.width - 100)
                min_height = min(300, geometry.height - 100)
                
                width = max(min_width, min(default_width, max_width))
                height = max(min_height, min(default_height, max_height))
                
                return width, height
    except Exception as e:
        print(f"Error obteniendo tamaño de pantalla: {e}")
    
    # Fallback a tamaño por defecto
    return default_width, default_height

def check_for_updates():
    """Comprueba las actualizaciones conectando con la API de GitHub con mejor manejo de errores."""
    try:
        # Add a user agent to avoid GitHub API rate limiting
        headers = {'User-Agent': f'SwiftInstall/{CURRENT_VERSION}'}
        
        # Add timeout and better error handling
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')
            release_url = release_data['html_url']
            
            # Comparar versiones
            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                return (True, latest_version, release_url)
            return (False, latest_version, release_url)
        elif response.status_code == 403:
            print("Rate limit exceeded or access forbidden. Check GitHub API usage.")
            return None
        else:
            print(f"Error checking for updates: HTTP {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        print("Timeout while checking for updates")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error while checking for updates")
        return None
    except Exception as e:
        print(f"Unexpected error checking for updates: {str(e)}")
        return None

class UpdateDialog(Adw.AlertDialog):
    def __init__(self, parent, latest_version, release_url):
        super().__init__()
        self.set_heading("Actualización disponible")
        self.set_body(f"Versión actual: {CURRENT_VERSION}\nNueva versión: {latest_version}")
        self.add_response("cancel", "Recordar más tarde")
        self.add_response("update", "Actualizar ahora")
        self.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("update")
        self.set_close_response("cancel")
        
        self.release_url = release_url

class SystemCleanupWindow(Adw.Window):
    def __init__(self, parent):
        super().__init__()
        self.set_title("Limpiar sistema")
        
        # Obtener tamaño seguro de ventana
        width, height = get_safe_window_size(600, 500, 0.8)
        self.set_default_size(width, height)
            
        self.set_transient_for(parent)
        self.set_modal(True)
        self.add_css_class("main-window")

        # Header bar al estilo GNOME
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Adw.WindowTitle(title="Limpiar sistema"))
        header_bar.add_css_class("header-bar")

        # Contenido principal en un ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        self.set_content(toolbar_view)

        # Contenido desplazable para que no se salga de la pantalla
        if height > 450:
            scrolled_main = Gtk.ScrolledWindow()
            scrolled_main.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled_main.set_propagate_natural_height(True)
            toolbar_view.set_content(scrolled_main)

            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            scrolled_main.set_child(main_box)
        else:
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            toolbar_view.set_content(main_box)

        # Título y descripción
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic")
        title_box.prepend(icon)
        
        title_label = Gtk.Label(label="Limpieza del sistema")
        title_label.add_css_class("title-label")
        title_box.append(title_label)
        main_box.append(title_box)
        
        desc_label = Gtk.Label(label="Dime qué quieres que limpie y te dejo el sistema reluciente")
        desc_label.add_css_class("subtitle-label")
        main_box.append(desc_label)

        # Sección de directorios a limpiar
        directories_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        directories_section.add_css_class("card")
        
        dir_title = Gtk.Label(label="Directorios a limpiar")
        dir_title.add_css_class("title-label")
        directories_section.append(dir_title)

        # Lista de checkboxes para directorios
        self.directory_checks = {}
        
        # Definir directorios comunes para limpiar
        self.cleanup_directories = {
            "~/.cache": "Caché de aplicaciones del usuario",
            "~/.local/share/Trash": "Papelera del usuario",
            "/tmp": "Archivos temporales del sistema",
            "~/.thumbnails": "Miniaturas de imágenes",
            "/var/tmp": "Archivos temporales variables", 
            "~/.config/*/logs": "Logs de aplicaciones",
            "/var/log": "Logs del sistema (requiere privilegios)",
            "~/.local/share/recently-used.xbel": "Lista de archivos recientes"
        }
        
        for directory, description in self.cleanup_directories.items():
            check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            
            check = Gtk.CheckButton()
            check.set_active(True)  # Por defecto activado
            self.directory_checks[directory] = check
            check_box.prepend(check)
            
            # Información del directorio
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            dir_label = Gtk.Label(label=directory, xalign=0)
            dir_label.add_css_class("title-label")
            info_box.append(dir_label)
            
            desc_label = Gtk.Label(label=description, xalign=0)
            desc_label.add_css_class("subtitle-label")
            info_box.append(desc_label)
            
            check_box.append(info_box)
            directories_section.append(check_box)

        main_box.append(directories_section)

        # Sección de opciones avanzadas
        advanced_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        advanced_section.add_css_class("card")
        
        adv_title = Gtk.Label(label="Opciones avanzadas")
        adv_title.add_css_class("title-label")
        advanced_section.append(adv_title)

        # Checkbox para limpiar paquetes huérfanos
        orphan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.orphan_check = Gtk.CheckButton()
        self.orphan_check.set_active(True)
        orphan_box.prepend(self.orphan_check)
        
        orphan_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        orphan_label = Gtk.Label(label="Eliminar paquetes huérfanos", xalign=0)
        orphan_label.add_css_class("title-label")
        orphan_info.append(orphan_label)
        
        orphan_desc = Gtk.Label(label="Paquetes que ya no son necesarios", xalign=0)
        orphan_desc.add_css_class("subtitle-label")
        orphan_info.append(orphan_desc)
        
        orphan_box.append(orphan_info)
        advanced_section.append(orphan_box)

        # Checkbox para limpiar caché de apt
        apt_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.apt_check = Gtk.CheckButton()
        self.apt_check.set_active(True)
        apt_box.prepend(self.apt_check)
        
        apt_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        apt_label = Gtk.Label(label="Limpiar caché de APT", xalign=0)
        apt_label.add_css_class("title-label")
        apt_info.append(apt_label)
        
        apt_desc = Gtk.Label(label="Archivos .deb descargados", xalign=0)
        apt_desc.add_css_class("subtitle-label")
        apt_info.append(apt_desc)
        
        apt_box.append(apt_info)
        advanced_section.append(apt_box)

        main_box.append(advanced_section)

        # Botones de acción
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_margin_top(16)
        
        # Botón analizar
        self.analyze_button = Gtk.Button()
        analyze_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        analyze_icon = Gtk.Image.new_from_icon_name("document-properties-symbolic")
        analyze_box.prepend(analyze_icon)
        analyze_label = Gtk.Label(label="Analizar")
        analyze_box.append(analyze_label)
        self.analyze_button.set_child(analyze_box)
        self.analyze_button.add_css_class("secondary-button")
        self.analyze_button.connect("clicked", self.on_analyze_clicked)
        button_box.append(self.analyze_button)
        
        # Botón limpiar
        self.clean_button = Gtk.Button()
        clean_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        clean_icon = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic")
        clean_box.prepend(clean_icon)
        clean_label = Gtk.Label(label="Limpiar ahora")
        clean_box.append(clean_label)
        self.clean_button.set_child(clean_box)
        self.clean_button.add_css_class("action-button")
        self.clean_button.connect("clicked", self.on_clean_clicked)
        self.clean_button.set_sensitive(False)
        button_box.append(self.clean_button)

        main_box.append(button_box)

        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("progress-bar")
        self.progress_bar.set_visible(False)
        main_box.append(self.progress_bar)

        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Selecciona las opciones y presiona 'Analizar'")
        self.status_label.add_css_class("status-label")
        main_box.append(self.status_label)

        # Variables para almacenar resultados del análisis
        self.analysis_results = {}
        self.total_size = 0

    def on_analyze_clicked(self, button):
        """Analiza el espacio que se puede liberar."""
        self.analyze_button.set_sensitive(False)
        self.clean_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Analizando archivos...")
        
        thread = threading.Thread(target=self.analyze_cleanup)
        thread.daemon = True
        thread.start()

    def analyze_cleanup(self):
        """Realiza el análisis en un hilo separado."""
        try:
            self.analysis_results = {}
            self.total_size = 0
            
            # Analizar cada directorio seleccionado
            selected_dirs = [d for d, check in self.directory_checks.items() if check.get_active()]
            total_dirs = len(selected_dirs)
            
            for i, directory in enumerate(selected_dirs):
                GLib.idle_add(self.update_progress, i / total_dirs)
                size = self.get_directory_size(directory)
                self.analysis_results[directory] = size
                self.total_size += size
            
            # Analizar paquetes huérfanos si está seleccionado
            if self.orphan_check.get_active():
                GLib.idle_add(self.update_progress, 0.8)
                orphan_size = self.get_orphan_packages_size()
                self.analysis_results["paquetes_huerfanos"] = orphan_size
                self.total_size += orphan_size
            
            # Analizar caché de APT si está seleccionado
            if self.apt_check.get_active():
                GLib.idle_add(self.update_progress, 0.9)
                apt_size = self.get_apt_cache_size()
                self.analysis_results["apt_cache"] = apt_size
                self.total_size += apt_size
            
            GLib.idle_add(self.analysis_complete)
            
        except Exception as e:
            print(f"Error en análisis: {e}")
            GLib.idle_add(self.analysis_error, str(e))

    def get_directory_size(self, directory):
        """Calcula el tamaño de un directorio."""
        import os
        total_size = 0
        try:
            # Expandir ~ y variables
            expanded_dir = os.path.expanduser(directory)
            
            if "*" in expanded_dir:
                # Manejar wildcards
                import glob
                matching_dirs = glob.glob(expanded_dir)
                for match_dir in matching_dirs:
                    if os.path.exists(match_dir):
                        total_size += self._calculate_dir_size(match_dir)
            else:
                if os.path.exists(expanded_dir):
                    total_size = self._calculate_dir_size(expanded_dir)
        except Exception as e:
            print(f"Error calculando tamaño de {directory}: {e}")
        
        return total_size

    def _calculate_dir_size(self, directory):
        """Calcula el tamaño de un directorio específico."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        pass  # Archivo inaccesible
        except Exception:
            pass
        
        return total_size

    def get_orphan_packages_size(self):
        """Estima el tamaño de los paquetes huérfanos."""
        try:
            result = subprocess.run(['apt', 'list', '--installed'], 
                                  capture_output=True, text=True, timeout=30)
            # Estimación aproximada basada en número de paquetes
            package_count = len(result.stdout.split('\n'))
            return package_count * 1024 * 1024  # 1MB promedio por paquete huérfano estimado
        except:
            return 0

    def get_apt_cache_size(self):
        """Calcula el tamaño del caché de APT."""
        return self._calculate_dir_size("/var/cache/apt/archives")

    def update_progress(self, fraction):
        """Actualiza la barra de progreso."""
        self.progress_bar.set_fraction(fraction)
        return False

    def analysis_complete(self):
        """Se ejecuta cuando el análisis está completo."""
        self.progress_bar.set_visible(False)
        self.analyze_button.set_sensitive(True)
        self.clean_button.set_sensitive(True)
        
        # Formatear el tamaño total
        size_str = self.format_size(self.total_size)
        self.status_label.set_text(f"Análisis completo. Se pueden liberar: {size_str}")
        
        return False

    def analysis_error(self, error_msg):
        """Se ejecuta si hay un error en el análisis."""
        self.progress_bar.set_visible(False)
        self.analyze_button.set_sensitive(True)
        self.status_label.set_text(f"Error en el análisis: {error_msg}")
        return False

    def format_size(self, size_bytes):
        """Formatea el tamaño en bytes a una representación legible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def on_clean_clicked(self, button):
        """Inicia el proceso de limpieza."""
        # Confirmar la limpieza
        dialog = Adw.AlertDialog(
            heading="Autorízame y yo limpio el sistema",
            body=f"Voy a limpiar el sistema.\n\nLiberaré aproximadamente: {self.format_size(self.total_size)}\n\nTen en cuenta que esta acción no se puede revertir."
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("clean", "Limpiar")
        dialog.set_response_appearance("clean", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.choose(self, None, self._on_clean_dialog_response, None)

    def _on_clean_dialog_response(self, dialog, result, data):
        """Respuesta del diálogo de confirmación de limpieza."""
        try:
            response = dialog.choose_finish(result)
            if response == "clean":
                self.start_cleanup()
        except Exception as e:
            print(f"Dialog error: {e}")

    def start_cleanup(self):
        """Inicia el proceso de limpieza."""
        self.analyze_button.set_sensitive(False)
        self.clean_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Limpiando archivos...")
        
        thread = threading.Thread(target=self.perform_cleanup)
        thread.daemon = True
        thread.start()

    def perform_cleanup(self):
        """Realiza la limpieza en un hilo separado."""
        try:
            cleaned_size = 0
            
            # Limpiar directorios seleccionados
            selected_dirs = [d for d, check in self.directory_checks.items() if check.get_active()]
            total_operations = len(selected_dirs) + (1 if self.orphan_check.get_active() else 0) + (1 if self.apt_check.get_active() else 0)
            current_op = 0
            
            for directory in selected_dirs:
                GLib.idle_add(self.update_progress, current_op / total_operations)
                cleaned_size += self.clean_directory(directory)
                current_op += 1
            
            # Limpiar paquetes huérfanos
            if self.orphan_check.get_active():
                GLib.idle_add(self.update_progress, current_op / total_operations)
                self.clean_orphan_packages()
                current_op += 1
            
            # Limpiar caché de APT
            if self.apt_check.get_active():
                GLib.idle_add(self.update_progress, current_op / total_operations)
                self.clean_apt_cache()
                current_op += 1
            
            GLib.idle_add(self.cleanup_complete, cleaned_size)
            
        except Exception as e:
            print(f"Error en limpieza: {e}")
            GLib.idle_add(self.cleanup_error, str(e))

    def clean_directory(self, directory):
        """Limpia un directorio específico."""
        import shutil
        cleaned_size = 0
        
        try:
            expanded_dir = os.path.expanduser(directory)
            
            if "*" in expanded_dir:
                import glob
                matching_dirs = glob.glob(expanded_dir)
                for match_dir in matching_dirs:
                    if os.path.exists(match_dir):
                        if os.path.isfile(match_dir):
                            size = os.path.getsize(match_dir)
                            os.remove(match_dir)
                            cleaned_size += size
                        elif os.path.isdir(match_dir):
                            size = self._calculate_dir_size(match_dir)
                            shutil.rmtree(match_dir, ignore_errors=True)
                            cleaned_size += size
            else:
                if os.path.exists(expanded_dir):
                    if os.path.isfile(expanded_dir):
                        size = os.path.getsize(expanded_dir)
                        os.remove(expanded_dir)
                        cleaned_size += size
                    elif os.path.isdir(expanded_dir):
                        # Para directorios importantes, solo limpiar el contenido
                        if directory in ["~/.cache", "/tmp", "/var/tmp", "~/.thumbnails"]:
                            for item in os.listdir(expanded_dir):
                                item_path = os.path.join(expanded_dir, item)
                                try:
                                    if os.path.isfile(item_path):
                                        size = os.path.getsize(item_path)
                                        os.remove(item_path)
                                        cleaned_size += size
                                    elif os.path.isdir(item_path):
                                        size = self._calculate_dir_size(item_path)
                                        shutil.rmtree(item_path, ignore_errors=True)
                                        cleaned_size += size
                                except:
                                    pass
                        else:
                            size = self._calculate_dir_size(expanded_dir)
                            shutil.rmtree(expanded_dir, ignore_errors=True)
                            cleaned_size += size
        except Exception as e:
            print(f"Error limpiando {directory}: {e}")
        
        return cleaned_size

    def clean_orphan_packages(self):
        """Limpia paquetes huérfanos."""
        try:
            subprocess.run(['pkexec', 'apt-get', 'autoremove', '-y'], 
                         timeout=300, capture_output=True)
        except Exception as e:
            print(f"Error limpiando paquetes huérfanos: {e}")

    def clean_apt_cache(self):
        """Limpia el caché de APT."""
        try:
            subprocess.run(['pkexec', 'apt-get', 'clean'], 
                         timeout=300, capture_output=True)
        except Exception as e:
            print(f"Error limpiando caché APT: {e}")

    def cleanup_complete(self, cleaned_size):
        """Se ejecuta cuando la limpieza está completa."""
        self.progress_bar.set_visible(False)
        self.analyze_button.set_sensitive(True)
        self.clean_button.set_sensitive(False)
        
        size_str = self.format_size(cleaned_size)
        self.status_label.set_text(f"Limpieza completada. Espacio liberado: {size_str}")
        
        # Mostrar diálogo de completado
        dialog = Adw.AlertDialog(
            heading="¡Ya he terminado!",
            body=f"He dejado impoluto tu Linux.\n\nHe liberado {size_str} que estaban ocupando espacio sin necesidad."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)
        
        return False

    def cleanup_error(self, error_msg):
        """Se ejecuta si hay un error en la limpieza."""
        self.progress_bar.set_visible(False)
        self.analyze_button.set_sensitive(True)
        self.clean_button.set_sensitive(True)
        self.status_label.set_text(f"Error en la limpieza: {error_msg}")
        
        dialog = Adw.AlertDialog(
            heading="Error en la limpieza",
            body=f"Ocurrió un error durante la limpieza:\n\n{error_msg}"
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)
        
        return False

class AntivirusWindow(Adw.Window):
    def __init__(self, parent):
        super().__init__()
        self.set_title("Análisis antivirus")
        
        # Obtener tamaño seguro de ventana
        width, height = get_safe_window_size(650, 600, 0.85)
        self.set_default_size(width, height)
            
        self.set_transient_for(parent)
        self.set_modal(True)
        self.add_css_class("main-window")

        # Header bar al estilo GNOME
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Adw.WindowTitle(title="Análisis de virus"))
        header_bar.add_css_class("header-bar")

        # Contenido principal en un ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        self.set_content(toolbar_view)

        # Crear scrolled window para el contenido principal si la ventana es muy alta
        if height > 500:  # Solo agregar scroll si la ventana es alta
            scrolled_main = Gtk.ScrolledWindow()
            scrolled_main.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled_main.set_propagate_natural_height(True)
            toolbar_view.set_content(scrolled_main)

            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            scrolled_main.set_child(main_box)
        else:
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            toolbar_view.set_content(main_box)

        # Título y descripción
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("security-high-symbolic")
        title_box.prepend(icon)
        
        title_label = Gtk.Label(label="Puedo analizar tu sistema en busca de virus.")
        title_label.add_css_class("title-label")
        title_box.append(title_label)
        main_box.append(title_box)
        
        desc_label = Gtk.Label(label="Protege tu sistema con análisis antivirus")
        desc_label.add_css_class("subtitle-label")
        main_box.append(desc_label)

        # Estado de ClamAV
        status_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        status_section.add_css_class("card")
        
        status_title = Gtk.Label(label="Estado del antivirus")
        status_title.add_css_class("title-label")
        status_section.append(status_title)

        self.clam_status_label = Gtk.Label(label="Verificando ClamAV...")
        self.clam_status_label.add_css_class("subtitle-label")
        status_section.append(self.clam_status_label)

        # Botón para instalar/actualizar ClamAV
        self.install_clam_button = Gtk.Button()
        install_clam_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        install_clam_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic")
        install_clam_box.prepend(install_clam_icon)
        install_clam_label = Gtk.Label(label="Instalar ClamAV")
        install_clam_box.append(install_clam_label)
        self.install_clam_button.set_child(install_clam_box)
        self.install_clam_button.add_css_class("action-button")
        self.install_clam_button.connect("clicked", self.on_install_clam_clicked)
        self.install_clam_button.set_visible(False)
        status_section.append(self.install_clam_button)

        main_box.append(status_section)

        # Sección de configuración del análisis
        config_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_section.add_css_class("card")
        
        config_title = Gtk.Label(label="Configuración del análisis")
        config_title.add_css_class("title-label")
        config_section.append(config_title)

        # Tipo de análisis
        scan_type_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        scan_type_label = Gtk.Label(label="Tipo de análisis:", xalign=0)
        scan_type_label.add_css_class("title-label")
        scan_type_box.append(scan_type_label)

        # Radio buttons para tipo de análisis
        self.quick_scan_radio = Gtk.CheckButton()
        self.quick_scan_radio.set_active(True)
        quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quick_box.prepend(self.quick_scan_radio)
        quick_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        quick_title = Gtk.Label(label="Análisis rápido", xalign=0)
        quick_title.add_css_class("title-label")
        quick_info.append(quick_title)
        quick_desc = Gtk.Label(label="Carpetas importantes del usuario (~, /tmp, /var/tmp)", xalign=0)
        quick_desc.add_css_class("subtitle-label")
        quick_info.append(quick_desc)
        quick_box.append(quick_info)
        scan_type_box.append(quick_box)

        self.full_scan_radio = Gtk.CheckButton()
        self.full_scan_radio.set_group(self.quick_scan_radio)
        full_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        full_box.prepend(self.full_scan_radio)
        full_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        full_title = Gtk.Label(label="Análisis completo", xalign=0)
        full_title.add_css_class("title-label")
        full_info.append(full_title)
        full_desc = Gtk.Label(label="Todo el sistema (puedo estar bastante rato trabajando)", xalign=0)
        full_desc.add_css_class("subtitle-label")
        full_info.append(full_desc)
        full_box.append(full_info)
        scan_type_box.append(full_box)

        self.custom_scan_radio = Gtk.CheckButton()
        self.custom_scan_radio.set_group(self.quick_scan_radio)
        custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        custom_box.prepend(self.custom_scan_radio)
        custom_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        custom_title = Gtk.Label(label="Análisis personalizado", xalign=0)
        custom_title.add_css_class("title-label")
        custom_info.append(custom_title)
        custom_desc = Gtk.Label(label="Selecciona los directorios que quieres que analice", xalign=0)
        custom_desc.add_css_class("subtitle-label")
        custom_info.append(custom_desc)
        custom_box.append(custom_info)
        scan_type_box.append(custom_box)

        config_section.append(scan_type_box)

        # Directorio personalizado
        self.custom_dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.custom_dir_entry = Gtk.Entry()
        self.custom_dir_entry.set_placeholder_text("Ruta del directorio a analizar...")
        self.custom_dir_entry.set_text(os.path.expanduser("~"))
        self.custom_dir_box.append(self.custom_dir_entry)
        
        browse_button = Gtk.Button()
        browse_icon = Gtk.Image.new_from_icon_name("folder-open-symbolic")
        browse_button.set_child(browse_icon)
        browse_button.connect("clicked", self.on_browse_clicked)
        self.custom_dir_box.append(browse_button)
        
        self.custom_dir_box.set_sensitive(False)
        config_section.append(self.custom_dir_box)

        # Conectar señales para habilitar/deshabilitar entrada personalizada
        self.custom_scan_radio.connect("toggled", self.on_custom_toggled)

        main_box.append(config_section)

        # Sección de opciones avanzadas
        advanced_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        advanced_section.add_css_class("card")
        
        adv_title = Gtk.Label(label="Opciones avanzadas")
        adv_title.add_css_class("title-label")
        advanced_section.append(adv_title)

        # Actualizar definiciones
        self.update_defs_check = Gtk.CheckButton()
        self.update_defs_check.set_active(True)
        update_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        update_box.prepend(self.update_defs_check)
        
        update_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        update_label = Gtk.Label(label="Actualizar definiciones antes del análisis", xalign=0)
        update_label.add_css_class("title-label")
        update_info.append(update_label)
        
        update_desc = Gtk.Label(label="Descargar las últimas actualizaciones de definiciones de virus para detectarles mejor", xalign=0)
        update_desc.add_css_class("subtitle-label")
        update_info.append(update_desc)
        
        update_box.append(update_info)
        advanced_section.append(update_box)

        # Análisis profundo
        self.deep_scan_check = Gtk.CheckButton()
        deep_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        deep_box.prepend(self.deep_scan_check)
        
        deep_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        deep_label = Gtk.Label(label="Análisis profundo", xalign=0)
        deep_label.add_css_class("title-label")
        deep_info.append(deep_label)
        
        deep_desc = Gtk.Label(label="Incluir archivos comprimidos y análisis heurístico", xalign=0)
        deep_desc.add_css_class("subtitle-label")
        deep_info.append(deep_desc)
        
        deep_box.append(deep_info)
        advanced_section.append(deep_box)

        main_box.append(advanced_section)

        # Botones de acción
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_margin_top(16)
        
        # Botón actualizar definiciones
        self.update_button = Gtk.Button()
        update_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        update_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        update_box.prepend(update_icon)
        update_label = Gtk.Label(label="Actualizar")
        update_box.append(update_label)
        self.update_button.set_child(update_box)
        self.update_button.add_css_class("secondary-button")
        self.update_button.connect("clicked", self.on_update_clicked)
        button_box.append(self.update_button)
        
        # Botón iniciar análisis
        self.scan_button = Gtk.Button()
        scan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        scan_icon = Gtk.Image.new_from_icon_name("security-high-symbolic")
        scan_box.prepend(scan_icon)
        scan_label = Gtk.Label(label="Iniciar análisis")
        scan_box.append(scan_label)
        self.scan_button.set_child(scan_box)
        self.scan_button.add_css_class("action-button")
        self.scan_button.connect("clicked", self.on_scan_clicked)
        button_box.append(self.scan_button)

        main_box.append(button_box)

        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("progress-bar")
        self.progress_bar.set_visible(False)
        main_box.append(self.progress_bar)

        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Listo para iniciar análisis")
        self.status_label.add_css_class("status-label")
        main_box.append(self.status_label)

        # Área de resultados (scrollable)
        results_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        results_section.add_css_class("card")
        
        results_title = Gtk.Label(label="Resultados del análisis")
        results_title.add_css_class("title-label")
        results_section.append(results_title)

        scrolled_results = Gtk.ScrolledWindow()
        scrolled_results.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_results.set_min_content_height(150)
        
        self.results_text = Gtk.TextView()
        self.results_text.set_editable(False)
        self.results_text.set_monospace(True)
        scrolled_results.set_child(self.results_text)
        
        results_section.append(scrolled_results)
        main_box.append(results_section)

        # Variables de estado
        self.is_clam_installed = False
        self.scan_process = None
        
        # Verificar ClamAV al iniciar
        GLib.timeout_add(500, self.check_clamav_status)

    def check_clamav_status(self):
        """Verifica si ClamAV está instalado."""
        thread = threading.Thread(target=self.check_clam_thread)
        thread.daemon = True
        thread.start()
        return False

    def check_clam_thread(self):
        """Verifica ClamAV en hilo separado."""
        try:
            # Verificar si clamscan está disponible
            result = subprocess.run(['which', 'clamscan'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # ClamAV está instalado, verificar versión
                version_result = subprocess.run(['clamscan', '--version'], 
                                              capture_output=True, text=True, timeout=10)
                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
                    GLib.idle_add(self.clam_found, version)
                else:
                    GLib.idle_add(self.clam_not_found)
            else:
                GLib.idle_add(self.clam_not_found)
                
        except Exception as e:
            print(f"Error verificando ClamAV: {e}")
            GLib.idle_add(self.clam_not_found)

    def clam_found(self, version):
        """Se ejecuta cuando ClamAV está instalado."""
        self.is_clam_installed = True
        self.clam_status_label.set_text(f"✅ ClamAV instalado: {version}")
        self.install_clam_button.set_visible(False)
        self.scan_button.set_sensitive(True)
        self.update_button.set_sensitive(True)
        return False

    def clam_not_found(self):
        """Se ejecuta cuando ClamAV no está instalado."""
        self.is_clam_installed = False
        self.clam_status_label.set_text("❌ ClamAV no está instalado")
        self.install_clam_button.set_visible(True)
        self.scan_button.set_sensitive(False)
        self.update_button.set_sensitive(False)
        return False

    def on_custom_toggled(self, button):
        """Habilita/deshabilita la entrada de directorio personalizado."""
        self.custom_dir_box.set_sensitive(self.custom_scan_radio.get_active())

    def on_browse_clicked(self, button):
        """Abre un diálogo para seleccionar directorio."""
        dialog = Gtk.FileChooserNative(
            title="Seleccionar directorio para análisis",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="Seleccionar",
            cancel_label="Cancelar"
        )
        dialog.connect("response", self._on_folder_dialog_response)
        dialog.show()

    def _on_folder_dialog_response(self, dialog, response):
        """Maneja la respuesta del diálogo de selección de carpeta."""
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                self.custom_dir_entry.set_text(file.get_path())
        dialog.destroy()

    def on_install_clam_clicked(self, button):
        """Instala ClamAV."""
        dialog = Adw.AlertDialog(
            heading="Instalar ClamAV",
            body="¿Quieres instalar ClamAV y sus definiciones de virus?\n\nEsto puede tardar varios minutos y requiere conexión a internet."
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("install", "Instalar")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        
        dialog.choose(self, None, self._on_install_clam_response, None)

    def _on_install_clam_response(self, dialog, result, data):
        """Respuesta del diálogo de instalación de ClamAV."""
        try:
            response = dialog.choose_finish(result)
            if response == "install":
                self.install_clamav()
        except Exception as e:
            print(f"Dialog error: {e}")

    def install_clamav(self):
        """Instala ClamAV."""
        self.install_clam_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Instalando ClamAV...")
        
        thread = threading.Thread(target=self.install_clam_thread)
        thread.daemon = True
        thread.start()

    def install_clam_thread(self):
        """Instala ClamAV en hilo separado."""
        try:
            # Primero intentar corregir dependencias rotas
            GLib.idle_add(self.update_status_clam, "Corrigiendo dependencias...")
            fix_process = subprocess.Popen(['pkexec', 'apt-get', '--fix-broken', 'install', '-y'],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = fix_process.stdout.readline()
                if output == '' and fix_process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_install_progress)
            
            fix_process.communicate()
            
            # Actualizar repositorios
            GLib.idle_add(self.update_status_clam, "Actualizando repositorios...")
            update_process = subprocess.Popen(['pkexec', 'apt-get', 'update'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            update_process.communicate()
            
            # Instalar ClamAV
            GLib.idle_add(self.update_status_clam, "Instalando ClamAV...")
            install_process = subprocess.Popen(['pkexec', 'apt-get', 'install', '-y', 'clamav', 'clamav-daemon', 'clamav-freshclam'],
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = install_process.stdout.readline()
                if output == '' and install_process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_install_progress)
            
            _, stderr = install_process.communicate()
            
            if install_process.returncode == 0:
                GLib.idle_add(self.install_clam_complete, True)
            else:
                # Si falla, intentar una vez más con autoremove y fix
                GLib.idle_add(self.update_status_clam, "Reintentando instalación...")
                
                # Limpiar paquetes huérfanos
                subprocess.run(['pkexec', 'apt-get', 'autoremove', '-y'], 
                             capture_output=True, timeout=120)
                
                # Intentar instalar de nuevo
                retry_process = subprocess.Popen(['pkexec', 'apt-get', 'install', '-y', '--fix-missing', 'clamav', 'clamav-daemon', 'clamav-freshclam'],
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                
                while True:
                    output = retry_process.stdout.readline()
                    if output == '' and retry_process.poll() is not None:
                        break
                    if output:
                        GLib.idle_add(self.update_install_progress)
                
                _, retry_stderr = retry_process.communicate()
                
                if retry_process.returncode == 0:
                    GLib.idle_add(self.install_clam_complete, True)
                else:
                    GLib.idle_add(self.install_clam_complete, False, f"Error original: {stderr}\nError reintento: {retry_stderr}")
                
        except Exception as e:
            GLib.idle_add(self.install_clam_complete, False, str(e))

    def update_status_clam(self, message):
        """Actualiza el mensaje de estado durante la instalación."""
        self.status_label.set_text(message)
        return False

    def update_install_progress(self):
        """Actualiza la barra de progreso de instalación."""
        current = self.progress_bar.get_fraction()
        new_value = min(1.0, current + 0.02)
        self.progress_bar.set_fraction(new_value)
        return False

    def install_clam_complete(self, success, error_msg=""):
        """Se ejecuta cuando la instalación de ClamAV termina."""
        self.progress_bar.set_visible(False)
        self.install_clam_button.set_sensitive(True)
        
        if success:
            self.status_label.set_text("ClamAV instalado correctamente")
            # Volver a verificar el estado
            GLib.timeout_add(1000, self.check_clamav_status)
        else:
            self.status_label.set_text(f"Error instalando ClamAV: {error_msg}")
            
        return False

    def on_update_clicked(self, button):
        """Actualiza las definiciones de virus."""
        self.update_button.set_sensitive(False)
        self.scan_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Actualizando definiciones de virus...")
        
        thread = threading.Thread(target=self.update_definitions_thread)
        thread.daemon = True
        thread.start()

    def update_definitions_thread(self):
        """Actualiza las definiciones en hilo separado."""
        try:
            process = subprocess.Popen(['pkexec', 'freshclam'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_definitions_progress)
            
            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.update_definitions_complete, True)
            else:
                GLib.idle_add(self.update_definitions_complete, False, stderr)
                
        except Exception as e:
            GLib.idle_add(self.update_definitions_complete, False, str(e))

    def update_definitions_progress(self):
        """Actualiza el progreso de actualización de definiciones."""
        current = self.progress_bar.get_fraction()
        new_value = min(1.0, current + 0.05)
        self.progress_bar.set_fraction(new_value)
        return False

    def update_definitions_complete(self, success, error_msg=""):
        """Se ejecuta cuando la actualización de definiciones termina."""
        self.progress_bar.set_visible(False)
        self.update_button.set_sensitive(True)
        self.scan_button.set_sensitive(True)
        
        if success:
            self.status_label.set_text("Definiciones actualizadas correctamente")
        else:
            self.status_label.set_text(f"Error actualizando definiciones: {error_msg}")
            
        return False

    def on_scan_clicked(self, button):
        """Inicia el análisis antivirus."""
        # Actualizar definiciones si está marcado
        if self.update_defs_check.get_active():
            self.on_update_clicked(button)
            # Esperar un momento y luego iniciar el análisis
            GLib.timeout_add(2000, self.start_scan_after_update)
        else:
            self.start_scan()

    def start_scan_after_update(self):
        """Inicia el análisis después de actualizar definiciones."""
        if not self.progress_bar.get_visible():  # Esperar a que termine la actualización
            self.start_scan()
            return False
        return True  # Continuar esperando

    def start_scan(self):
        """Inicia el análisis antivirus."""
        self.scan_button.set_sensitive(False)
        self.update_button.set_sensitive(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.status_label.set_text("Iniciando análisis antivirus...")
        
        # Limpiar resultados anteriores
        buffer = self.results_text.get_buffer()
        buffer.set_text("")
        
        thread = threading.Thread(target=self.scan_thread)
        thread.daemon = True
        thread.start()

    def scan_thread(self):
        """Ejecuta el análisis antivirus en hilo separado."""
        try:
            # Determinar qué analizar
            if self.quick_scan_radio.get_active():
                scan_paths = [os.path.expanduser("~"), "/tmp", "/var/tmp"]
            elif self.full_scan_radio.get_active():
                scan_paths = ["/"]
            else:  # custom scan
                scan_paths = [self.custom_dir_entry.get_text()]
            
            # Construir comando clamscan
            cmd = ['clamscan', '-r', '--no-summary']
            
            if self.deep_scan_check.get_active():
                cmd.extend(['--scan-archive', '--heuristic-scan-precedence'])
            
            cmd.extend(scan_paths)
            
            GLib.idle_add(self.append_result, f"Ejecutando: {' '.join(cmd)}\n\n")
            
            self.scan_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE, universal_newlines=True)
            
            infected_files = []
            scanned_files = 0
            
            while True:
                output = self.scan_process.stdout.readline()
                if output == '' and self.scan_process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    scanned_files += 1
                    
                    # Actualizar progreso cada 100 archivos
                    if scanned_files % 100 == 0:
                        GLib.idle_add(self.update_scan_progress)
                    
                    # Mostrar archivos infectados
                    if "FOUND" in line:
                        infected_files.append(line)
                        GLib.idle_add(self.append_result, f"🦠 INFECTADO: {line}\n")
                    elif scanned_files % 1000 == 0:  # Mostrar progreso cada 1000 archivos
                        GLib.idle_add(self.append_result, f"Analizados: {scanned_files} archivos...\n")
            
            _, stderr = self.scan_process.communicate()
            
            GLib.idle_add(self.scan_complete, len(infected_files), scanned_files, stderr)
            
        except Exception as e:
            GLib.idle_add(self.scan_error, str(e))

    def update_scan_progress(self):
        """Actualiza el progreso del análisis."""
        current = self.progress_bar.get_fraction()
        # Progreso más lento para análisis largos
        new_value = min(0.95, current + 0.01)
        self.progress_bar.set_fraction(new_value)
        return False

    def append_result(self, text):
        """Añade texto a los resultados."""
        buffer = self.results_text.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, text)
        
        # Scroll hacia abajo
        mark = buffer.get_insert()
        self.results_text.scroll_to_mark(mark, 0.0, False, 0.0, 0.0)
        return False

    def scan_complete(self, infected_count, scanned_count, stderr):
        """Se ejecuta cuando el análisis termina."""
        self.progress_bar.set_fraction(1.0)
        self.scan_button.set_sensitive(True)
        self.update_button.set_sensitive(True)
        
        if infected_count == 0:
            status = f"✅ Análisis completado. He revisado {scanned_count} archivos y no he encontrado amenazas. Puedes estar tranquilo."
            GLib.idle_add(self.append_result, f"\n{status}\n")
        else:
            status = f"⚠️ ¡Cuidado! He pillado amenazas que puede que te la estén liando... He encontrado {infected_count} amenazas en {scanned_count} archivos analizados. Para evitar problemas toma medidas. Recomendamos realizar una reinstalación siempre que se encuentren virus."
            GLib.idle_add(self.append_result, f"\n{status}\n")
            
            # Mostrar diálogo con opciones de limpieza
            self.show_threat_dialog(infected_count)
        
        self.status_label.set_text(status)
        
        GLib.timeout_add(2000, self.hide_progress_bar)
        return False

    def hide_progress_bar(self):
        """Oculta la barra de progreso."""
        self.progress_bar.set_visible(False)
        return False

    def show_threat_dialog(self, threat_count):
        """Muestra diálogo cuando se encuentran amenazas."""
        dialog = Adw.AlertDialog(
            heading="⚠️ ¡Cuidado!",
            body=f"He detectado {threat_count} amenazas en tu sistema.\n\n¿Qué quieres hacer?"
        )
        dialog.add_response("ignore", "Ignorar")
        dialog.add_response("quarantine", "Poner en cuarentena")
        dialog.add_response("delete", "Eliminar amenazas")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("quarantine", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("quarantine")
        dialog.set_close_response("ignore")
        
        dialog.choose(self, None, self._on_threat_dialog_response, None)

    def _on_threat_dialog_response(self, dialog, result, data):
        """Respuesta del diálogo de amenazas."""
        try:
            response = dialog.choose_finish(result)
            if response == "quarantine":
                self.append_result("\n🔒 Poniendo amenazas en cuarentena...\n")
                # Aquí se implementaría la cuarentena
                self.append_result("Funcionalidad de cuarentena no implementada aún.\n")
            elif response == "delete":
                self.append_result("\n🗑️ Eliminando amenazas...\n")
                # Aquí se implementaría la eliminación
                self.append_result("Funcionalidad de eliminación no implementada aún.\n")
        except Exception as e:
            print(f"Dialog error: {e}")

    def scan_error(self, error_msg):
        """Se ejecuta si hay un error en el análisis."""
        self.progress_bar.set_visible(False)
        self.scan_button.set_sensitive(True)
        self.update_button.set_sensitive(True)
        self.status_label.set_text(f"Error en el análisis: {error_msg}")
        GLib.idle_add(self.append_result, f"\n❌ Error: {error_msg}\n")
        return False

class InstalledAppsWindow(Adw.Window):
    def __init__(self, parent):
        super().__init__()
        self.set_title("Aplicaciones instaladas")
        
        # Obtener tamaño seguro de ventana
        width, height = get_safe_window_size(500, 400, 0.7)
        self.set_default_size(width, height)
            
        self.set_transient_for(parent)
        self.set_modal(True)
        self.add_css_class("main-window")

        # Header bar al estilo GNOME
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Adw.WindowTitle(title="Aplicaciones instaladas"))
        header_bar.add_css_class("header-bar")

        # Contenido principal en un ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        self.set_content(toolbar_view)

        # Contenido desplazable para pantallas pequeñas
        if height > 380:
            scrolled_main = Gtk.ScrolledWindow()
            scrolled_main.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled_main.set_propagate_natural_height(True)
            toolbar_view.set_content(scrolled_main)

            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            scrolled_main.set_child(main_box)
        else:
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            main_box.set_margin_top(16)
            main_box.set_margin_bottom(16)
            main_box.set_margin_start(16)
            main_box.set_margin_end(16)
            toolbar_view.set_content(main_box)

        # Barra de búsqueda con icono
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        search_box.prepend(search_icon)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar aplicaciones...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.add_css_class("search-entry")
        search_box.append(self.search_entry)
        
        main_box.append(search_box)

        # Tarjeta para la lista de aplicaciones
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("card")
        main_box.append(card)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(300)
        card.append(scrolled_window)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_filter_func(self.filter_func)
        scrolled_window.set_child(self.listbox)
        
        # Barra de progreso
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        progress_box.set_margin_top(16)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("progress-bar")
        progress_box.append(self.progress_bar)
        
        main_box.append(progress_box)
        self.progress_bar.set_visible(False)

        # Mensaje de estado
        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("status-label")
        main_box.append(self.status_label)
        
        # Cargar aplicaciones
        self.load_installed_apps()
    
    def load_installed_apps(self):
        # Limpiar la lista actual
        child = self.listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.listbox.remove(child)
            child = next_child
            
        # Mostrar un spinner mientras se cargan las aplicaciones
        spinner = Gtk.Spinner()
        spinner.start()
        spinner_row = Gtk.ListBoxRow()
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        spinner_box.set_margin_top(12)
        spinner_box.set_margin_bottom(12)
        spinner_box.append(spinner)
        spinner_row.set_child(spinner_box)
        self.listbox.append(spinner_row)
        
        # Iniciar un hilo para cargar las aplicaciones
        thread = threading.Thread(target=self.load_apps_thread)
        thread.daemon = True
        thread.start()
    
    def load_apps_thread(self):
        try:
            # Obtener paquetes instalados
            packages = []
            appimages = []
            
            # Obtener paquetes del sistema
            try:
                output = subprocess.check_output(['dpkg', '--get-selections'], 
                                               timeout=10).decode('utf-8')
                packages = [line.split()[0] for line in output.split('\n') if line.strip()]
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"Error al obtener paquetes: {e}")
            
            # Obtener AppImages
            desktop_dir = "/usr/share/applications"
            if os.path.exists(desktop_dir):
                for filename in os.listdir(desktop_dir):
                    if filename.endswith(".desktop"):
                        desktop_path = os.path.join(desktop_dir, filename)
                        try:
                            with open(desktop_path, 'r') as f:
                                content = f.read()
                                if "/usr/bin/" in content and "appimage.png" in content:
                                    app_name = filename.replace(".desktop", "")
                                    appimages.append(app_name)
                        except:
                            pass
            
            # Actualizar la UI en lotes para evitar sobrecargar el bucle principal
            def update_ui_with_packages():
                # Eliminar el spinner
                child = self.listbox.get_first_child()
                while child:
                    next_child = child.get_next_sibling()
                    child_widget = child.get_child()
                    if isinstance(child_widget, Gtk.Box):
                        first_grandchild = child_widget.get_first_child()
                        if isinstance(first_grandchild, Gtk.Spinner):
                            self.listbox.remove(child)
                            break
                    child = next_child
                
                # Añadir paquetes en lotes
                batch_size = 50
                for i in range(0, len(packages), batch_size):
                    batch = packages[i:i+batch_size]
                    for package_name in batch:
                        self.add_app_to_list(package_name, False)
                    
                    # Permitir que la UI se actualice entre lotes
                    # En GTK 4, esto se maneja automáticamente
                
                # Añadir AppImages
                for app_name in appimages:
                    self.add_app_to_list(app_name, True)
                
                # Mostrar mensaje si no se encontraron aplicaciones
                if not packages and not appimages:
                    self.show_no_apps_message()
                
                return False
            
            # Programar la actualización de la UI en el hilo principal
            GLib.idle_add(update_ui_with_packages)
            
        except Exception as e:
            print(f"Error al cargar aplicaciones: {e}")
            GLib.idle_add(self.show_error_message)
    
    def add_app_to_list(self, package_name, is_appimage=False):
        """Añadir una aplicación a la lista"""
        row = Gtk.ListBoxRow()
        row.add_css_class("list-row")
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        row.set_child(hbox)
        
        # Icono para el tipo de aplicación
        icon_name = "package-x-generic" if not is_appimage else "application-x-executable"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        hbox.prepend(icon)
        
        # Nombre a mostrar
        display_name = package_name
        
        # Contenedor vertical para nombre y tipo
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        label = Gtk.Label(label=display_name, xalign=0)
        label.add_css_class("title-label")
        vbox.append(label)
        
        # Etiqueta para el tipo
        type_label = Gtk.Label(label="AppImage" if is_appimage else "Paquete instalado", xalign=0)
        type_label.add_css_class("subtitle-label")
        vbox.append(type_label)
        
        hbox.append(vbox)
        
        # Botón de desinstalar con icono
        button = Gtk.Button()
        button.set_tooltip_text("Desinstalar")
        button.add_css_class("destructive-button")
        
        button_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic")
        button.set_child(button_icon)
        
        button.connect("clicked", self.on_uninstall_clicked, package_name, is_appimage)
        hbox.append(button)
        
        self.listbox.append(row)
    
    # Mensaje de que no hay aplicaciones instaladas en el sistema (clara prueba de que está habiendo un error)
    def show_no_apps_message(self):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        
        icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        box.append(icon)
        
        label = Gtk.Label(label="No he encontrado aplicaciones instaladas en tu sistema")
        label.get_style_context().add_class("title-label")
        box.append(label)
        
        row.add(box)
        self.listbox.add(row)
        return False
    
    def show_error_message(self):
        # Eliminar el spinner si existe
        child = self.listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            child_widget = child.get_child()
            if isinstance(child_widget, Gtk.Box):
                first_grandchild = child_widget.get_first_child()
                if isinstance(first_grandchild, Gtk.Spinner):
                    self.listbox.remove(child)
                    break
            child = next_child
        
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        
        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
        box.append(icon)
        
        label = Gtk.Label(label="No he podido encontrar aplicaciones instaladas en tu sistema")
        label.get_style_context().add_class("title-label")
        box.append(label)
        
        row.add(box)
        self.listbox.add(row)
        return False
    
    def on_search_changed(self, entry):
        self.listbox.invalidate_filter()
    
    def filter_func(self, row):
        text = self.search_entry.get_text().lower()
        if not text:
            return True
        
        # Buscar en el título de la aplicación
        box = row.get_child()
        if box and isinstance(box, Gtk.Box):
            child = box.get_first_child()
            while child:
                if isinstance(child, Gtk.Box) and child.get_orientation() == Gtk.Orientation.VERTICAL:
                    label_child = child.get_first_child()
                    while label_child:
                        if isinstance(label_child, Gtk.Label) and hasattr(label_child, 'get_text'):
                            if text in label_child.get_text().lower():
                                return True
                        label_child = label_child.get_next_sibling()
                child = child.get_next_sibling()
        return False
    
    # Aviso desinstalación
    def on_uninstall_clicked(self, button, package_name, is_appimage=False):
        if is_appimage:
            message = f"¿Deseas desinstalar {package_name}?"
        else:
            message = f"¿Deseas desinstalar {package_name}?"
            
        dialog = Adw.AlertDialog(
            heading="Confirmación",
            body=message
        )
        dialog.add_response("no", "No")
        dialog.add_response("yes", "Sí")
        dialog.set_response_appearance("yes", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("no")
        dialog.set_close_response("no")
        
        
        # Los botones ya se han estilizado en la configuración del AlertDialog
        
        dialog.choose(self, None, self._on_uninstall_dialog_response, (package_name, is_appimage))
    
    def _on_uninstall_dialog_response(self, dialog, result, data):
        package_name, is_appimage = data
        try:
            response = dialog.choose_finish(result)
            if response == "yes":
                self.uninstall_package(package_name, is_appimage)
        except Exception as e:
            print(f"Dialog error: {e}")
    
    # Desinstalar paquete
    def uninstall_package(self, package_name, is_appimage=False):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_visible(True)
        self.status_label.set_text(f"Desinstalando {package_name}...")
        
        if is_appimage:
            # Eliminar el AppImage y su archivo .desktop
            cmd = [
                'pkexec', 'bash', '-c',
                f'rm -f /usr/bin/{package_name} && ' +
                f'rm -f /usr/share/applications/{package_name}.desktop'
            ]
        else:
            # Eliminar un paquete normal
            cmd = ['pkexec', 'apt-get', 'remove', '-y', package_name]
            
        thread = threading.Thread(target=self.run_uninstall, args=(cmd, package_name, is_appimage))
        thread.daemon = True
        thread.start()
    
    def run_uninstall(self, cmd, package_name, is_appimage=False):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_uninstall_progress)
            
            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.uninstall_complete, package_name, True, is_appimage)
            else:
                GLib.idle_add(self.uninstall_complete, package_name, False, is_appimage, str(stderr))
        except subprocess.CalledProcessError as e:
            GLib.idle_add(self.uninstall_complete, package_name, False, is_appimage, str(e))
    
    # Barra de progreso de la desinstalación
    def update_uninstall_progress(self):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.05)
        self.progress_bar.set_fraction(new_value)
        return False

    # Mensaje después de ejecutar la desinstalación
    def uninstall_complete(self, package_name, success, is_appimage=False, error_message=None):
        self.progress_bar.set_visible(False)
        self.progress_bar.set_fraction(0.0)
        
        if success:
            if is_appimage:
                message = f"{package_name} ha sido desinstalado correctamente. Recuerda borrar los archivos que haya creado la aplicación."
            else:
                message = f"{package_name} ha sido desinstalado correctamente."
                
            dialog = Adw.AlertDialog(
                heading="Desinstalación completada",
                body=message
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            self.status_label.set_text("Desinstalación completada")
        else:
            if is_appimage:
                message = f"Error al desinstalar Swiftinstall Enhance AppImage - {package_name}."
            else:
                message = f"Error al desinstalar {package_name}."
                
            dialog = Adw.AlertDialog(
                heading="Error en la desinstalación",
                body=f"{message}\n\n{error_message or ''}"
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            self.status_label.set_text("Uy... ha habido un error cuando estaba desinstalándote la app")
        
        
        dialog.present(self)
        self.load_installed_apps()  # Refrescar la lista


class PackageInstaller(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Swift Install")
        # Ajustar tamaño de ventana principal a la pantalla
        width, height = get_safe_window_size(600, 500, 0.9)
        self.set_default_size(width, height)
        self.add_css_class("main-window")
        
        # Header bar al estilo GNOME
        header_bar = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title="Swift Install", subtitle=f"Versión {CURRENT_VERSION}")
        header_bar.set_title_widget(title_widget)
        header_bar.add_css_class("header-bar")
        
        # Botón de menú en la header bar
        menu_button = Gtk.MenuButton()
        menu_button.set_tooltip_text("Menú")
        icon = Gtk.Image.new_from_icon_name("open-menu-symbolic")
        menu_button.set_child(icon)
        
        # Crear el menú
        popover = Gtk.Popover()
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        popover_box.set_margin_top(10)
        popover_box.set_margin_bottom(10)
        popover_box.set_margin_start(10)
        popover_box.set_margin_end(10)
        
        # Elementos del menú
        about_button = Gtk.Button(label="Acerca de Swift Install")
        about_button.connect("clicked", self.on_about_clicked)
        popover_box.append(about_button)
        
        report_button = Gtk.Button(label="Reportar un error")
        report_button.connect("clicked", self.on_report_issue)
        popover_box.append(report_button)
        
        update_button = Gtk.Button(label="Buscar actualizaciones")
        update_button.connect("clicked", self.on_check_updates_clicked)
        popover_box.append(update_button)
        
        popover.set_child(popover_box)
        menu_button.set_popover(popover)
        
        header_bar.pack_end(menu_button)
        
        # Contenido principal en un ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        self.set_content(toolbar_view)

        # Contenido principal con scroll si es necesario
        if height > 500:
            scrolled_main = Gtk.ScrolledWindow()
            scrolled_main.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled_main.set_propagate_natural_height(True)
            toolbar_view.set_content(scrolled_main)

            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
            main_box.set_margin_top(24)
            main_box.set_margin_bottom(24)
            main_box.set_margin_start(24)
            main_box.set_margin_end(24)
            scrolled_main.set_child(main_box)
        else:
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
            main_box.set_margin_top(24)
            main_box.set_margin_bottom(24)
            main_box.set_margin_start(24)
            main_box.set_margin_end(24)
            toolbar_view.set_content(main_box)

        # Sección de selección de archivo
        file_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        file_section.add_css_class("card")
        
        # Título de la sección
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("package-x-generic-symbolic")
        title_box.prepend(icon)
        
        title_label = Gtk.Label(label="¿Qué debo instalar?")
        title_label.add_css_class("title-label")
        title_box.append(title_label)
        
        file_section.append(title_box)
        
        # Selector de archivo con estilo
        file_chooser_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        file_chooser_box.add_css_class("file-chooser-button")
        
        file_icon = Gtk.Image.new_from_icon_name("document-open-symbolic")
        file_chooser_box.append(file_icon)
        
        file_label = Gtk.Label(label="Selecciona el archivo que debo instalar")
        file_label.add_css_class("subtitle-label")
        file_chooser_box.append(file_label)
        
        file_chooser_button = Gtk.Button()
        file_chooser_button.set_child(file_chooser_box)
        file_chooser_button.connect("clicked", self.on_file_chooser_clicked)
        
        file_section.append(file_chooser_button)
        
        # Etiqueta para mostrar el archivo seleccionado
        self.selected_file_label = Gtk.Label(label="Aún no has seleccionado ningún archivo")
        self.selected_file_label.add_css_class("subtitle-label")
        file_section.append(self.selected_file_label)
        
        main_box.append(file_section)
        
        # Sección de acciones
        actions_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        actions_section.add_css_class("card")
        
        # Título de la sección
        actions_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_icon = Gtk.Image.new_from_icon_name("preferences-other-symbolic")
        actions_title_box.prepend(actions_icon)
        
        actions_title_label = Gtk.Label(label="Acciones")
        actions_title_label.add_css_class("title-label")
        actions_title_box.append(actions_title_label)
        
        actions_section.append(actions_title_box)
        
        # Botones de acción - Primera fila
        buttons_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons_box1.set_homogeneous(True)
        
        # Botón de instalar - CORREGIDO: sin label en el constructor
        self.install_button = Gtk.Button()
        self.install_button.add_css_class("action-button")
        install_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        install_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic")
        install_box.prepend(install_icon)
        install_label = Gtk.Label(label="Instalar")
        install_box.append(install_label)
        self.install_button.set_child(install_box)
        self.install_button.connect("clicked", self.on_install_clicked)
        self.install_button.set_sensitive(False)
        buttons_box1.append(self.install_button)
        
        # Botón de corregir errores - CORREGIDO: sin label en el constructor
        self.fix_deps_button = Gtk.Button()
        self.fix_deps_button.add_css_class("secondary-button")
        fix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fix_icon = Gtk.Image.new_from_icon_name("applications-utilities-symbolic")
        fix_box.prepend(fix_icon)
        fix_label = Gtk.Label(label="Corregir errores")
        fix_box.append(fix_label)
        self.fix_deps_button.set_child(fix_box)
        self.fix_deps_button.connect("clicked", self.on_fix_deps_clicked)
        buttons_box1.append(self.fix_deps_button)
        
        actions_section.append(buttons_box1)
        
        # Segunda fila de botones
        buttons_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons_box2.set_homogeneous(True)
        
        # Botón de eliminar aplicaciones - CORREGIDO: sin label en el constructor
        self.apps_button = Gtk.Button()
        self.apps_button.add_css_class("secondary-button")
        apps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apps_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic")
        apps_box.prepend(apps_icon)
        apps_label = Gtk.Label(label="Eliminar apps")
        apps_box.append(apps_label)
        self.apps_button.set_child(apps_box)
        self.apps_button.connect("clicked", self.on_apps_clicked)
        buttons_box2.append(self.apps_button)
        
        # Botón de limpiar sistema - NUEVO
        self.clean_button = Gtk.Button()
        self.clean_button.add_css_class("secondary-button")
        clean_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        clean_icon = Gtk.Image.new_from_icon_name("edit-clear-all-symbolic")
        clean_box.prepend(clean_icon)
        clean_label = Gtk.Label(label="Limpiar sistema")
        clean_box.append(clean_label)
        self.clean_button.set_child(clean_box)
        self.clean_button.connect("clicked", self.on_clean_clicked)
        buttons_box2.append(self.clean_button)
        
        actions_section.append(buttons_box2)
        
        # Tercera fila de botones
        buttons_box3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons_box3.set_homogeneous(True)
        
        # Botón de análisis antivirus - NUEVO
        self.antivirus_button = Gtk.Button()
        self.antivirus_button.add_css_class("secondary-button")
        antivirus_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        antivirus_icon = Gtk.Image.new_from_icon_name("security-high-symbolic")
        antivirus_box.prepend(antivirus_icon)
        antivirus_label = Gtk.Label(label="Análisis antivirus")
        antivirus_box.append(antivirus_label)
        self.antivirus_button.set_child(antivirus_box)
        self.antivirus_button.connect("clicked", self.on_antivirus_clicked)
        buttons_box3.append(self.antivirus_button)
        
        # Placeholder para futuro botón (mantener simetría)
        placeholder_button = Gtk.Box()  # Caja vacía para mantener el espaciado
        buttons_box3.append(placeholder_button)
        
        actions_section.append(buttons_box2)
        actions_section.append(buttons_box3)
        main_box.append(actions_section)
        
        # Sección de progreso
        progress_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        progress_section.add_css_class("card")
        
        # Título de la sección
        progress_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        progress_icon = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic")
        progress_title_box.prepend(progress_icon)
        
        progress_title_label = Gtk.Label(label="Progreso")
        progress_title_label.add_css_class("title-label")
        progress_title_box.append(progress_title_label)
        
        progress_section.append(progress_title_box)
        
        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.add_css_class("progress-bar")
        progress_section.append(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Empieza seleccionando un archivo que contenga una app")
        self.status_label.add_css_class("status-label")
        progress_section.append(self.status_label)
        
        main_box.append(progress_section)

        self.installed_package = None
        self.file_path = None
        
        # Comprobar actualizaciones al iniciar la aplicación
        GLib.timeout_add(500, self.check_updates_on_startup)
    
    def on_file_chooser_clicked(self, button):
        dialog = Gtk.FileChooserNative(
            title="Seleccionar paquete",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Abrir",
            cancel_label="Cancelar"
        )
        
        # En GTK 4, los filtros se pueden configurar opcionalmente
        # El FileChooserNative funciona sin filtros explícitos
        
        dialog.connect("response", self._on_file_dialog_response)
        dialog.show()
    
    def _on_file_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                self.file_path = file.get_path()
                self.selected_file_label.set_text(f"Archivo seleccionado: {os.path.basename(self.file_path)}")
                self.install_button.set_sensitive(True)
                self.status_label.set_text(f"Estoy listo para instalar: {os.path.basename(self.file_path)}")
        dialog.destroy()

    def create_desktop_file(self, app_name):
        # Obtener la ruta del icono
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appimage.png")
        
        # Crear el contenido del archivo .desktop
        desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_name}
Exec=/usr/bin/{app_name}
Icon={icon_path}
Terminal=false
Categories=Utility;
"""
        
        # Comando para crear el archivo .desktop
        desktop_path = f"/usr/share/applications/{app_name}.desktop"
        return f"echo '{desktop_content}' > {desktop_path}"

    def check_updates_on_startup(self):
        thread = threading.Thread(target=self.check_updates_thread)
        thread.daemon = True
        thread.start()
        return False  # No repetir el timeout
    
    def check_updates_thread(self):
        update_info = check_for_updates()
        if update_info:
            has_update, latest_version, release_url = update_info
            if has_update:
                GLib.idle_add(self.show_update_dialog, latest_version, release_url)
    
    def show_update_dialog(self, latest_version, release_url):
        dialog = UpdateDialog(self, latest_version, release_url)
        dialog.choose(self, None, self._on_update_dialog_response, release_url)
        return False
    
    def _on_update_dialog_response(self, dialog, result, release_url):
        try:
            response = dialog.choose_finish(result)
            if response == "update":
                safe_open_url(release_url)
        except Exception as e:
            print(f"Dialog error: {e}")
    
    def on_check_updates_clicked(self, widget):
        self.status_label.set_text("Estoy comprobando las actualizaciones")
        thread = threading.Thread(target=self.manual_check_updates)
        thread.daemon = True
        thread.start()
    
    def manual_check_updates(self):
        update_info = check_for_updates()
        if update_info:
            has_update, latest_version, release_url = update_info
            if has_update:
                GLib.idle_add(self.show_update_dialog, latest_version, release_url)
            else:
                GLib.idle_add(self.show_no_updates_message)
        else:
            GLib.idle_add(self.show_update_check_error)
    
    def show_no_updates_message(self):
        dialog = Adw.AlertDialog(
            heading="Estoy actualizado :)",
            body=f"Bien hecho, estoy actualizado a la última versión ({CURRENT_VERSION})."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)
        self.status_label.set_text("Empieza seleccionando un archivo que contenga una app")
        return False
    
    def show_update_check_error(self):
        dialog = Adw.AlertDialog(
            heading="He encontrado un error",
            body="Vaya, no he podido comprobar las actualizaciones. ¿Estás conectado a internet?"
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self)
        self.status_label.set_text("Empieza seleccionando un archivo que contenga una app")
        return False

    def on_install_clicked(self, widget):
        if not self.file_path:
            return
            
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(False)
        self.apps_button.set_sensitive(False)
        self.clean_button.set_sensitive(False)
        self.antivirus_button.set_sensitive(False)
        self.status_label.set_text("Instalando...")
        self.progress_bar.set_fraction(0.0)

        file_extension = os.path.splitext(self.file_path)[1].lower()

        if file_extension == '.deb':
            cmd = ['pkexec', 'dpkg', '-i', self.file_path]
        elif file_extension == '.rpm':
            cmd = ['pkexec', 'rpm', '-i', self.file_path]
        elif file_extension == '.appimage':
            # Obtener el nombre del archivo sin extensión
            app_name = os.path.basename(self.file_path).replace('.appimage', '')
            
            # Crear comandos para:
            # 1. Hacer ejecutable el AppImage
            # 2. Mover el AppImage a /usr/bin
            # 3. Crear el archivo .desktop
            cmd = [
                'pkexec', 'bash', '-c',
                f'chmod +x "{self.file_path}" && ' +
                f'cp "{self.file_path}" /usr/bin/{app_name} && ' +
                self.create_desktop_file(app_name)
            ]
        elif file_extension in ('.tar.xz', '.tar.gz', '.tgz'):
            extract_dir = os.path.expanduser('~/.local')
            cmd = ['tar', '-xvf', self.file_path, '-C', extract_dir]
        else:
            self.status_label.set_text("Formato de paquete no soportado por Swift Install")
            self.install_button.set_sensitive(True)
            self.fix_deps_button.set_sensitive(True)
            self.apps_button.set_sensitive(True)
            return

        thread = threading.Thread(target=self.run_installation, args=(cmd,))
        thread.daemon = True
        thread.start()

    def on_fix_deps_clicked(self, widget):
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(False)
        self.apps_button.set_sensitive(False)
        self.clean_button.set_sensitive(False)
        self.antivirus_button.set_sensitive(False)
        self.status_label.set_text("Corrigiendo errores")
        self.progress_bar.set_fraction(0.0)

        cmd = ['pkexec', 'apt-get', 'install', '-f', '-y']
        thread = threading.Thread(target=self.run_fix_deps, args=(cmd,))
        thread.daemon = True
        thread.start()

    def on_apps_clicked(self, widget):
        apps_window = InstalledAppsWindow(self)
        apps_window.present()

    def on_clean_clicked(self, widget):
        clean_window = SystemCleanupWindow(self)
        clean_window.present()

    def on_antivirus_clicked(self, widget):
        antivirus_window = AntivirusWindow(self)
        antivirus_window.present()

    def run_installation(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_progress)

            _, stderr = process.communicate()
            
            if process.returncode == 0:
                self.installed_package = self.file_path
                
                # Mensaje especial para AppImage
                if self.file_path.lower().endswith('.appimage'):
                    app_name = os.path.basename(self.file_path).replace('.appimage', '')
                    GLib.idle_add(self.installation_complete, f"AppImage instalado como {app_name}. Se ha creado un acceso directo.")
                else:
                    GLib.idle_add(self.installation_complete, "He instalado todo bien, ¡disfrútala!")
            else:
                GLib.idle_add(self.installation_complete, f"Vaya, he encontrado un error al instalar: {stderr}", True, stderr)
        except Exception as e:
            GLib.idle_add(self.installation_complete, f"Error en la instalación: {str(e)}", True, "")

    def run_fix_deps(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_progress)

            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.fix_deps_complete, "He arreglado las dependencias")
            else:
                GLib.idle_add(self.fix_deps_complete, f"Vaya, un error al corregir dependencias: {stderr}", True)
        except Exception as e:
            GLib.idle_add(self.fix_deps_complete, f"Error al corregir dependencias: {str(e)}", True)

    def update_progress(self):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.01)
        self.progress_bar.set_fraction(new_value)
        return False

    def installation_complete(self, message, is_error=False, stderr_output=""):
        self.progress_bar.set_fraction(1.0)
        self.status_label.set_text(message)
        
        if is_error:
            print(f"DEBUG: Error detectado. stderr_output: {stderr_output}")  # Debug temporal
            # Verificar si el error es de dependencias faltantes
            if self.should_auto_install_deps(stderr_output):
                print("DEBUG: Dependencias faltantes detectadas, iniciando instalación automática")  # Debug temporal
                self.handle_missing_dependencies(stderr_output)
                return
                
            dialog = Adw.AlertDialog(
                heading="¡Un error en la instalación!",
                body=message
            )
        else:
            dialog = Adw.AlertDialog(
                heading="He terminado la instalación",
                body=message
            )
        
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        
        dialog.present(self)
        
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)

    def fix_deps_complete(self, message, is_error=False):
        self.progress_bar.set_fraction(1.0)
        self.status_label.set_text(message)
        
        if is_error:
            dialog = Adw.AlertDialog(
                heading="¡Un error al corregir las dependencias!",
                body=message
            )
        else:
            dialog = Adw.AlertDialog(
                heading="He corregido las dependencias",
                body=message
            )
        
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        
        dialog.present(self)
        
        self.install_button.set_sensitive(True)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)
        self.clean_button.set_sensitive(True)
        self.antivirus_button.set_sensitive(True)

    def should_auto_install_deps(self, stderr_output):
        """Determina si el error se debe a dependencias faltantes."""
        if not stderr_output:
            print("DEBUG: No hay stderr_output")  # Debug temporal
            return False
            
        # Patrones comunes que indican dependencias faltantes (inglés y español)
        dependency_patterns = [
            # Patrones en inglés
            "depends on",
            "dependency is not satisfiable", 
            "unmet dependencies",
            "depends:",
            "pre-depends:",
            "Dependency is not satisfiable:",
            "broken dependencies",
            "conflicting packages",
            "package has unmet dependencies",
            "dependency problems",
            "trying to overwrite",
            "dpkg: dependency problems prevent",
            "configure: error",
            # Patrones en español
            "depende de",
            "problemas de dependencias",
            "dependencias - se deja sin configurar",
            "no está instalado",
            "sin embargo:",
            "dpkg: problemas de dependencias impiden",
            "error al procesar el paquete",
            "dependencias no satisfechas",
            "paquete no está instalado"
        ]
        
        stderr_lower = stderr_output.lower()
        found_pattern = None
        for pattern in dependency_patterns:
            if pattern.lower() in stderr_lower:
                found_pattern = pattern
                break
        
        print(f"DEBUG: Buscando patrones de dependencias. Encontrado: {found_pattern}")  # Debug temporal
        return found_pattern is not None

    def extract_missing_packages(self, stderr_output):
        """Extrae los nombres de paquetes faltantes del error."""
        import re
        
        missing_packages = set()
        
        # Patrones para extraer nombres de paquetes (inglés y español)
        patterns = [
            # Patrones en inglés
            r'(\w+(?:[-_]\w+)*)\s*\([^)]*\)\s*but',
            r'depends\s+on\s+(\w+(?:[-_]\w+)*)',
            r'(\w+(?:[-_]\w+)*)\s*:\s*Depends:',
            r'Depends:\s*(\w+(?:[-_]\w+)*)',
            r'package\s+(\w+(?:[-_]\w+)*)\s+is\s+not\s+installed',
            # Patrones en español
            r'depende\s+de\s+([a-zA-Z0-9][a-zA-Z0-9\-\.]*)',
            r'El\s+paquete\s+[`\'""]([a-zA-Z0-9][a-zA-Z0-9\-\.]*)[`\'""]\s+no\s+está\s+instalado',
            r'([a-zA-Z0-9][a-zA-Z0-9\-\.]*)\s+\([^)]*\);\s+sin\s+embargo:',
            r'([a-zA-Z0-9][a-zA-Z0-9\-\.]*)\s+depende\s+de'
        ]
        
        print(f"DEBUG: Extrayendo paquetes del error: {stderr_output[:200]}...")  # Debug temporal
        
        for pattern in patterns:
            matches = re.findall(pattern, stderr_output, re.IGNORECASE)
            print(f"DEBUG: Patrón '{pattern}' encontró: {matches}")  # Debug temporal
            missing_packages.update(matches)
        
        # Filtrar paquetes comunes que no necesitan instalación manual
        filter_out = {'but', 'is', 'not', 'installed', 'depends', 'on', 'package', 'de', 'el', 'paquete', 'sin', 'embargo'}
        missing_packages = {pkg for pkg in missing_packages if pkg.lower() not in filter_out and len(pkg) > 2}
        
        print(f"DEBUG: Paquetes finales extraídos: {list(missing_packages)}")  # Debug temporal
        return list(missing_packages)

    def handle_missing_dependencies(self, stderr_output):
        """Maneja la instalación automática de dependencias faltantes."""
        print(f"DEBUG: Manejando dependencias faltantes...")  # Debug temporal
        missing_packages = self.extract_missing_packages(stderr_output)
        print(f"DEBUG: Paquetes faltantes detectados: {missing_packages}")  # Debug temporal
        
        if not missing_packages:
            print("DEBUG: No se detectaron paquetes específicos, usando auto_fix_dependencies")  # Debug temporal
            # Si no podemos detectar paquetes específicos, intentar la corrección general
            self.auto_fix_dependencies()
            return
        
        # Mostrar diálogo de confirmación
        packages_text = ", ".join(missing_packages)
        print(f"DEBUG: Mostrando diálogo para instalar: {packages_text}")  # Debug temporal
        dialog = Adw.AlertDialog(
            heading="Dependencias faltantes detectadas",
            body=f"He detectado que faltan estas dependencias:\n{packages_text}\n\n¿Quieres que las instale automáticamente?"
        )
        dialog.add_response("no", "No")
        dialog.add_response("yes", "Sí, instalar")
        dialog.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("yes")
        dialog.set_close_response("no")
        
        dialog.choose(self, None, self._on_auto_install_response, missing_packages)

    def _on_auto_install_response(self, dialog, result, missing_packages):
        """Respuesta del diálogo de instalación automática."""
        try:
            response = dialog.choose_finish(result)
            if response == "yes":
                self.install_missing_packages(missing_packages)
        except Exception as e:
            print(f"Dialog error: {e}")

    def install_missing_packages(self, packages):
        """Instala los paquetes faltantes."""
        self.status_label.set_text("Instalando dependencias faltantes...")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_visible(True)
        
        # Construir comando para instalar paquetes
        cmd = ['pkexec', 'apt-get', 'install', '-y'] + packages
        
        thread = threading.Thread(target=self.run_auto_dependency_install, args=(cmd, packages))
        thread.daemon = True
        thread.start()

    def run_auto_dependency_install(self, cmd, packages):
        """Ejecuta la instalación de dependencias en un hilo separado."""
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_progress)
            
            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.auto_install_complete, packages, True)
            else:
                GLib.idle_add(self.auto_install_complete, packages, False, stderr)
        except Exception as e:
            GLib.idle_add(self.auto_install_complete, packages, False, str(e))

    def auto_install_complete(self, packages, success, error_msg=""):
        """Maneja el resultado de la instalación automática."""
        self.progress_bar.set_visible(False)
        self.progress_bar.set_fraction(0.0)
        
        if success:
            self.status_label.set_text("Dependencias instaladas. Reintentando instalación...")
            # Reintentar la instalación del paquete original
            self.retry_installation()
        else:
            self.status_label.set_text("Error al instalar dependencias")
            dialog = Adw.AlertDialog(
                heading="Error al instalar dependencias",
                body=f"No pude instalar las dependencias automáticamente.\nError: {error_msg}\n\nPuedes intentar corregir manualmente usando el botón 'Corregir errores'."
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            
            # Re-habilitar botones
            self.install_button.set_sensitive(True)
            self.fix_deps_button.set_sensitive(True)
            self.apps_button.set_sensitive(True)

    def auto_fix_dependencies(self):
        """Ejecuta apt-get install -f automáticamente."""
        print("DEBUG: Ejecutando auto_fix_dependencies")  # Debug temporal
        
        # Mostrar diálogo de confirmación para la corrección automática
        dialog = Adw.AlertDialog(
            heading="Error de dependencias detectado",
            body="He detectado un problema con las dependencias del paquete.\n\n¿Quieres que intente corregir las dependencias automáticamente?"
        )
        dialog.add_response("no", "No")
        dialog.add_response("yes", "Sí, corregir")
        dialog.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("yes")
        dialog.set_close_response("no")
        
        dialog.choose(self, None, self._on_auto_fix_response, None)

    def _on_auto_fix_response(self, dialog, result, data):
        """Respuesta del diálogo de corrección automática."""
        try:
            response = dialog.choose_finish(result)
            if response == "yes":
                print("DEBUG: Usuario confirmó corrección automática")  # Debug temporal
                self.status_label.set_text("Corrigiendo dependencias automáticamente...")
                self.progress_bar.set_fraction(0.0)
                self.progress_bar.set_visible(True)
                
                cmd = ['pkexec', 'apt-get', 'install', '-f', '-y']
                thread = threading.Thread(target=self.run_auto_fix, args=(cmd,))
                thread.daemon = True
                thread.start()
            else:
                print("DEBUG: Usuario canceló corrección automática")  # Debug temporal
                # Re-habilitar botones si el usuario cancela
                self.install_button.set_sensitive(True)
                self.fix_deps_button.set_sensitive(True)
                self.apps_button.set_sensitive(True)
        except Exception as e:
            print(f"Dialog error: {e}")

    def run_auto_fix(self, cmd):
        """Ejecuta la corrección automática de dependencias."""
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_progress)
            
            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.auto_fix_complete, True)
            else:
                GLib.idle_add(self.auto_fix_complete, False, stderr)
        except Exception as e:
            GLib.idle_add(self.auto_fix_complete, False, str(e))

    def auto_fix_complete(self, success, error_msg=""):
        """Maneja el resultado de la corrección automática."""
        self.progress_bar.set_visible(False)
        self.progress_bar.set_fraction(0.0)
        
        if success:
            self.status_label.set_text("Dependencias corregidas. Reintentando instalación...")
            # Reintentar la instalación del paquete original
            self.retry_installation()
        else:
            self.status_label.set_text("Error al corregir dependencias automáticamente")
            dialog = Adw.AlertDialog(
                heading="Error al corregir dependencias",
                body=f"No pude corregir las dependencias automáticamente.\nError: {error_msg}"
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            
            # Re-habilitar botones
            self.install_button.set_sensitive(True)
            self.fix_deps_button.set_sensitive(True)
            self.apps_button.set_sensitive(True)

    def retry_installation(self):
        """Reintenta la instalación del paquete original después de corregir dependencias."""
        if not self.file_path:
            return
            
        self.status_label.set_text("Reintentando instalación...")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_visible(True)
        
        # Reconstruir el comando de instalación
        file_extension = os.path.splitext(self.file_path)[1].lower()
        
        if file_extension == '.deb':
            cmd = ['pkexec', 'dpkg', '-i', self.file_path]
        elif file_extension == '.rpm':
            cmd = ['pkexec', 'rpm', '-i', self.file_path]
        elif file_extension == '.appimage':
            app_name = os.path.basename(self.file_path).replace('.appimage', '')
            cmd = [
                'pkexec', 'bash', '-c',
                f'chmod +x "{self.file_path}" && ' +
                f'cp "{self.file_path}" /usr/bin/{app_name} && ' +
                self.create_desktop_file(app_name)
            ]
        elif file_extension in ('.tar.xz', '.tar.gz', '.tgz'):
            extract_dir = os.path.expanduser('~/.local')
            cmd = ['tar', '-xvf', self.file_path, '-C', extract_dir]
        else:
            self.status_label.set_text("Formato de paquete no soportado")
            return
        
        thread = threading.Thread(target=self.run_installation, args=(cmd,))
        thread.daemon = True
        thread.start()

    def on_report_issue(self, widget):
        safe_open_url("https://github.com/Inled-Group/swiftinstall/issues")
    
    def open_inled_es(self, widget):
        safe_open_url("https://inled.es")
    
    def on_about_clicked(self, widget):
        about_dialog = Adw.AboutWindow(
            transient_for=self,
            modal=True,
            application_name="Swift Install",
            application_icon="package-x-generic-symbolic",
            version=CURRENT_VERSION,
            comments="Soy un instalador de paquetes gráfico para Linux. Espero que disfrutes usándome",
            license_type=Gtk.License.GPL_3_0,
            website="https://inled.es",
            developers=["Inled Group"]
        )
        about_dialog.present()
def check_dependencies():
    """Verifica que todas las dependencias necesarias estén instaladas."""
    missing_deps = []
    
    # Verificar Python
    try:
        import sys
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 6):
            missing_deps.append(f"Python 3.6+ (versión actual: {python_version.major}.{python_version.minor})")
    except:
        missing_deps.append("Python 3.6+")
    
    # Verificar dependencias de GTK
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except ImportError:
        missing_deps.append("PyGObject (python3-gi)")
    except ValueError:
        missing_deps.append("GTK 3.0 (libgtk-3-0)")
    
    # Verificar otras dependencias de Python
    dependencies = [
        ('requests', 'requests'),
        ('packaging', 'packaging'),
    ]
    
    for module_name, package_name in dependencies:
        try:
            __import__(module_name)
        except ImportError:
            missing_deps.append(f"{package_name}")
    
    return missing_deps

def show_dependencies_dialog(parent_window, missing_deps):
    """Muestra un diálogo con las dependencias faltantes."""
    if not missing_deps:
        return True
    
    from gi.repository import Gtk
    
    deps_text = "\n".join([f"• {dep}" for dep in missing_deps])
    install_cmd = "sudo apt install python3 python3-gi python3-requests python3-packaging libgtk-3-0"
    
    dialog = Gtk.MessageDialog(
        transient_for=parent_window,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text="Faltan dependencias requeridas"
    )
    
    if parent_window:
        dialog.present(parent_window)
    else:
        dialog.present(None)
    
    return False  # Indicar que faltan dependencias

class SwiftInstallApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.inled.swiftinstall")
        self.connect("activate", self.on_activate)
    
    def on_activate(self, app):
        missing_deps = check_dependencies()
        # Cargar el CSS para el estilo GNOME moderno
        load_css()
        
        win = PackageInstaller(app)
        win.present()

def Component():
    app = SwiftInstallApp()
    return app.run()

if __name__ == "__main__":
    Component() 