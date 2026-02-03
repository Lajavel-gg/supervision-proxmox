#!/usr/bin/env python3
"""
Supervision Proxmox - API et Dashboard
Alpine LXC compatible
Connexion à l'API Proxmox pour lire les VMs en temps réel
"""

import os
import subprocess
import json
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify
from requests.auth import HTTPBasicAuth

# Configuration Proxmox depuis les variables d'environnement
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "localhost")
PROXMOX_API_USER = os.getenv("PROXMOX_API_USER", "root@pam")
PROXMOX_API_PASSWORD = os.getenv("PROXMOX_API_PASSWORD", "")

# URL de l'API Proxmox
PROXMOX_API_URL = f"https://{PROXMOX_HOST}:8006/api2/json"

app = Flask(__name__)

# Désactiver les avertissements SSL (Proxmox utilise un certificat auto-signé)
requests.packages.urllib3.disable_warnings()

def get_proxmox_ticket():
    """Obtenir un ticket d'authentification Proxmox"""
    try:
        auth_url = f"{PROXMOX_API_URL}/access/ticket"
        
        response = requests.post(
            auth_url,
            data={
                'username': PROXMOX_API_USER,
                'password': PROXMOX_API_PASSWORD,
                'realm': 'pam'
            },
            verify=False,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                'ticket': data.get('data', {}).get('ticket'),
                'csrftoken': data.get('data', {}).get('CSRFPreventionToken')
            }
        return None
        
    except Exception as e:
        print(f"Erreur auth Proxmox: {e}")
        return None

def get_proxmox_vms():
    """Récupérer la liste des VMs depuis l'API Proxmox"""
    try:
        # Obtenir un ticket d'auth
        auth = get_proxmox_ticket()
        if not auth or not auth.get('ticket'):
            print("Impossible de s'authentifier à Proxmox")
            return []
        
        cookies = {'PVEAuthCookie': auth['ticket']}
        headers = {'CSRFPreventionToken': auth['csrftoken']}
        
        response = requests.get(
            f"{PROXMOX_API_URL}/nodes",
            cookies=cookies,
            headers=headers,
            verify=False,
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"Erreur API Proxmox: {response.status_code}")
            return []
        
        nodes = response.json().get("data", [])
        vms = []
        
        # Pour chaque nœud, récupérer les VMs
        for node in nodes:
            node_name = node["node"]
            
            # VMs QEMU
            try:
                qm_response = requests.get(
                    f"{PROXMOX_API_URL}/nodes/{node_name}/qemu",
                    cookies=cookies,
                    headers=headers,
                    verify=False,
                    timeout=5
                )
                
                if qm_response.status_code == 200:
                    for vm in qm_response.json().get("data", []):
                        vms.append({
                            'id': vm['vmid'],
                            'name': vm['name'],
                            'type': 'VM',
                            'status': vm['status'],
                            'node': node_name,
                            'memory': vm.get('mem', 0),
                            'maxmem': vm.get('maxmem', 0),
                            'cpu': vm.get('cpus', 0)
                        })
            except:
                pass
            
            # Containers LXC
            try:
                lxc_response = requests.get(
                    f"{PROXMOX_API_URL}/nodes/{node_name}/lxc",
                    cookies=cookies,
                    headers=headers,
                    verify=False,
                    timeout=5
                )
                
                if lxc_response.status_code == 200:
                    for container in lxc_response.json().get("data", []):
                        vms.append({
                            'id': container['vmid'],
                            'name': container['hostname'],
                            'type': 'LXC',
                            'status': container['status'],
                            'node': node_name,
                            'memory': container.get('mem', 0),
                            'maxmem': container.get('maxmem', 0),
                            'cpu': container.get('cpus', 0)
                        })
            except:
                pass
        
        return vms
        
    except Exception as e:
        print(f"Erreur récupération VMs: {e}")
        return []

@app.route('/')
def dashboard():
    """Dashboard principal"""
    return render_template('index.html')

@app.route('/api/vms')
def api_vms():
    """API: liste des VMs depuis Proxmox"""
    vms = get_proxmox_vms()
    return jsonify(vms)

@app.route('/api/status')
def api_status():
    """API: status général du cluster"""
    try:
        vms = get_proxmox_vms()
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'total_vms': len(vms),
            'running': len([v for v in vms if v['status'] == 'running']),
            'stopped': len([v for v in vms if v['status'] != 'running']),
            'proxmox_host': PROXMOX_HOST
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Supervision Proxmox démarrée sur http://0.0.0.0:5000")
    print(f"   Connecté à Proxmox: {PROXMOX_HOST}")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
