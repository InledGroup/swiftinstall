#!/bin/bash

# Script local para construir el paquete .deb de SwiftInstall

# Asegurar que estamos en el directorio raíz del proyecto
cd "$(dirname "$0")"

# Nombre del paquete y versión (extraídos del archivo control)
PACKAGE_NAME=$(grep '^Package:' swiftinstall/DEBIAN/control | cut -d' ' -f2)
VERSION=$(grep '^Version:' swiftinstall/DEBIAN/control | cut -d' ' -f2)
ARCH=$(grep '^Architecture:' swiftinstall/DEBIAN/control | cut -d' ' -f2)

DEB_FILE="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "Construyendo $DEB_FILE..."

# Sincronizar archivos del código fuente a la estructura del paquete
echo "Sincronizando archivos..."
mkdir -p swiftinstall/usr/share/swiftinstall/
cp start.py swiftinstall/usr/share/swiftinstall/
cp styles.css swiftinstall/usr/share/swiftinstall/
cp appimage.png swiftinstall/usr/share/swiftinstall/

# Ajustar permisos necesarios para el paquete Debian
echo "Ajustando permisos..."
chmod -R 755 swiftinstall/usr
chmod 755 swiftinstall/DEBIAN/postinst
# Los archivos de control deben tener permisos específicos (644)
chmod 644 swiftinstall/DEBIAN/control

# Construir el paquete
if command -v dpkg-deb >/dev/null; then
    dpkg-deb --root-owner-group --build swiftinstall "$DEB_FILE"
    echo "¡Hecho! El paquete se ha creado: $DEB_FILE"
else
    echo "Error: dpkg-deb no está instalado. No puedo construir el paquete."
    exit 1
fi
