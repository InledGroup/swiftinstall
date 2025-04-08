import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio, Gdk
import subprocess
import os
import threading
import webbrowser
import requests
from packaging import version

# Versión actual de la aplicación
CURRENT_VERSION = "5.0"  # Cambia esto a la versión actual de tu aplicación
GITHUB_REPO = "Inled-Group/swiftinstall"

# Aplicar CSS para un estilo GNOME moderno
def load_css():
    css_provider = Gtk.CssProvider()
    
    # Cargar el CSS desde un archivo externo
    try:
        with open("styles.css", "rb") as css_file:
            css_provider.load_from_data(css_file.read())
        
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
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

class UpdateDialog(Gtk.Dialog):
    def __init__(self, parent, latest_version, release_url):
        Gtk.Dialog.__init__(
            self, title="Actualización disponible", transient_for=parent, flags=0
        )
        self.add_buttons(
            "Actualizar ahora", Gtk.ResponseType.YES,
            "Recordar más tarde", Gtk.ResponseType.NO,
        )
        
        self.set_default_size(400, 200)
        
        content_area = self.get_content_area()
        content_area.set_spacing(20)
        content_area.set_margin_top(24)
        content_area.set_margin_bottom(24)
        content_area.set_margin_start(24)
        content_area.set_margin_end(24)
        
        # Icono de actualización
        icon = Gtk.Image.new_from_icon_name("software-update-available", Gtk.IconSize.DIALOG)
        content_area.add(icon)
        
        # Título con formato
        title_label = Gtk.Label()
        title_label.set_markup("<span size='large' weight='bold'>Necesito actualizarme</span>")
        content_area.add(title_label)
        
        # Información de versiones
        version_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        version_box.set_margin_top(12)
        
        current_version_label = Gtk.Label()
        current_version_label.set_markup(f"Versión actual: <b>{CURRENT_VERSION}</b>")
        version_box.add(current_version_label)
        
        new_version_label = Gtk.Label()
        new_version_label.set_markup(f"Nueva versión: <b>{latest_version}</b>")
        version_box.add(new_version_label)
        
        content_area.add(version_box)
        
        self.release_url = release_url
        self.show_all()
        
        action_area = self.get_widget_for_response(Gtk.ResponseType.YES).get_parent()
        for button in action_area.get_children():
            text = button.get_label()
            if text == "Actualizar ahora":
                button.get_style_context().add_class("action-button")
            elif text == "Ignorar esta versión":
                button.get_style_context().add_class("secondary-button")

class InstalledAppsWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Aplicaciones instaladas")
        self.set_default_size(500, 400)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.get_style_context().add_class("main-window")

        # Header bar al estilo GNOME
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.set_title("Aplicaciones instaladas")
        header_bar.get_style_context().add_class("header-bar")
        self.set_titlebar(header_bar)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        self.add(main_box)

        # Barra de búsqueda con icono
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU)
        search_box.pack_start(search_icon, False, False, 8)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar aplicaciones...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.get_style_context().add_class("search-entry")
        search_box.pack_start(self.search_entry, True, True, 0)
        
        main_box.pack_start(search_box, False, False, 0)

        # Tarjeta para la lista de aplicaciones
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.get_style_context().add_class("card")
        main_box.pack_start(card, True, True, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(300)
        card.pack_start(scrolled_window, True, True, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_filter_func(self.filter_func)
        scrolled_window.add(self.listbox)
        
        # Barra de progreso
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        progress_box.set_margin_top(16)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.get_style_context().add_class("progress-bar")
        progress_box.pack_start(self.progress_bar, False, False, 0)
        
        main_box.pack_start(progress_box, False, False, 0)
        self.progress_bar.hide()

        # Mensaje de estado
        self.status_label = Gtk.Label(label="")
        self.status_label.get_style_context().add_class("status-label")
        main_box.pack_start(self.status_label, False, False, 0)
        
        # Cargar aplicaciones
        self.load_installed_apps()
    
    def load_installed_apps(self):
        # Limpiar la lista actual
        for child in self.listbox.get_children():
            self.listbox.remove(child)
            
        # Mostrar un spinner mientras se cargan las aplicaciones
        spinner = Gtk.Spinner()
        spinner.start()
        spinner_row = Gtk.ListBoxRow()
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        spinner_box.set_margin_top(12)
        spinner_box.set_margin_bottom(12)
        spinner_box.pack_start(spinner, True, True, 0)
        spinner_row.add(spinner_box)
        self.listbox.add(spinner_row)
        self.listbox.show_all()
        
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
                for child in self.listbox.get_children():
                    if isinstance(child.get_child(), Gtk.Box) and \
                       isinstance(child.get_child().get_children()[0], Gtk.Spinner):
                        self.listbox.remove(child)
                        break
                
                # Añadir paquetes en lotes
                batch_size = 50
                for i in range(0, len(packages), batch_size):
                    batch = packages[i:i+batch_size]
                    for package_name in batch:
                        self.add_app_to_list(package_name, False)
                    
                    # Permitir que la UI se actualice entre lotes
                    while Gtk.events_pending():
                        Gtk.main_iteration()
                
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
        row.get_style_context().add_class("list-row")
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        row.add(hbox)
        
        # Icono para el tipo de aplicación
        icon_name = "package-x-generic" if not is_appimage else "application-x-executable"
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        hbox.pack_start(icon, False, False, 0)
        
        # Nombre a mostrar
        display_name = package_name
        
        # Contenedor vertical para nombre y tipo
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        label = Gtk.Label(label=display_name, xalign=0)
        label.get_style_context().add_class("title-label")
        vbox.pack_start(label, False, False, 0)
        
        # Etiqueta para el tipo
        type_label = Gtk.Label(label="AppImage" if is_appimage else "Paquete instalado", xalign=0)
        type_label.get_style_context().add_class("subtitle-label")
        vbox.pack_start(type_label, False, False, 0)
        
        hbox.pack_start(vbox, True, True, 0)
        
        # Botón de desinstalar con icono
        button = Gtk.Button()
        button.set_tooltip_text("Desinstalar")
        button.get_style_context().add_class("destructive-button")
        
        button_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        button.add(button_icon)
        
        button.connect("clicked", self.on_uninstall_clicked, package_name, is_appimage)
        hbox.pack_start(button, False, False, 0)
        
        self.listbox.add(row)
        row.show_all()
    
    def show_no_apps_message(self):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        
        icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, True, 8)
        
        label = Gtk.Label(label="No he encontrado aplicaciones instaladas en tu sistema")
        label.get_style_context().add_class("title-label")
        box.pack_start(label, False, True, 8)
        
        row.add(box)
        self.listbox.add(row)
        row.show_all()
        return False
    
    def show_error_message(self):
        # Eliminar el spinner si existe
        for child in self.listbox.get_children():
            if isinstance(child.get_child(), Gtk.Box) and \
               isinstance(child.get_child().get_children()[0], Gtk.Spinner):
                self.listbox.remove(child)
                break
        
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        
        icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic", Gtk.IconSize.DIALOG)
        box.pack_start(icon, False, True, 8)
        
        label = Gtk.Label(label="No he podido encontrar aplicaciones instaladas en tu sistema")
        label.get_style_context().add_class("title-label")
        box.pack_start(label, False, True, 8)
        
        row.add(box)
        self.listbox.add(row)
        row.show_all()
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
            for child in box.get_children():
                if isinstance(child, Gtk.Box) and child.get_orientation() == Gtk.Orientation.VERTICAL:
                    for label in child.get_children():
                        if isinstance(label, Gtk.Label) and hasattr(label, 'get_text'):
                            if text in label.get_text().lower():
                                return True
        return False
    
    def on_uninstall_clicked(self, button, package_name, is_appimage=False):
        if is_appimage:
            message = f"¿Deseas desinstalar {package_name}?"
        else:
            message = f"¿Deseas desinstalar {package_name}?"
            
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message
        )
        
        # Estilizar el diálogo
        dialog.set_default_size(350, 150)
        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_top(20)
        content_area.set_margin_bottom(20)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        
        # Estilizar los botones - CORREGIDO: no usar get_action_area()
        action_area = dialog.get_widget_for_response(Gtk.ResponseType.YES).get_parent()
        for button in action_area.get_children():
            text = button.get_label()
            if text == "Sí":
                button.get_style_context().add_class("destructive-button")
            elif text == "No":
                button.get_style_context().add_class("secondary-button")
        
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.uninstall_package(package_name, is_appimage)
    
    def uninstall_package(self, package_name, is_appimage=False):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.show()
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
    
    def update_uninstall_progress(self):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.05)
        self.progress_bar.set_fraction(new_value)
        return False

    def uninstall_complete(self, package_name, success, is_appimage=False, error_message=None):
        self.progress_bar.hide()
        self.progress_bar.set_fraction(0.0)
        
        if success:
            if is_appimage:
                message = f"{package_name} ha sido desinstalado correctamente. Recuerda borrar los archivos que haya creado la aplicación."
            else:
                message = f"{package_name} ha sido desinstalado correctamente."
                
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
            self.status_label.set_text("Desinstalación completada")
        else:
            if is_appimage:
                message = f"Error al desinstalar Swiftinstall Enhance AppImage - {package_name}."
            else:
                message = f"Error al desinstalar {package_name}."
                
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=message,
                secondary_text=error_message
            )
            self.status_label.set_text("Uy... ha habido un error cuando estaba desinstalándote la app")
        
        # Estilizar el diálogo
        dialog.set_default_size(350, 150)
        content_area = dialog.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_top(20)
        content_area.set_margin_bottom(20)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        
        dialog.run()
        dialog.destroy()
        self.load_installed_apps()  # Refrescar la lista


class PackageInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Swift Install")
        self.set_default_size(600, 500)
        self.get_style_context().add_class("main-window")
        
        # Header bar al estilo GNOME
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.set_title("Swift Install")
        header_bar.set_subtitle(f"Versión {CURRENT_VERSION}")
        header_bar.get_style_context().add_class("header-bar")
        
        # Botón de menú en la header bar
        menu_button = Gtk.MenuButton()
        menu_button.set_tooltip_text("Menú")
        icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        menu_button.add(icon)
        
        # Crear el menú
        popover = Gtk.Popover()
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        popover_box.set_margin_top(10)
        popover_box.set_margin_bottom(10)
        popover_box.set_margin_start(10)
        popover_box.set_margin_end(10)
        
        # Elementos del menú
        about_button = Gtk.ModelButton(label="Acerca de Swift Install")
        about_button.connect("clicked", self.on_about_clicked)
        popover_box.add(about_button)
        
        report_button = Gtk.ModelButton(label="Reportar un error")
        report_button.connect("clicked", self.on_report_issue)
        popover_box.add(report_button)
        
        update_button = Gtk.ModelButton(label="Buscar actualizaciones")
        update_button.connect("clicked", self.on_check_updates_clicked)
        popover_box.add(update_button)
        
        popover_box.show_all()
        popover.add(popover_box)
        menu_button.set_popover(popover)
        
        header_bar.pack_end(menu_button)
        
        self.set_titlebar(header_bar)

        # Contenido principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.add(main_box)

        # Sección de selección de archivo
        file_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        file_section.get_style_context().add_class("card")
        
        # Título de la sección
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name("package-x-generic-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        title_box.pack_start(icon, False, False, 0)
        
        title_label = Gtk.Label(label="¿Qué debo instalar?")
        title_label.get_style_context().add_class("title-label")
        title_box.pack_start(title_label, False, False, 0)
        
        file_section.pack_start(title_box, False, False, 0)
        
        # Selector de archivo con estilo
        file_chooser_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        file_chooser_box.get_style_context().add_class("file-chooser-button")
        
        file_icon = Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.DIALOG)
        file_chooser_box.pack_start(file_icon, True, True, 8)
        
        file_label = Gtk.Label(label="Selecciona el archivo que debo instalar")
        file_label.get_style_context().add_class("subtitle-label")
        file_chooser_box.pack_start(file_label, False, False, 8)
        
        file_chooser_button = Gtk.Button()
        file_chooser_button.add(file_chooser_box)
        file_chooser_button.connect("clicked", self.on_file_chooser_clicked)
        
        file_section.pack_start(file_chooser_button, True, True, 0)
        
        # Etiqueta para mostrar el archivo seleccionado
        self.selected_file_label = Gtk.Label(label="Aún no has seleccionado ningún archivo")
        self.selected_file_label.get_style_context().add_class("subtitle-label")
        file_section.pack_start(self.selected_file_label, False, False, 0)
        
        main_box.pack_start(file_section, False, False, 0)
        
        # Sección de acciones
        actions_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        actions_section.get_style_context().add_class("card")
        
        # Título de la sección
        actions_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_icon = Gtk.Image.new_from_icon_name("preferences-other-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        actions_title_box.pack_start(actions_icon, False, False, 0)
        
        actions_title_label = Gtk.Label(label="Acciones")
        actions_title_label.get_style_context().add_class("title-label")
        actions_title_box.pack_start(actions_title_label, False, False, 0)
        
        actions_section.pack_start(actions_title_box, False, False, 0)
        
        # Botones de acción
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons_box.set_homogeneous(True)
        
        # Botón de instalar - CORREGIDO: sin label en el constructor
        self.install_button = Gtk.Button()
        self.install_button.get_style_context().add_class("action-button")
        install_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        install_icon = Gtk.Image.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        install_box.pack_start(install_icon, False, False, 0)
        install_label = Gtk.Label(label="Instalar")
        install_box.pack_start(install_label, False, False, 0)
        self.install_button.add(install_box)
        self.install_button.connect("clicked", self.on_install_clicked)
        self.install_button.set_sensitive(False)
        buttons_box.pack_start(self.install_button, True, True, 0)
        
        # Botón de corregir errores - CORREGIDO: sin label en el constructor
        self.fix_deps_button = Gtk.Button()
        self.fix_deps_button.get_style_context().add_class("secondary-button")
        fix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fix_icon = Gtk.Image.new_from_icon_name("applications-utilities-symbolic", Gtk.IconSize.BUTTON)
        fix_box.pack_start(fix_icon, False, False, 0)
        fix_label = Gtk.Label(label="Corregir errores")
        fix_box.pack_start(fix_label, False, False, 0)
        self.fix_deps_button.add(fix_box)
        self.fix_deps_button.connect("clicked", self.on_fix_deps_clicked)
        buttons_box.pack_start(self.fix_deps_button, True, True, 0)
        
        # Botón de eliminar aplicaciones - CORREGIDO: sin label en el constructor
        self.apps_button = Gtk.Button()
        self.apps_button.get_style_context().add_class("secondary-button")
        apps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apps_icon = Gtk.Image.new_from_icon_name("user-trash-symbolic", Gtk.IconSize.BUTTON)
        apps_box.pack_start(apps_icon, False, False, 0)
        apps_label = Gtk.Label(label="Eliminar apps")
        apps_box.pack_start(apps_label, False, False, 0)
        self.apps_button.add(apps_box)
        self.apps_button.connect("clicked", self.on_apps_clicked)
        buttons_box.pack_start(self.apps_button, True, True, 0)
        
        actions_section.pack_start(buttons_box, True, True, 0)
        main_box.pack_start(actions_section, False, False, 0)
        
        # Sección de progreso
        progress_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        progress_section.get_style_context().add_class("card")
        
        # Título de la sección
        progress_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        progress_icon = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        progress_title_box.pack_start(progress_icon, False, False, 0)
        
        progress_title_label = Gtk.Label(label="Progreso")
        progress_title_label.get_style_context().add_class("title-label")
        progress_title_box.pack_start(progress_title_label, False, False, 0)
        
        progress_section.pack_start(progress_title_box, False, False, 0)
        
        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.get_style_context().add_class("progress-bar")
        progress_section.pack_start(self.progress_bar, False, False, 0)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Empieza seleccionando un archivo que contenga una app")
        self.status_label.get_style_context().add_class("status-label")
        progress_section.pack_start(self.status_label, False, False, 0)
        
        main_box.pack_start(progress_section, False, False, 0)

        self.installed_package = None
        self.file_path = None
        
        # Comprobar actualizaciones al iniciar la aplicación
        GLib.timeout_add(500, self.check_updates_on_startup)
    
    def on_file_chooser_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar paquete",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.OK
        )
        
        # Filtros para tipos de archivo
        filter_deb = Gtk.FileFilter()
        filter_deb.set_name("Paquetes Debian (.deb)")
        filter_deb.add_pattern("*.deb")
        dialog.add_filter(filter_deb)
        
        filter_rpm = Gtk.FileFilter()
        filter_rpm.set_name("Paquetes RPM (.rpm)")
        filter_rpm.add_pattern("*.rpm")
        dialog.add_filter(filter_rpm)
        
        filter_appimage = Gtk.FileFilter()
        filter_appimage.set_name("AppImage (.AppImage)")
        filter_appimage.add_pattern("*.AppImage")
        dialog.add_filter(filter_appimage)
        
        filter_tar = Gtk.FileFilter()
        filter_tar.set_name("Archivos comprimidos (.tar.gz, .tar.xz)")
        filter_tar.add_pattern("*.tar.gz")
        filter_tar.add_pattern("*.tar.xz")
        filter_tar.add_pattern("*.tgz")
        dialog.add_filter(filter_tar)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("Todos los archivos")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.file_path = dialog.get_filename()
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
        response = dialog.run()
        
        if response == Gtk.ResponseType.YES:
            # Usar el método seguro en lugar de webbrowser.open directamente
            safe_open_url(release_url)
        elif response == Gtk.ResponseType.CANCEL:
            # El usuario eligió ignorar esta versión - se podría guardar esta preferencia
            pass
        # Para la respuesta NO, simplemente cerrar el diálogo y recordar más tarde
        
        dialog.destroy()
        return False
    
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
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Estoy actualizado :)",
            secondary_text=f"Bien hecho, estoy actualizado a la última versión ({CURRENT_VERSION})."
        )
        dialog.run()
        dialog.destroy()
        self.status_label.set_text("Empieza seleccionando un archivo que contenga una app")
        return False
    
    def show_update_check_error(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="He encontrado un error",
            secondary_text="Vaya, no he podido comprobar las actualizaciones. ¿Estás conectado a internet?"
        )
        dialog.run()
        dialog.destroy()
        self.status_label.set_text("Empieza seleccionando un archivo que contenga una app")
        return False

    def on_install_clicked(self, widget):
        if not self.file_path:
            return
            
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(False)
        self.apps_button.set_sensitive(False)
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
        self.status_label.set_text("Corrigiendo errores")
        self.progress_bar.set_fraction(0.0)

        cmd = ['pkexec', 'apt-get', 'install', '-f', '-y']
        thread = threading.Thread(target=self.run_fix_deps, args=(cmd,))
        thread.daemon = True
        thread.start()

    def on_apps_clicked(self, widget):
        apps_window = InstalledAppsWindow(self)
        apps_window.show_all()

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
                GLib.idle_add(self.installation_complete, f"Vaya, he encontrado un error al instalar: {stderr}", True)
        except Exception as e:
            GLib.idle_add(self.installation_complete, f"Error en la instalación: {str(e)}", True)

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

    def installation_complete(self, message, is_error=False):
        self.progress_bar.set_fraction(1.0)
        self.status_label.set_text(message)
        
        if is_error:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="¡Un error en la instalación!",
                secondary_text=message
            )
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="He terminado la instalación",
                secondary_text=message
            )
        
        dialog.run()
        dialog.destroy()
        
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)

    def fix_deps_complete(self, message, is_error=False):
        self.progress_bar.set_fraction(1.0)
        self.status_label.set_text(message)
        
        if is_error:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="¡Un error al corregir las dependencias!",
                secondary_text=message
            )
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="He corregido las dependencias",
                secondary_text=message
            )
        
        dialog.run()
        dialog.destroy()
        
        self.install_button.set_sensitive(True)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)

    def on_report_issue(self, widget):
        safe_open_url("https://github.com/Inled-Group/swiftinstall/issues")
    
    def open_inled_es(self, widget):
        safe_open_url("https://inled.es")
    
    def on_about_clicked(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)
        
        about_dialog.set_program_name("Swift Install")
        about_dialog.set_version(CURRENT_VERSION)
        about_dialog.set_comments("Soy un instalador de paquetes gráfico para Linux. Espero que disfrutes usándome")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        about_dialog.set_website("https://inled.es")
        about_dialog.set_website_label("inled.es")
        about_dialog.set_authors(["Inled Group"])
        about_dialog.set_logo_icon_name("package-x-generic-symbolic")
        
        about_dialog.run()
        about_dialog.destroy()

def Component():
    # Cargar el CSS para el estilo GNOME moderno
    load_css()
    
    win = PackageInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

Component() 
