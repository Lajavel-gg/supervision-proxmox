# Supervision Proxmox

Application web de supervision pour Proxmox VE. Deploiement automatise dans un container Alpine LXC ultra-leger.

## Presentation

Cette application permet de superviser un cluster Proxmox VE via une interface web moderne et reactive. Elle utilise l'API native de Proxmox pour recuperer les informations en temps reel sur les machines virtuelles, containers et noeuds du cluster.

### Fonctionnalites principales

- **Dashboard temps reel** : Visualisation de l'etat des VMs et containers avec rafraichissement automatique
- **Monitoring des noeuds** : CPU, RAM, stockage avec jauges circulaires
- **Graphiques historiques** : Evolution des metriques sur la derniere heure (donnees RRD Proxmox)
- **Details des VMs** : Panel lateral avec informations detaillees (config, ressources, reseau, stockage)
- **Activite recente** : Journal des actions du cluster (demarrages, arrets, backups, erreurs)
- **Filtres et recherche** : Filtrage par status (running/stopped), type (VM/LXC) et recherche par nom

### Captures d'ecran

<img width="1541" height="1012" alt="image" src="https://github.com/user-attachments/assets/f4f309ef-d128-4d4a-8b1a-b81b1e9bce93" />


## Installation

### Pre-requis

- Serveur Proxmox VE 7.x ou 8.x
- Acces root au serveur Proxmox
- Connexion internet (pour telecharger le template Alpine)

### Installation automatique

Executez cette commande sur le serveur Proxmox en tant que root :

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Lajavel-gg/supervision-proxmox/main/install.sh)"
```

Le script effectue les operations suivantes :

1. Creation d'un utilisateur API Proxmox avec permissions en lecture seule (PVEAuditor)
2. Generation d'un token API securise
3. Telechargement du template Alpine Linux
4. Creation et configuration du container LXC
5. Installation des dependances (Python3, Flask)
6. Deploiement de l'application
7. Configuration du demarrage automatique

### Acces au dashboard

Une fois l'installation terminee, accedez a l'interface web :

```
http://<IP-CONTAINER>:5000
```

## Architecture technique

```
Proxmox VE Host
    |
    +-- API Proxmox (port 8006)
    |       |
    |       v
    +-- Container LXC Alpine
            |
            +-- Python 3 + Flask
            |       |
            |       +-- API REST (lecture seule)
            |       +-- Templates HTML/CSS/JS
            |
            +-- Dashboard Web (port 5000)
```

### Technologies utilisees

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Backend | Python / Flask | 3.x / 3.0 |
| Frontend | HTML5 / CSS3 / JavaScript | - |
| Container | Alpine Linux | 3.23 |
| API | Proxmox VE API | 7.x / 8.x |

### Securite

- **Lecture seule** : Le token API utilise le role PVEAuditor (aucune action possible)
- **Container isole** : L'application tourne dans un LXC dedie
- **Pas d'authentification** : A implementer pour un usage en production

## API REST

L'application expose plusieurs endpoints JSON :

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard web |
| `GET /api/vms` | Liste des VMs et containers |
| `GET /api/status` | Status general du cluster |
| `GET /api/nodes` | Informations des noeuds |
| `GET /api/nodes/<node>/rrddata` | Historique metriques d'un noeud |
| `GET /api/vm/<node>/<type>/<vmid>` | Details d'une VM/LXC |
| `GET /api/vm/<node>/<type>/<vmid>/rrddata` | Historique metriques d'une VM |
| `GET /api/tasks` | Activite recente du cluster |
| `GET /api/health` | Health check |

### Exemples

```bash
# Liste des VMs
curl http://192.168.1.100:5000/api/vms

# Status du cluster
curl http://192.168.1.100:5000/api/status

# Details d'une VM
curl http://192.168.1.100:5000/api/vm/proxmox/VM/101

# Historique CPU d'un noeud (derniere heure)
curl http://192.168.1.100:5000/api/nodes/proxmox/rrddata?timeframe=hour
```

## Maintenance

### Mise a jour de l'application

```bash
# Remplacer VMID par l'ID de votre container (ex: 100)

# Telecharger les mises a jour
pct exec VMID -- git -C /app pull

# Redemarrer l'application
pct exec VMID -- pkill -f "python3 /app/app.py"
pct enter VMID
. /etc/supervision.env && nohup /app/venv/bin/python3 /app/app.py > /var/log/supervision.log 2>&1 &
exit
```

### Commandes utiles

```bash
# Voir les logs
pct exec VMID -- tail -f /var/log/supervision.log

# Verifier si l'application tourne
pct exec VMID -- ps aux | grep python

# Arreter l'application
pct exec VMID -- pkill -f "python3 /app/app.py"

# Redemarrer le container
pct reboot VMID

# Supprimer le container
pct destroy VMID --purge
```

## Structure du projet

```
supervision-proxmox/
|-- install.sh              # Script d'installation automatique
|-- app.py                  # Application Flask (API + routes)
|-- requirements.txt        # Dependances Python
|-- templates/
|   +-- index.html          # Dashboard (HTML/CSS/JS)
|-- README.md
+-- .gitignore
```

## Performance

| Metrique | Valeur |
|----------|--------|
| Taille du container | ~200 MB |
| RAM utilisee | 50-100 MB |
| CPU au repos | < 1% |
| Rafraichissement | 5 secondes |

## Developpement local

```bash
# Cloner le projet
git clone https://github.com/Lajavel-gg/supervision-proxmox.git
cd supervision-proxmox

# Creer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r requirements.txt

# Configurer les variables d'environnement
export PROXMOX_HOST="192.168.1.1"
export PROXMOX_API_USER="supervision@pve"
export PROXMOX_API_TOKEN_NAME="supervision-token"
export PROXMOX_API_TOKEN="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Lancer l'application
python3 app.py
```

## Licence

MIT

## Auteur

Lajavel-gg

---

Projet realise dans le cadre d'un fil rouge de formation.
