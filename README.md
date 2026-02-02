# 🖥️ Supervision Proxmox

Automation script pour déployer rapidement une application web de supervision Proxmox avec un container Alpine ultra-léger.

## 🚀 Installation rapide

Sur un serveur Proxmox (en tant que root):

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Lajavel-gg/supervision-proxmox/main/install.sh)"
```

## 📋 Qu'est-ce que ça fait?

1. ✅ Crée un container Alpine LXC ultra-léger (5 MB)
2. ✅ Installe Python3 + Flask (minimalist)
3. ✅ Déploie l'API de lecture Proxmox
4. ✅ Lance un dashboard web en temps réel
5. ✅ Configure le service systemd pour l'auto-redémarrage

## 🌐 Accès

Une fois installé, accédez à: `http://<IP-CONTAINER>:5000`

## 📊 Fonctionnalités

- ✅ Liste des VMs et containers
- ✅ Status en temps réel (running/stopped)
- ✅ Auto-refresh toutes les 5 secondes
- ✅ API REST simple
- ✅ Dashboard minimaliste et ultra-rapide
- ✅ Consomme très peu de ressources

## 🏗️ Architecture

```
[Proxmox Host]
    ↓
[Script install.sh]
    ↓
[Alpine LXC Container (512 MB RAM)]
    ├── Python3
    ├── Flask API
    └── Dashboard Web (HTML/CSS/JS)
```

## 📡 API Endpoints

- `GET /` - Dashboard web
- `GET /api/vms` - Liste toutes les VMs/containers (JSON)
- `GET /api/status` - Status général du cluster (JSON)
- `GET /api/health` - Health check

### Exemples d'appels API

```bash
# Récupérer toutes les VMs
curl http://localhost:5000/api/vms

# Récupérer le status
curl http://localhost:5000/api/status

# Health check
curl http://localhost:5000/api/health
```

## 📁 Structure du projet

```
supervision-proxmox/
├── install.sh              # Script d'installation automatique
├── app.py                  # Application Flask + API
├── requirements.txt        # Dépendances Python (minimales)
├── templates/
│   └── index.html         # Dashboard HTML/CSS/JS
├── README.md              # Cette documentation
└── .gitignore
```

## 🔧 Développement

### Clone le repo

```bash
git clone https://github.com/Lajavel-gg/supervision-proxmox.git
cd supervision-proxmox
```

### Installation locale (sans Proxmox)

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'app
python3 app.py
```

Accédez à `http://localhost:5000`

## 🛠️ Troubleshooting

### Voir les logs

```bash
pct exec 200 -- tail -f /var/log/supervision.log
```

### Redémarrer le service

```bash
pct exec 200 -- rc-service supervision restart
```

### Arrêter le container

```bash
pct stop 200
```

### Redémarrer le container

```bash
pct reboot 200
```

### Supprimer le container

```bash
pct destroy 200 --purge
```

## 🐛 Erreurs courantes

### "Erreur: Ce script doit être exécuté sur Proxmox"
- Le script doit être lancé sur la machine Proxmox directement
- Connectez-vous en SSH au serveur Proxmox et relancez le script

### "Container $VMID existe déjà"
- Le script détecte qu'un container avec cet ID existe
- Répondez "y" pour le supprimer et le recréer
- Ou changez `VMID=200` à une autre valeur dans le script

### Dashboard vide ou "Erreur"
- Vérifiez que le container est démarré: `pct status 200`
- Vérifiez les logs: `pct exec 200 -- tail -f /var/log/supervision.log`
- Vérifiez que le host Proxmox a bien les commandes `qm` et `pct`

## 📊 Performance

- **Taille du container**: ~200 MB
- **RAM utilisée**: ~50-100 MB (très léger)
- **CPU**: < 1% au repos
- **Refresh**: 5 secondes par défaut

## 🔐 Sécurité

- ⚠️ Le dashboard n'a pas d'authentification (à faire!)
- Le container Alpine est ultra-minimaliste pour réduire les attaques
- À améliorer: ajouter un login/password

## 🚀 Améliorations futures

- [ ] Authentification (login/password)
- [ ] Graphiques temps réel (CPU, RAM, Network)
- [ ] Alertes (Email, Slack, Discord)
- [ ] Actions (start/stop VM depuis le web)
- [ ] Base de données pour l'historique
- [ ] API Plus complète (Proxmox API native)

## 📝 Licence

MIT

## 👨‍💻 Auteur

Lajavel-gg

## 🤝 Contribution

Les pull requests sont bienvenues!

```bash
git checkout -b feature/ma-feature
git commit -m "Add ma-feature"
git push origin feature/ma-feature
```

Puis créez une Pull Request!

## 📞 Support

Pour des problèmes, ouvrez une issue sur GitHub: https://github.com/Lajavel-gg/supervision-proxmox/issues
