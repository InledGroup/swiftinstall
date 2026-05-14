#!/bin/bash

# Script local para construir el paquete .deb de AppInstall

# Asegurar que estamos en el directorio raíz del proyecto
cd "$(dirname "$0")"

# Nombre del paquete y versión (extraídos del archivo control)
PACKAGE_NAME=$(grep '^Package:' appinstall/DEBIAN/control | cut -d' ' -f2)
VERSION=$(grep '^Version:' appinstall/DEBIAN/control | cut -d' ' -f2)
ARCH=$(grep '^Architecture:' appinstall/DEBIAN/control | cut -d' ' -f2)

DEB_FILE="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "Construyendo $DEB_FILE..."

# Sincronizar archivos del código fuente a la estructura del paquete
echo "Sincronizando archivos..."
mkdir -p appinstall/usr/share/appinstall/
cp start.py appinstall/usr/share/appinstall/
cp styles.css appinstall/usr/share/appinstall/
cp appimage.png appinstall/usr/share/appinstall/

# Ajustar permisos necesarios para el paquete Debian
echo "Ajustando permisos..."
chmod -R 755 appinstall/usr
chmod 755 appinstall/DEBIAN/postinst
# Los archivos de control deben tener permisos específicos (644)
chmod 644 appinstall/DEBIAN/control

# Construir el paquete
if command -v dpkg-deb >/dev/null; then
    dpkg-deb --root-owner-group --build appinstall "$DEB_FILE"
    echo "¡Hecho! El paquete se ha creado: $DEB_FILE"
else
    echo "Error: dpkg-deb no está instalado. No puedo construir el paquete."
    exit 1
fi
