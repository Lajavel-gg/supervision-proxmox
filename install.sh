#!/bin/bash
# Installation supervision Proxmox avec Alpine
# Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/Lajavel-gg/supervision-proxmox/main/install.sh)"

set -e

echo "🚀 Déploiement Supervision Proxmox (Alpine)..."

# ==================== CONFIG ====================
HOSTNAME="supervision-proxmox"
IP="dhcp"
MEMORY=512
CORES=1
STORAGE="local-lvm"
REPO_URL="https://github.com/Lajavel-gg/supervision-proxmox"
# ===============================================

echo "📥 Vérification des prérequis..."
if ! command -v pct &> /dev/null; then
    echo "❌ Erreur: Ce script doit être exécuté sur Proxmox (commande 'pct' non trouvée)"
    exit 1
fi

# ==================== TROUVER UN ID DISPONIBLE ====================
echo "🔍 Recherche d'un ID de container disponible..."
VMID=100
while pct status $VMID &>/dev/null; do
    VMID=$((VMID + 1))
done
echo "✅ ID disponible trouvé: $VMID"
# ==================================================================

echo "🏗️  Vérification du template Alpine..."

# Chercher dans les templates déjà téléchargés
ALPINE_TEMPLATE=$(pveam list local 2>/dev/null | grep -i alpine | grep amd64 | head -1 | awk '{print $1}' | sed 's|local:vztmpl/||')

if [ -z "$ALPINE_TEMPLATE" ]; then
    echo "📥 Aucun template Alpine trouvé localement"
    echo "   Recherche des templates disponibles en ligne..."
    
    # Chercher dans les templates disponibles
    ALPINE_TEMPLATE=$(pveam list content 2>/dev/null | grep -i "alpine.*amd64" | head -1 | awk '{print $1}')
    
    if [ -z "$ALPINE_TEMPLATE" ]; then
        echo "❌ Aucun template Alpine trouvé"
        echo "   Veuillez télécharger manuellement via l'interface Proxmox"
        exit 1
    fi
    
    echo "📥 Téléchargement de $ALPINE_TEMPLATE..."
    pveam download local $ALPINE_TEMPLATE
fi

echo "✅ Template Alpine: $ALPINE_TEMPLATE"
echo "🏗️  Création du container LXC Alpine..."
pct create $VMID local:vztmpl/$ALPINE_TEMPLATE \
  -hostname $HOSTNAME \
  -net0 name=eth0,ip=$IP,bridge=vmbr0 \
  -memory $MEMORY \
  -cores $CORES \
  -storage $STORAGE \
  -onboot 1

echo "⚡ Démarrage du container..."
pct start $VMID
sleep 3

echo "🔧 Configuration Alpine..."
pct exec $VMID -- apk update
pct exec $VMID -- apk add --no-cache python3 py3-pip git curl bash

echo "📦 Clonage du repo..."
pct exec $VMID -- git clone $REPO_URL /app

echo "📚 Installation dépendances Python..."
pct exec $VMID -- pip3 install --no-cache-dir -r /app/requirements.txt

echo "🔄 Configuration du service..."
pct exec $VMID -- tee /etc/init.d/supervision > /dev/null << 'EOF'
#!/sbin/openrc-run

description="Supervision Proxmox"
command="/usr/bin/python3"
command_args="/app/app.py"
command_background=yes
pidfile="/var/run/supervision.pid"
stderr_file="/var/log/supervision.log"
stdout_file="/var/log/supervision.log"

depend() {
    need net
}

EOF

pct exec $VMID -- chmod +x /etc/init.d/supervision
pct exec $VMID -- rc-service supervision start
pct exec $VMID -- rc-update add supervision

sleep 2

echo ""
echo "✅ Installation terminée!"
echo ""
IP_CONTAINER=$(pct exec $VMID -- ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
echo "🌐 Accédez à: http://$IP_CONTAINER:5000"
echo ""
echo "Commandes utiles:"
echo "  Voir les logs: pct exec $VMID -- tail -f /var/log/supervision.log"
echo "  Arrêter: pct stop $VMID"
echo "  Redémarrer: pct reboot $VMID"
echo "  Supprimer: pct destroy $VMID --purge"
