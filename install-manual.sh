#!/bin/bash

# Script de instalación manual de SwiftInstall

echo "Instalando SwiftInstall manualmente..."

# Crear directorios
sudo mkdir -p /usr/share/swiftinstall
sudo mkdir -p /usr/share/applications
sudo mkdir -p /usr/share/pixmaps

# Copiar archivos
sudo cp start.py /usr/share/swiftinstall/
sudo cp styles.css /usr/share/swiftinstall/
sudo cp appimage.png /usr/share/swiftinstall/
sudo cp swiftinstall/usr/share/applications/swiftinstall.desktop /usr/share/applications/
sudo cp swiftinstall/usr/share/pixmaps/swiftinstall.png /usr/share/pixmaps/

# Crear script ejecutable
sudo tee /usr/bin/swiftinstall > /dev/null << 'EOF'
#!/bin/bash
python3 "/usr/share/swiftinstall/start.py"
EOF

# Dar permisos
sudo chmod +x /usr/bin/swiftinstall

echo "SwiftInstall instalado correctamente!"
echo "Puedes ejecutarlo con: swiftinstall"
echo "O buscarlo en el menú de aplicaciones como 'Swift Install'"