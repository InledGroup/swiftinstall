#!/bin/bash

# Script local para construir el paquete .rpm de AppInstall usando alien
# alien es una herramienta común para convertir paquetes entre formatos

# Asegurar que estamos en el directorio raíz del proyecto
cd "$(dirname "$0")"

# Primero construir el .deb si no existe o para asegurar que está actualizado
./build_deb.sh

DEB_FILE=$(ls appinstall_*.deb | head -n 1)

if [ -z "$DEB_FILE" ]; then
    echo "Error: No se pudo encontrar el archivo .deb para convertir."
    exit 1
fi

echo "Convirtiendo $DEB_FILE a RPM..."

# Intentar usar alien para la conversión
if command -v alien >/dev/null; then
    # --to-rpm: convertir a rpm
    # --scripts: intentar convertir los scripts (postinst)
    # --keep-version: mantener la versión exacta
    sudo alien --to-rpm --scripts --keep-version "$DEB_FILE"
    
    # alien suele dejar el archivo en el directorio actual
    RPM_FILE=$(ls appinstall-*.rpm | head -n 1)
    if [ -n "$RPM_FILE" ]; then
        echo "¡Hecho! El paquete RPM se ha creado: $RPM_FILE"
    else
        echo "Error: Alien terminó pero no encuentro el archivo .rpm resultante."
    fi
else
    echo "Error: 'alien' no está instalado. Por favor instálalo (sudo apt install alien) para convertir el paquete."
    exit 1
fi
