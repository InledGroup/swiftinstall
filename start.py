import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gio, Gdk
import subprocess
import os
import threading
import webbrowser
import requests
from packaging import version
from gi.repository import Gtk, GLib

# Versión actual de la aplicación
CURRENT_VERSION = "4.0"  # Cambia esto a la versión actual de tu aplicación
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
        
        self.set_default_size(350, 150)
        
        content_area = self.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        
        label = Gtk.Label()
        label.set_markup(
            f"<b>Hay una nueva versión disponible!</b>\n\n"
            f"Versión actual: {CURRENT_VERSION}\n"
            f"Nueva versión: {latest_version}\n\n"
            f"¿Desea actualizar ahora?"
        )
        content_area.add(label)
        
        self.release_url = release_url
        self.show_all()

class InstalledAppsWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Aplicaciones instaladas")
        self.set_default_size(400, 300)
        self.set_transient_for(parent)
        self.set_modal(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar aplicaciones...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.listbox = Gtk.ListBox()
        scrolled_window.add(self.listbox)
        self.listbox.set_filter_func(self.filter_func)

        self.overlay = Gtk.Overlay()
        self.overlay.add(scrolled_window)
        main_box.pack_start(self.overlay, True, True, 0)

        self.progress_bar = Gtk.ProgressBar()
        main_box.pack_start(self.progress_bar, False, False, 0)
        self.progress_bar.hide()

        self.load_installed_apps()
    
    def load_installed_apps(self):
        def add_app(package_name):
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add(hbox)
            label = Gtk.Label(label=package_name, xalign=0)
            hbox.pack_start(label, True, True, 0)
            button = Gtk.Button(label="x")
            button.connect("clicked", self.on_uninstall_clicked, package_name)
            hbox.pack_start(button, False, False, 0)
            self.listbox.add(row)
            row.show_all()
            return False

        def load_apps():
            try:
                output = subprocess.check_output(['dpkg', '--get-selections']).decode('utf-8')
                for line in output.split('\n'):
                    if line.strip():
                        package_name = line.split()[0]
                        GLib.idle_add(add_app, package_name)
            except subprocess.CalledProcessError:
                label = Gtk.Label(label="No se pudieron recuperar las aplicaciones instaladas")
                self.listbox.add(label)
            
            return False

        GLib.idle_add(load_apps)
    
    def on_search_changed(self, entry):
        self.listbox.invalidate_filter()
    
    def filter_func(self, row):
        text = self.search_entry.get_text().lower()
        if not text:
            return True
        label = row.get_child().get_children()[0]
        return text in label.get_text().lower()
    
    def on_uninstall_clicked(self, button, package_name):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"¿Deseas desinstalar {package_name}?"
        )
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            self.uninstall_package(package_name)
    
    def uninstall_package(self, package_name):
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.show()
        
        cmd = ['pkexec', 'apt-get', 'remove', '-y', package_name]
        thread = threading.Thread(target=self.run_uninstall, args=(cmd, package_name))
        thread.daemon = True
        thread.start()
    
    def run_uninstall(self, cmd, package_name):
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
                GLib.idle_add(self.uninstall_complete, package_name, True)
            else:
                GLib.idle_add(self.uninstall_complete, package_name, False, str(stderr))
        except subprocess.CalledProcessError as e:
            GLib.idle_add(self.uninstall_complete, package_name, False, str(e))
    
    def update_uninstall_progress(self):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.05)
        self.progress_bar.set_fraction(new_value)
        return False

    def uninstall_complete(self, package_name, success, error_message=None):
        self.progress_bar.hide()
        self.progress_bar.set_fraction(0.0)
        
        if success:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=f"{package_name} ha sido desinstalado correctamente."
            )
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=f"Error al desinstalar {package_name}.",
                secondary_text=error_message
            )
        dialog.run()
        dialog.destroy()
        self.load_installed_apps()  # Refrescar la lista


