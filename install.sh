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
PROXMOX_HOST="localhost"
PROXMOX_API_USER="supervision@pve"
# ===============================================

echo "📥 Vérification des prérequis..."
if ! command -v pct &> /dev/null; then
    echo "❌ Erreur: Ce script doit être exécuté sur Proxmox (commande 'pct' non trouvée)"
    exit 1
fi

# ==================== DÉTECTER L'IP PROXMOX ====================
echo "🔍 Détection de l'adresse IP Proxmox..."
PROXMOX_HOST=$(hostname -I | awk '{print $1}')
if [ -z "$PROXMOX_HOST" ]; then
    PROXMOX_HOST="127.0.0.1"
fi
echo "✅ IP Proxmox détectée: $PROXMOX_HOST"
# ==================================================================
echo "🔐 Configuration de l'API Proxmox..."

PROXMOX_API_USER="supervision@pve"

# Créer l'user s'il n'existe pas
if ! pveum user list | grep -q "$PROXMOX_API_USER"; then
    echo "👤 Création de l'user Proxmox: $PROXMOX_API_USER"
    pveum user add $PROXMOX_API_USER -comment "User API Supervision" 2>/dev/null || true
else
    echo "✅ User Proxmox existe déjà"
fi

# Donner les permissions
echo "🔑 Attribution des permissions..."
pveum acl modify / --roles PVEVMUser --users $PROXMOX_API_USER 2>/dev/null || true

# Créer le token API avec un nom unique
TOKEN_NAME="supervision-$(date +%s)"
echo "🔑 Création du token API: $TOKEN_NAME"

# Extraire le token correctement (c'est un UUID au format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
API_TOKEN_VALUE=$(pveum user token add $PROXMOX_API_USER $TOKEN_NAME 2>/dev/null | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}')

if [ -z "$API_TOKEN_VALUE" ]; then
    echo "⚠️  Impossible de créer le token automatiquement"
    API_TOKEN_VALUE="TOKEN_NOT_CREATED"
fi

echo "✅ API Proxmox configurée"
echo "   User: $PROXMOX_API_USER"
echo "   Token: ${API_TOKEN_VALUE:0:8}..."
# ===================================================================
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

# Créer un script de startup qui passe les variables CORRECTEMENT à Python
pct exec $VMID -- tee /usr/local/bin/start-supervision.sh > /dev/null << 'STARTUP_SCRIPT'
#!/bin/sh
# Script de démarrage pour Supervision Proxmox

# Source les variables d'environnement
if [ -f /etc/supervision.env ]; then
    . /etc/supervision.env
fi

# Passer les variables EXPLICITEMENT à Python via exec
exec env PROXMOX_HOST="${PROXMOX_HOST:-localhost}" \
         PROXMOX_API_USER="${PROXMOX_API_USER:-supervision@pve}" \
         PROXMOX_API_TOKEN="${PROXMOX_API_TOKEN:-}" \
         /app/venv/bin/python3 /app/app.py > /var/log/supervision.log 2>&1
STARTUP_SCRIPT

pct exec $VMID -- chmod +x /usr/local/bin/start-supervision.sh

# Écrire les variables dans le fichier d'environnement
pct exec $VMID -- sh -c "cat > /etc/supervision.env << 'ENV_FILE'
PROXMOX_HOST=\"${PROXMOX_HOST}\"
PROXMOX_API_USER=\"${PROXMOX_API_USER}\"
PROXMOX_API_TOKEN=\"${API_TOKEN_VALUE}\"
ENV_FILE"

# Créer un vrai rc.local qui source les variables ET lance le script
pct exec $VMID -- sh -c 'cat > /etc/rc.local << "RCLOCAL_FILE"
#!/bin/sh
# Source les variables d environnement
[ -f /etc/supervision.env ] && . /etc/supervision.env
# Lancer le script
/usr/local/bin/start-supervision.sh
exit 0
RCLOCAL_FILE'

pct exec $VMID -- chmod +x /etc/rc.local

# Lancer l'app immédiatement pour tester
pct exec $VMID -- sh -c "PROXMOX_HOST='${PROXMOX_HOST}' PROXMOX_API_USER='${PROXMOX_API_USER}' PROXMOX_API_TOKEN='${API_TOKEN_VALUE}' /usr/local/bin/start-supervision.sh"

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
