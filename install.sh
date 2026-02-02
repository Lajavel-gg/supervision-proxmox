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

# ==================== TÉLÉCHARGER ALPINE ====================
echo "🏗️  Préparation du template Alpine..."

ALPINE_TEMPLATE="alpine-minirootfs-3.23.0-x86_64.tar.gz"
TEMPLATE_DIR="/var/lib/vz/template/cache"
TEMPLATE_PATH="$TEMPLATE_DIR/$ALPINE_TEMPLATE"

# Vérifier si le template existe déjà
if [ -f "$TEMPLATE_PATH" ]; then
    echo "✅ Template Alpine trouvé localement"
else
    echo "📥 Template non trouvé localement"
    echo "   Téléchargement d'Alpine depuis Internet..."
    echo "   (Cela peut prendre 2-3 minutes selon la connexion)"
    
    # Créer le répertoire s'il n'existe pas
    mkdir -p "$TEMPLATE_DIR"
    
    # URL de téléchargement (depuis le CDN Alpine Linux officiel)
    DOWNLOAD_URL="https://dl-cdn.alpinelinux.org/alpine/v3.23/releases/x86_64/alpine-minirootfs-3.23.0-x86_64.tar.gz"
    
    echo "📡 Téléchargement depuis: $DOWNLOAD_URL"
    
    # Télécharger avec wget (plus fiable)
    if command -v wget &> /dev/null; then
        wget -q --show-progress -O "$TEMPLATE_PATH" "$DOWNLOAD_URL" || {
            echo "❌ Erreur de téléchargement avec wget"
            rm -f "$TEMPLATE_PATH"
            exit 1
        }
    elif command -v curl &> /dev/null; then
        curl -# -o "$TEMPLATE_PATH" "$DOWNLOAD_URL" || {
            echo "❌ Erreur de téléchargement avec curl"
            rm -f "$TEMPLATE_PATH"
            exit 1
        }
    else
        echo "❌ Erreur: wget ou curl requis pour télécharger"
        exit 1
    fi
    
    echo "✅ Téléchargement terminé"
fi

echo "✅ Template Alpine prêt"
# ==============================================================

echo "🏗️  Création du container LXC Alpine (ID: $VMID)..."
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

echo "🌐 Activation de l'interface réseau..."
pct exec $VMID -- ip link set eth0 up
sleep 1

echo "📡 Attente de l'IP DHCP..."
pct exec $VMID -- sh -c 'timeout 30 udhcpc -i eth0' || true
sleep 2

echo "✅ Interface réseau prête"
echo "🔧 Configuration Alpine..."
pct exec $VMID -- apk update
pct exec $VMID -- apk add --no-cache python3 py3-pip git curl bash openrc

echo "📦 Clonage du repo..."
pct exec $VMID -- git clone $REPO_URL /app

echo "📚 Installation dépendances Python..."
pct exec $VMID -- python3 -m venv /app/venv
pct exec $VMID -- /app/venv/bin/pip install -r /app/requirements.txt

echo "🔄 Configuration du démarrage automatique..."
pct exec $VMID -- mkdir -p /var/log

# Ajouter la commande de lancement dans rc.local
pct exec $VMID -- sh -c 'echo "#!/bin/sh" > /etc/rc.local'
pct exec $VMID -- sh -c 'echo "/app/venv/bin/python3 /app/app.py > /var/log/supervision.log 2>&1 &" >> /etc/rc.local'
pct exec $VMID -- chmod +x /etc/rc.local

# Lancer tout de suite pour le test
pct exec $VMID -- /app/venv/bin/python3 /app/app.py > /dev/null 2>&1 &

sleep 5

echo ""
echo "✅ Installation terminée!"
echo ""

# Attendre un peu que tout soit stable
sleep 2

# Récupérer l'IP du container
IP_CONTAINER=$(pct config $VMID | grep "^net0" | grep -oP '(?<=ip=)[^,]*' | cut -d'/' -f1)

# Si pas d'IP statique, chercher l'IP dynamique
if [ -z "$IP_CONTAINER" ] || [ "$IP_CONTAINER" = "dhcp" ]; then
    IP_CONTAINER=$(pct exec $VMID -- ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "DHCP")
fi

echo "🌐 Dashboard disponible à: http://$IP_CONTAINER:5000"
echo ""
echo "📝 Commandes utiles:"
echo "   Voir les logs: pct exec $VMID -- tail -f /var/log/supervision.log"
echo "   Vérifier si l'app tourne: pct exec $VMID -- ps aux | grep python3"
echo "   Arrêter: pct stop $VMID"
echo "   Redémarrer: pct reboot $VMID"
echo "   Supprimer: pct destroy $VMID --purge"
echo ""
