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

def check_for_updates():
    """
    Comprueba si hay actualizaciones comparando la versión actual con la última versión en GitHub.
    Devuelve una tupla (hay_actualizacion, ultima_version, url_release) o None si falla
    """
    try:
        response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=5)
        if response.status_code == 200:
            release_data = response.json()
            latest_version = release_data['tag_name'].lstrip('v')
            release_url = release_data['html_url']
            
            # Comparar versiones
            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                return (True, latest_version, release_url)
            return (False, latest_version, release_url)
    except Exception as e:
        print(f"Error al comprobar actualizaciones: {str(e)}")
    return None

class UpdateDialog(Gtk.Dialog):
    def __init__(self, parent, latest_version, release_url):
        Gtk.Dialog.__init__(
            self, title="Actualización disponible", transient_for=parent, flags=0
        )
        self.add_buttons(
            "Actualizar ahora", Gtk.ResponseType.YES,
            "Recordar más tarde", Gtk.ResponseType.NO,
            "Ignorar esta versión", Gtk.ResponseType.CANCEL
        )
        
        self.set_default_size(400, 180)
        
        content_area = self.get_content_area()
        content_area.set_spacing(12)
        content_area.set_margin_top(24)
        content_area.set_margin_bottom(24)
        content_area.set_margin_start(24)
        content_area.set_margin_end(24)
        
        # Título con estilo Gnome
        title_label = Gtk.Label()
        title_label.set_markup("<span font_weight='bold' font_size='large'>Actualización disponible</span>")
        title_label.set_halign(Gtk.Align.START)
        content_area.add(title_label)
        
        # Separador sutil
        separator = Gtk.Separator()
        separator.set_margin_top(12)
        separator.set_margin_bottom(12)
        content_area.add(separator)
        
        # Contenido
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_start(6)
        
        version_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        current_label = Gtk.Label(label="Versión actual:")
        current_label.set_halign(Gtk.Align.START)
        current_version_label = Gtk.Label(label=CURRENT_VERSION)
        current_version_label.set_halign(Gtk.Align.START)
        version_box.pack_start(current_label, False, False, 0)
        version_box.pack_start(current_version_label, False, False, 0)
        
        new_version_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        new_label = Gtk.Label(label="Nueva versión:")
        new_label.set_halign(Gtk.Align.START)
        new_version_label = Gtk.Label(label=latest_version)
        new_version_label.set_halign(Gtk.Align.START)
        new_version_box.pack_start(new_label, False, False, 0)
        new_version_box.pack_start(new_version_label, False, False, 0)
        
        info_box.add(version_box)
        info_box.add(new_version_box)
        
        question_label = Gtk.Label(label="¿Desea actualizar ahora?")
        question_label.set_margin_top(12)
        question_label.set_halign(Gtk.Align.START)
        
        content_area.add(info_box)
        content_area.add(question_label)
        
        self.release_url = release_url
        self.show_all()

class InstalledAppsWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Eliminar aplicaciones")
        self.set_default_size(500, 400)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        # Estilo Gnome: Usar HeaderBar en lugar de título normal
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title("Eliminar aplicaciones")
        headerbar.set_subtitle("Elimina las aplicaciones instaladas en tu sistema")
        self.set_titlebar(headerbar)
        
        # Botón de actualizar en la HeaderBar
        refresh_button = Gtk.Button()
        refresh_icon = Gio.ThemedIcon(name="view-refresh-symbolic")
        refresh_image = Gtk.Image.new_from_gicon(refresh_icon, Gtk.IconSize.BUTTON)
        refresh_button.add(refresh_image)
        refresh_button.set_tooltip_text("Actualizar lista")
        refresh_button.connect("clicked", self.on_refresh_clicked)
        headerbar.pack_end(refresh_button)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(18)
        main_box.set_margin_bottom(18)
        main_box.set_margin_start(18)
        main_box.set_margin_end(18)
        self.add(main_box)

        # Búsqueda con estilo Gnome
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar aplicaciones...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(search_icon, False, False, 0)
        search_box.pack_start(self.search_entry, True, True, 0)
        main_box.pack_start(search_box, False, False, 0)

        # Separador sutil
        separator = Gtk.Separator()
        separator.set_margin_top(6)
        separator.set_margin_bottom(6)
        main_box.pack_start(separator, False, False, 0)

        # Lista de aplicaciones con estilo Gnome
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_filter_func(self.filter_func)
        
        scrolled_window.add(self.listbox)

        self.overlay = Gtk.Overlay()
        self.overlay.add(scrolled_window)
        main_box.pack_start(self.overlay, True, True, 0)

        # Barra de progreso con estilo Gnome
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_top(12)
        main_box.pack_start(self.progress_bar, False, False, 0)
        self.progress_bar.hide()

        self.load_installed_apps()
    
    def on_refresh_clicked(self, button):
        # Limpiar la lista actual
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        # Recargar las aplicaciones
        self.load_installed_apps()
    
    def load_installed_apps(self):
        def add_app(package_name, is_appimage=False):
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_start(6)
            hbox.set_margin_end(6)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)
            row.add(hbox)
            
            # Icono para el tipo de aplicación
            icon_name = "package-x-generic-symbolic" if not is_appimage else "application-x-executable-symbolic"
            app_icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            hbox.pack_start(app_icon, False, False, 0)
            
            # Añadir un prefijo para AppImages para distinguirlos
            display_name = package_name
            if is_appimage:
                display_name = f"{package_name}"
                
            # Contenedor vertical para nombre y etiqueta
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            
            label = Gtk.Label(label=display_name, xalign=0)
            label.set_halign(Gtk.Align.START)
            vbox.pack_start(label, False, False, 0)
            
            # Etiqueta para el tipo
            type_label = Gtk.Label(xalign=0)
            type_label.set_markup(f"<span size='small' foreground='#888888'>{('AppImage' if is_appimage else 'Paquete')}</span>")
            vbox.pack_start(type_label, False, False, 0)
            
            hbox.pack_start(vbox, True, True, 0)
            
            # Botón de desinstalar con estilo Gnome
            button = Gtk.Button()
            button.set_tooltip_text("Desinstalar")
            trash_icon = Gio.ThemedIcon(name="user-trash-symbolic")
            trash_image = Gtk.Image.new_from_gicon(trash_icon, Gtk.IconSize.BUTTON)
            button.add(trash_image)
            button.get_style_context().add_class("destructive-action")
            button.connect("clicked", self.on_uninstall_clicked, package_name, is_appimage)
            hbox.pack_end(button, False, False, 0)
            
            self.listbox.add(row)
            row.show_all()
            return False

        def load_apps():
            try:
                # Cargar paquetes instalados
                output = subprocess.check_output(['dpkg', '--get-selections']).decode('utf-8')
                for line in output.split('\n'):
                    if line.strip():
                        package_name = line.split()[0]
                        GLib.idle_add(add_app, package_name, False)
                
                # Cargar AppImages instalados (archivos .desktop)
                desktop_dir = "/usr/share/applications"
                if os.path.exists(desktop_dir):
                    for filename in os.listdir(desktop_dir):
                        if filename.endswith(".desktop"):
                            # Verificar si es un AppImage creado por SwiftInstall
                            desktop_path = os.path.join(desktop_dir, filename)
                            try:
                                with open(desktop_path, 'r') as f:
                                    content = f.read()
                                    # Verificar si el archivo .desktop apunta a un AppImage en /usr/bin
                                    if "/usr/bin/" in content and "appimage.png" in content:
                                        app_name = filename.replace(".desktop", "")
                                        GLib.idle_add(add_app, app_name, True)
                            except:
                                pass
            except subprocess.CalledProcessError:
                # Mensaje de error con estilo Gnome
                info_bar = Gtk.InfoBar()
                info_bar.set_message_type(Gtk.MessageType.ERROR)
                
                content = info_bar.get_content_area()
                label = Gtk.Label(label="No se pudieron obtener las aplicaciones instaladas")
                content.add(label)
                
                self.listbox.add(info_bar)
                info_bar.show_all()
            
            return False

        GLib.idle_add(load_apps)
    
    def on_search_changed(self, entry):
        self.listbox.invalidate_filter()
    
    def filter_func(self, row):
        text = self.search_entry.get_text().lower()
        if not text:
            return True
        
        # Obtener el label del nombre de la aplicación (primer hijo del vbox)
        hbox = row.get_child()
        if not hbox or not isinstance(hbox, Gtk.Box):
            return False
            
        for child in hbox.get_children():
            if isinstance(child, Gtk.Box) and child.get_orientation() == Gtk.Orientation.VERTICAL:
                vbox = child
                if vbox.get_children():
                    label = vbox.get_children()[0]
                    if isinstance(label, Gtk.Label):
                        return text in label.get_text().lower()
        
        return False
    
    def on_uninstall_clicked(self, button, package_name, is_appimage=False):
        # Diálogo de confirmación con estilo Gnome
        if is_appimage:
            message = f"¿Deseas desinstalar el AppImage {package_name}?"
        else:
            message = f"¿Deseas desinstalar {package_name}?"
            
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=message
        )
        
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        delete_button = dialog.add_button("Desinstalar", Gtk.ResponseType.YES)
        delete_button.get_style_context().add_class("destructive-action")
        
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.uninstall_package(package_name, is_appimage)
    
    def uninstall_package(self, package_name, is_appimage=False):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.show()
        
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
        
        # Diálogo de resultado con estilo Gnome
        if success:
            if is_appimage:
                message = f"{package_name} ha sido desinstalado correctamente."
            else:
                message = f"{package_name} ha sido desinstalado correctamente."
                
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
        else:
            if is_appimage:
                message = f"Error al desinstalar {package_name}."
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
        dialog.run()
        dialog.destroy()
        self.load_installed_apps()  # Refrescar la lista


class PackageInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Swift Install")
        self.set_default_size(600, 400)
        
        # Estilo Gnome: Usar HeaderBar en lugar de menú tradicional
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title("Swift Install")
        headerbar.set_subtitle(f"Versión {CURRENT_VERSION}")
        self.set_titlebar(headerbar)
        
        # Botón de aplicaciones instaladas en la HeaderBar
        apps_button = Gtk.Button()
        apps_icon = Gio.ThemedIcon(name="user-trash-symbolic")
        apps_image = Gtk.Image.new_from_gicon(apps_icon, Gtk.IconSize.BUTTON)
        apps_button.add(apps_image)
        apps_button.set_tooltip_text("Desinstalar aplicaciones")
        apps_button.connect("clicked", self.on_apps_clicked)
        headerbar.pack_start(apps_button)
        
        # Botones de menú directamente en la HeaderBar en lugar de un menú desplegable
        about_button = Gtk.Button()
        about_icon = Gio.ThemedIcon(name="help-about-symbolic")
        about_image = Gtk.Image.new_from_gicon(about_icon, Gtk.IconSize.BUTTON)
        about_button.add(about_image)
        about_button.set_tooltip_text("Acerca de Inled Group")
        about_button.connect("clicked", self.open_inled_es)
        headerbar.pack_end(about_button)
        
        report_button = Gtk.Button()
        report_icon = Gio.ThemedIcon(name="dialog-warning-symbolic")
        report_image = Gtk.Image.new_from_gicon(report_icon, Gtk.IconSize.BUTTON)
        report_button.add(report_image)
        report_button.set_tooltip_text("Reportar un error")
        report_button.connect("clicked", self.on_report_issue)
        headerbar.pack_end(report_button)
        
        update_button = Gtk.Button()
        update_icon = Gio.ThemedIcon(name="software-update-available-symbolic")
        update_image = Gtk.Image.new_from_gicon(update_icon, Gtk.IconSize.BUTTON)
        update_button.add(update_image)
        update_button.set_tooltip_text("Buscar actualizaciones")
        update_button.connect("clicked", self.on_check_updates_clicked)
        headerbar.pack_end(update_button)
        
        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        self.add(main_box)
        
        # Sección de selección de archivo
        file_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        file_header = Gtk.Label()
        file_header.set_markup("<span font_weight='bold' font_size='large'>Instalar aplicaciones</span>")
        file_header.set_halign(Gtk.Align.START)
        
        file_description = Gtk.Label(label="Seleccione un archivo .deb, .rpm o .appimage para instalar")
        file_description.set_halign(Gtk.Align.START)
        file_description.get_style_context().add_class("dim-label")
        
        file_section.add(file_header)
        file_section.add(file_description)
        
        # Selector de archivo con estilo Gnome
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.file_chooser = Gtk.FileChooserButton(title="Explorar archivos")
        self.file_chooser.connect("file-set", self.on_file_selected)
        
        self.install_button = Gtk.Button(label="Instalar")
        self.install_button.get_style_context().add_class("suggested-action")
        self.install_button.connect("clicked", self.on_install_clicked)
        self.install_button.set_sensitive(False)
        
        file_box.pack_start(self.file_chooser, True, True, 0)
        file_box.pack_start(self.install_button, False, False, 0)
        
        file_section.add(file_box)
        main_box.pack_start(file_section, False, False, 0)
        
        # Separador
        separator = Gtk.Separator()
        main_box.pack_start(separator, False, False, 0)
        
        # Sección de herramientas
        tools_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        tools_header = Gtk.Label()
        tools_header.set_markup("<span font_weight='bold' font_size='large'>Herramientas</span>")
        tools_header.set_halign(Gtk.Align.START)
        
        tools_section.add(tools_header)
        
        # Botones de herramientas con iconos
        tools_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.fix_deps_button = Gtk.Button(label="Corregir errores de instalación")
        fix_icon = Gio.ThemedIcon(name="folder-download-symbolic")
        fix_image = Gtk.Image.new_from_gicon(fix_icon, Gtk.IconSize.BUTTON)
        self.fix_deps_button.set_image(fix_image)
        self.fix_deps_button.set_always_show_image(True)
        self.fix_deps_button.connect("clicked", self.on_fix_deps_clicked)
        
        tools_box.pack_start(self.fix_deps_button, True, True, 0)
        tools_section.add(tools_box)
        
        main_box.pack_start(tools_section, False, False, 0)
        
        # Sección de progreso
        progress_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Barra de progreso con estilo Gnome
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress_section.add(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = Gtk.Label(label="Seleccione un paquete a instalar")
        self.status_label.set_halign(Gtk.Align.START)
        progress_section.add(self.status_label)
        
        main_box.pack_start(progress_section, False, False, 0)
        
        self.installed_package = None
        
        # Comprobar actualizaciones al iniciar la aplicación
        GLib.timeout_add(500, self.check_updates_on_startup)

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
            # Abrir la página de la versión en el navegador
            webbrowser.open(release_url)
        elif response == Gtk.ResponseType.CANCEL:
            # El usuario eligió ignorar esta versión - se podría guardar esta preferencia
            pass
        # Para la respuesta NO, simplemente cerrar el diálogo y recordar más tarde
        
        dialog.destroy()
        return False
    
    def on_check_updates_clicked(self, widget):
        self.status_label.set_text("Comprobando actualizaciones...")
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
        # Diálogo de información con estilo Gnome
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="No hay actualizaciones disponibles",
            secondary_text=f"Estás utilizando la versión más reciente ({CURRENT_VERSION})."
        )
        dialog.run()
        dialog.destroy()
        self.status_label.set_text("Seleccione un paquete a instalar")
        return False
    
    def show_update_check_error(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error al comprobar actualizaciones",
            secondary_text="No se pudo conectar con el servidor de GitHub. Compruebe su conexión a Internet."
        )
        dialog.run()
        dialog.destroy()
        self.status_label.set_text("Seleccione un paquete a instalar")
        return False

    def on_file_selected(self, widget):
        self.file_path = widget.get_filename()
        self.install_button.set_sensitive(True)
        self.status_label.set_text(f"Seleccionó: {os.path.basename(self.file_path)}")

    def on_install_clicked(self, widget):
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(False)
        self.file_chooser.set_sensitive(False)
        self.status_label.set_text("Instalando...")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Preparando instalación...")

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
            # Mostrar error con estilo Gnome
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Formato no soportado",
                secondary_text="Este formato de paquete no está soportado por Swift Install."
            )
            dialog.run()
            dialog.destroy()
            
            self.status_label.set_text("Formato de paquete no soportado")
            self.install_button.set_sensitive(True)
            self.file_chooser.set_sensitive(True)
            self.fix_deps_button.set_sensitive(True)
            return

        thread = threading.Thread(target=self.run_installation, args=(cmd,))
        thread.daemon = True
        thread.start()

    def on_fix_deps_clicked(self, widget):
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(False)
        self.file_chooser.set_sensitive(False)
        self.status_label.set_text("Corrigiendo errores")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Reparando dependencias...")

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
                    GLib.idle_add(self.update_progress, "Instalando...")

            _, stderr = process.communicate()
            
            if process.returncode == 0:
                self.installed_package = self.file_path
                
                # Mensaje especial para AppImage
                if self.file_path.lower().endswith('.appimage'):
                    app_name = os.path.basename(self.file_path).replace('.appimage', '')
                    GLib.idle_add(self.installation_complete, f"AppImage instalado como {app_name}. Se ha creado un acceso directo.")
                else:
                    GLib.idle_add(self.installation_complete, "Instalación completada correctamente")
            else:
                GLib.idle_add(self.installation_complete, f"Error en la instalación", stderr)
        except Exception as e:
            GLib.idle_add(self.installation_complete, f"Error en la instalación", str(e))

    def run_fix_deps(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    GLib.idle_add(self.update_progress, "Reparando dependencias...")

            _, stderr = process.communicate()
            
            if process.returncode == 0:
                GLib.idle_add(self.fix_deps_complete, "Dependencias corregidas correctamente")
            else:
                GLib.idle_add(self.fix_deps_complete, "Error al corregir dependencias", stderr)
        except Exception as e:
            GLib.idle_add(self.fix_deps_complete, "Error en la instalación de dependencias", str(e))

    def update_progress(self, message=None):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.01)
        self.progress_bar.set_fraction(new_value)
        if message:
            self.progress_bar.set_text(message)
        return False

    def installation_complete(self, message, error_details=None):
        if error_details:
            # Mostrar diálogo de error con detalles
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
            dialog.format_secondary_text(error_details)
            dialog.run()
            dialog.destroy()
            self.progress_bar.set_text("Error en la instalación")
        else:
            # Mostrar diálogo de éxito
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
            dialog.run()
            dialog.destroy()
            self.progress_bar.set_text("Instalación completada")
            
        self.status_label.set_text(message)
        self.progress_bar.set_fraction(1.0)
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(True)
        self.file_chooser.set_sensitive(True)

    def fix_deps_complete(self, message, error_details=None):
        if error_details:
            # Mostrar diálogo de error con detalles
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
            dialog.format_secondary_text(error_details)
            dialog.run()
            dialog.destroy()
            self.progress_bar.set_text("Error al corregir dependencias")
        else:
            # Mostrar diálogo de éxito
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=message
            )
            dialog.run()
            dialog.destroy()
            self.progress_bar.set_text("Dependencias corregidas")
            
        self.status_label.set_text(message)
        self.progress_bar.set_fraction(1.0)
        self.install_button.set_sensitive(True)
        self.fix_deps_button.set_sensitive(True)
        self.file_chooser.set_sensitive(True)

    def on_report_issue(self, widget):
        webbrowser.open("https://github.com/Inled-Group/swiftinstall/issues")
        
    def open_inled_es(self, widget):
        webbrowser.open("https://inled.es")

def Component():
    win = PackageInstaller()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

Component()