class PackageInstaller(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Swift Install")
        self.set_border_width(10)
        self.set_default_size(400, 250)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Menu bar
        menu_bar = Gtk.MenuBar()
        vbox.pack_start(menu_bar, False, False, 0)

        # About menu
        about_menu = Gtk.MenuItem(label=f"Acerca de Swift Install v{CURRENT_VERSION}")
        menu_bar.append(about_menu)

        about_submenu = Gtk.Menu()
        about_menu.set_submenu(about_submenu)

        author_item = Gtk.MenuItem(label="Inled Group")
        author_item.connect("activate", self.open_inled_es)
        about_submenu.append(author_item)

        report_item = Gtk.MenuItem(label="Reportar un error")
        report_item.connect("activate", self.on_report_issue)
        about_submenu.append(report_item)

        # Añadir elemento de menú para comprobar actualizaciones
        update_item = Gtk.MenuItem(label="Buscar actualizaciones")
        update_item.connect("activate", self.on_check_updates_clicked)
        about_submenu.append(update_item)

        self.file_chooser = Gtk.FileChooserButton(title="seleccione paquete")
        self.file_chooser.connect("file-set", self.on_file_selected)
        vbox.pack_start(self.file_chooser, True, True, 0)

        button_box = Gtk.Box(spacing=6)
        vbox.pack_start(button_box, True, True, 0)

        self.install_button = Gtk.Button(label="Instalar")
        self.install_button.connect("clicked", self.on_install_clicked)
        self.install_button.set_sensitive(False)
        button_box.pack_start(self.install_button, True, True, 0)

        self.fix_deps_button = Gtk.Button(label="Corregir errores")
        self.fix_deps_button.connect("clicked", self.on_fix_deps_clicked)
        button_box.pack_start(self.fix_deps_button, True, True, 0)

        self.apps_button = Gtk.Button(label="Eliminar aplicaciones")
        self.apps_button.connect("clicked", self.on_apps_clicked)
        button_box.pack_start(self.apps_button, True, True, 0)

        # Contenedor para el spinner y la barra de progreso
        self.progress_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(self.progress_container, True, True, 0)
        
        # Barra de progreso existente
        self.progress_bar = Gtk.ProgressBar()
        self.progress_container.pack_start(self.progress_bar, True, True, 0)

        self.status_label = Gtk.Label(label="Seleccione un paquete a instalar")
        vbox.pack_start(self.status_label, True, True, 0)

        self.installed_package = None
        
        # Comprobar actualizaciones al iniciar la aplicación
        GLib.timeout_add(500, self.check_updates_on_startup)

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
        self.apps_button.set_sensitive(False)
        self.file_chooser.set_sensitive(False)
        self.status_label.set_text("Instalando...")
        self.progress_bar.set_fraction(0.0)

        file_extension = os.path.splitext(self.file_path)[1].lower()

        if file_extension == '.deb':
            cmd = ['pkexec', 'dpkg', '-i', self.file_path]
        elif file_extension == '.rpm':
            cmd = ['pkexec', 'rpm', '-i', self.file_path]
        elif file_extension == '.appimage':
            cmd = ['chmod', '+x', self.file_path]
            subprocess.run(cmd)
            cmd = [self.file_path]
        elif file_extension in ('.tar.xz', '.tar.gz', '.tgz'):
            extract_dir = os.path.expanduser('~/.local')
            cmd = ['tar', '-xvf', self.file_path, '-C', extract_dir]
        else:
            self.status_label.set_text("Formato de paquete no soportado por Swift Install")
            self.install_button.set_sensitive(True)
            self.file_chooser.set_sensitive(True)
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
        self.file_chooser.set_sensitive(False)
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
                GLib.idle_add(self.installation_complete, "Instalado")
            else:
                GLib.idle_add(self.installation_complete, f"Hemos tenido unos errores al instalar: {stderr}")
        except Exception as e:
            GLib.idle_add(self.installation_complete, f"No hemos podido instalar por esto: {str(e)}")


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
                GLib.idle_add(self.fix_deps_complete, "Corregimos los errores!")
            else:
                GLib.idle_add(self.fix_deps_complete, f"Hemos encontrado errores al intentar solucionarlos: {stderr}")
        except Exception as e:
            GLib.idle_add(self.fix_deps_complete, f"Error en la instalación de dependencias: {str(e)}")

    def update_progress(self):
        new_value = min(1.0, self.progress_bar.get_fraction() + 0.01)
        self.progress_bar.set_fraction(new_value)
        return False

    def installation_complete(self, message):
        self.status_label.set_text(message)
        self.progress_bar.set_fraction(1.0)
        self.install_button.set_sensitive(False)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)
        self.file_chooser.set_sensitive(True)

    def fix_deps_complete(self, message):
        self.status_label.set_text(message)
        self.progress_bar.set_fraction(1.0)
        self.install_button.set_sensitive(True)
        self.fix_deps_button.set_sensitive(True)
        self.apps_button.set_sensitive(True)
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