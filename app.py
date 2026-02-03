#!/usr/bin/env python3
"""
Supervision Proxmox - API et Dashboard
Alpine LXC compatible
Connexion à l'API Proxmox avec Token API
"""

import os
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

# Configuration Proxmox depuis les variables d'environnement
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "localhost")
PROXMOX_API_USER = os.getenv("PROXMOX_API_USER", "root@pam")
PROXMOX_API_TOKEN_NAME = os.getenv("PROXMOX_API_TOKEN_NAME", "")
PROXMOX_API_TOKEN = os.getenv("PROXMOX_API_TOKEN", "")

# URL de l'API Proxmox
PROXMOX_API_URL = f"https://{PROXMOX_HOST}:8006/api2/json"

app = Flask(__name__)

# Désactiver les avertissements SSL
requests.packages.urllib3.disable_warnings()

def get_headers():
    """Retourne les headers d'authentification"""
    return {
        "Authorization": f"PVEAPIToken={PROXMOX_API_USER}!{PROXMOX_API_TOKEN_NAME}={PROXMOX_API_TOKEN}"
    }

def format_uptime(seconds):
    """Convertit les secondes en format lisible"""
    if not seconds:
        return "N/A"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}j {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def format_bytes(bytes_val):
    """Convertit les bytes en format lisible"""
    if not bytes_val:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"

def get_node_status():
    """Récupérer les informations du nœud Proxmox (CPU, RAM, Disque)"""
    try:
        headers = get_headers()

        # Récupérer les nœuds
        response = requests.get(
            f"{PROXMOX_API_URL}/nodes",
            headers=headers,
            verify=False,
            timeout=5
        )

        if response.status_code != 200:
            return None

        nodes_data = []
        for node in response.json().get("data", []):
            node_name = node["node"]

            # Récupérer le status détaillé du nœud
            status_response = requests.get(
                f"{PROXMOX_API_URL}/nodes/{node_name}/status",
                headers=headers,
                verify=False,
                timeout=5
            )

            if status_response.status_code == 200:
                status = status_response.json().get("data", {})

                # CPU
                cpu_usage = status.get("cpu", 0) * 100
                cpu_cores = status.get("cpuinfo", {}).get("cpus", 1)

                # RAM
                memory = status.get("memory", {})
                mem_used = memory.get("used", 0)
                mem_total = memory.get("total", 1)
                mem_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0

                # Disque (rootfs)
                rootfs = status.get("rootfs", {})
                disk_used = rootfs.get("used", 0)
                disk_total = rootfs.get("total", 1)
                disk_percent = (disk_used / disk_total * 100) if disk_total > 0 else 0

                # Uptime
                uptime = status.get("uptime", 0)

                nodes_data.append({
                    'name': node_name,
                    'status': node.get("status", "unknown"),
                    'cpu_usage': round(cpu_usage, 1),
                    'cpu_cores': cpu_cores,
                    'mem_used': mem_used,
                    'mem_total': mem_total,
                    'mem_percent': round(mem_percent, 1),
                    'disk_used': disk_used,
                    'disk_total': disk_total,
                    'disk_percent': round(disk_percent, 1),
                    'uptime': uptime,
                    'uptime_formatted': format_uptime(uptime)
                })

        return nodes_data

    except Exception as e:
        print(f"Erreur récupération status nœud: {e}")
        return None

def get_proxmox_vms():
    """Récupérer la liste des VMs depuis l'API Proxmox avec le token"""
    try:
        headers = get_headers()

        # Récupérer les nœuds
        response = requests.get(
            f"{PROXMOX_API_URL}/nodes",
            headers=headers,
            verify=False,
            timeout=5
        )

        if response.status_code != 200:
            print(f"Erreur API Proxmox (nodes): {response.status_code}")
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
                    headers=headers,
                    verify=False,
                    timeout=5
                )

                if qm_response.status_code == 200:
                    for vm in qm_response.json().get("data", []):
                        # Calculer l'utilisation CPU et RAM
                        cpu_usage = vm.get('cpu', 0) * 100
                        mem_used = vm.get('mem', 0)
                        mem_max = vm.get('maxmem', 1)
                        mem_percent = (mem_used / mem_max * 100) if mem_max > 0 else 0

                        vms.append({
                            'id': vm['vmid'],
                            'name': vm.get('name', f"VM-{vm['vmid']}"),
                            'type': 'VM',
                            'status': vm['status'],
                            'node': node_name,
                            'cpu_usage': round(cpu_usage, 1),
                            'cpu_cores': vm.get('cpus', vm.get('maxcpu', 1)),
                            'mem_used': mem_used,
                            'mem_max': mem_max,
                            'mem_percent': round(mem_percent, 1),
                            'disk_used': vm.get('disk', 0),
                            'disk_max': vm.get('maxdisk', 0),
                            'uptime': vm.get('uptime', 0),
                            'uptime_formatted': format_uptime(vm.get('uptime', 0)),
                            'netin': vm.get('netin', 0),
                            'netout': vm.get('netout', 0)
                        })
            except Exception as e:
                print(f"Erreur récupération VMs QEMU: {e}")

            # Containers LXC
            try:
                lxc_response = requests.get(
                    f"{PROXMOX_API_URL}/nodes/{node_name}/lxc",
                    headers=headers,
                    verify=False,
                    timeout=5
                )

                if lxc_response.status_code == 200:
                    for container in lxc_response.json().get("data", []):
                        # Calculer l'utilisation CPU et RAM
                        cpu_usage = container.get('cpu', 0) * 100
                        mem_used = container.get('mem', 0)
                        mem_max = container.get('maxmem', 1)
                        mem_percent = (mem_used / mem_max * 100) if mem_max > 0 else 0

                        vms.append({
                            'id': container['vmid'],
                            'name': container.get('name', container.get('hostname', f"CT-{container['vmid']}")),
                            'type': 'LXC',
                            'status': container['status'],
                            'node': node_name,
                            'cpu_usage': round(cpu_usage, 1),
                            'cpu_cores': container.get('cpus', container.get('maxcpu', 1)),
                            'mem_used': mem_used,
                            'mem_max': mem_max,
                            'mem_percent': round(mem_percent, 1),
                            'disk_used': container.get('disk', 0),
                            'disk_max': container.get('maxdisk', 0),
                            'uptime': container.get('uptime', 0),
                            'uptime_formatted': format_uptime(container.get('uptime', 0)),
                            'netin': container.get('netin', 0),
                            'netout': container.get('netout', 0)
                        })
            except Exception as e:
                print(f"Erreur récupération containers LXC: {e}")

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
        nodes = get_node_status()
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'total_vms': len(vms),
            'running': len([v for v in vms if v['status'] == 'running']),
            'stopped': len([v for v in vms if v['status'] != 'running']),
            'proxmox_host': PROXMOX_HOST,
            'nodes': nodes
        })
    except Exception as e:
        return jsonify({'error': str(e), 'total_vms': 0, 'running': 0, 'stopped': 0}), 500

@app.route('/api/nodes')
def api_nodes():
    """API: informations détaillées des nœuds"""
    try:
        nodes = get_node_status()
        return jsonify(nodes or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print(f"🚀 Supervision Proxmox démarrée sur http://0.0.0.0:5000")
    print(f"   Connecté à Proxmox: {PROXMOX_HOST}")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
