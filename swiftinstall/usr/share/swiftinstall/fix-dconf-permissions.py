import os
import subprocess
import sys

def fix_dconf_permissions():
    """
    Corrige los permisos de dconf para la aplicación Swift Install.
    Este script debe ejecutarse antes de iniciar la aplicación principal.
    """
    # Obtener el ID de usuario actual
    user_id = os.getuid()
    user_runtime_dir = f"/run/user/{user_id}"
    
    # Verificar si existe el directorio
    if not os.path.exists(user_runtime_dir):
        print(f"El directorio {user_runtime_dir} no existe. Creándolo...")
        try:
            # Crear el directorio con los permisos correctos
            subprocess.run(['pkexec', 'mkdir', '-p', user_runtime_dir], check=True)
            subprocess.run(['pkexec', 'chown', f"{user_id}:{user_id}", user_runtime_dir], check=True)
            subprocess.run(['pkexec', 'chmod', '700', user_runtime_dir], check=True)
            print(f"Directorio {user_runtime_dir} creado correctamente.")
        except subprocess.CalledProcessError as e:
            print(f"Error al crear el directorio: {e}")
            return False
    
    # Verificar el directorio dconf
    dconf_dir = os.path.join(user_runtime_dir, 'dconf')
    if not os.path.exists(dconf_dir):
        print(f"El directorio {dconf_dir} no existe. Creándolo...")
        try:
            # Crear el directorio dconf con los permisos correctos
            subprocess.run(['mkdir', '-p', dconf_dir], check=True)
            print(f"Directorio {dconf_dir} creado correctamente.")
        except subprocess.CalledProcessError as e:
            print(f"Error al crear el directorio dconf: {e}")
            return False
    
    # Verificar permisos
    try:
        # Asegurar que el usuario es propietario del directorio dconf
        subprocess.run(['pkexec', 'chown', '-R', f"{user_id}:{user_id}", dconf_dir], check=True)
        subprocess.run(['pkexec', 'chmod', '-R', '700', dconf_dir], check=True)
        print("Permisos de dconf corregidos correctamente.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error al corregir permisos: {e}")
        return False

def main():
    print("Verificando permisos de dconf...")
    if fix_dconf_permissions():
        print("Permisos corregidos. Iniciando Swift Install...")
        
        # Importar y ejecutar el script principal
        try:
            # Asegurar que XDG_RUNTIME_DIR está configurado correctamente
            user_id = os.getuid()
            os.environ['XDG_RUNTIME_DIR'] = f"/run/user/{user_id}"
            
            # Importar el módulo principal y ejecutarlo
            from start import Component
            Component()
        except ImportError:
            print("Error: No se pudo importar el módulo principal.")
            print("Asegúrate de que el archivo start.py está en el mismo directorio.")
            sys.exit(1)
    else:
        print("No se pudieron corregir los permisos de dconf.")
        print("Intentando iniciar Swift Install de todos modos...")
        
        try:
            from start import Component
            Component()
        except ImportError:
            print("Error: No se pudo importar el módulo principal.")
            sys.exit(1)

if __name__ == "__main__":
    main()