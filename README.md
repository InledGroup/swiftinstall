# SwiftInstall

Instala y desinstala aplicaciones fuera de la Store en Linux de forma gráfica.

## Instalar
1. Selecciona el paquete a instalar.
2. Pulsa en **Instalar**.
3. *(Opcional)* Si hay un superusuario, introduce la contraseña de superusuario.

Y ya estaría instalada la aplicación.

## Desinstalar
1. Pulsa en **Eliminar aplicaciones**.
2. Busca la aplicación.
3. Pulsa en la **X**.
4. *(Opcional)* Si hay un superusuario, introduce la contraseña de superusuario.

Y ya estaría desinstalada la aplicación.

## Empezar a usar SwiftInstall
1. Descarga los ficheros `start.py` y `start.sh`.
2. [Instala Python en tu dispositivo](https://python-guide-es.readthedocs.io/es/latest/starting/install3/linux.html).
3. Dale permisos de ejecución a `start.sh` con el siguiente comando:

   ```sh
   chmod +x start.sh
   ```

4. Instala el paquete **GTK y PyGObject** si no los tienes en tu sistema:

   ```sh
   sudo apt update
   sudo apt install -y gir1.2-gtk-3.0 python3-gi
   ```

5. En el gestor de archivos, haz **clic derecho** en `start.sh` y pulsa en **"Ejecutar como programa"**.
