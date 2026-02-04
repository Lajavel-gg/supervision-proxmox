#!/usr/bin/env python3
"""
Supervision Proxmox - API et Dashboard
Alpine LXC compatible
Connexion à l'API Proxmox avec Token API
"""

import os
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

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

@app.route('/api/vm/<node>/<vmtype>/<int:vmid>')
def api_vm_details(node, vmtype, vmid):
    """API: details d'une VM ou container specifique"""
    try:
        headers = get_headers()
        endpoint_type = "qemu" if vmtype.upper() == "VM" else "lxc"

        # Recuperer la config
        config_response = requests.get(
            f"{PROXMOX_API_URL}/nodes/{node}/{endpoint_type}/{vmid}/config",
            headers=headers,
            verify=False,
            timeout=5
        )

        # Recuperer le status actuel
        status_response = requests.get(
            f"{PROXMOX_API_URL}/nodes/{node}/{endpoint_type}/{vmid}/status/current",
            headers=headers,
            verify=False,
            timeout=5
        )

        if config_response.status_code != 200 or status_response.status_code != 200:
            return jsonify({'error': 'VM non trouvee'}), 404

        config = config_response.json().get("data", {})
        status = status_response.json().get("data", {})

        # Construire les details
        details = {
            'id': vmid,
            'node': node,
            'type': vmtype.upper(),
            'name': config.get('name', status.get('name', f'{vmtype}-{vmid}')),
            'status': status.get('status', 'unknown'),

            # CPU
            'cpu_usage': round(status.get('cpu', 0) * 100, 1),
            'cpu_cores': config.get('cores', status.get('cpus', 1)),
            'cpu_sockets': config.get('sockets', 1),

            # Memoire
            'mem_used': status.get('mem', 0),
            'mem_max': status.get('maxmem', config.get('memory', 0) * 1024 * 1024),
            'mem_percent': round((status.get('mem', 0) / max(status.get('maxmem', 1), 1)) * 100, 1),

            # Disque
            'disk_used': status.get('disk', 0),
            'disk_max': status.get('maxdisk', 0),

            # Reseau
            'netin': status.get('netin', 0),
            'netout': status.get('netout', 0),

            # Uptime
            'uptime': status.get('uptime', 0),
            'uptime_formatted': format_uptime(status.get('uptime', 0)),

            # Config supplementaire
            'description': config.get('description', ''),
            'ostype': config.get('ostype', 'unknown'),
            'boot_order': config.get('boot', ''),
        }

        # Infos specifiques VM QEMU
        if vmtype.upper() == "VM":
            details['bios'] = config.get('bios', 'seabios')
            details['machine'] = config.get('machine', '')
            details['scsihw'] = config.get('scsihw', '')

        # Infos specifiques LXC
        else:
            details['hostname'] = config.get('hostname', '')
            details['arch'] = config.get('arch', 'amd64')
            details['swap'] = config.get('swap', 0)

        # Recuperer les interfaces reseau
        networks = []
        for key, value in config.items():
            if key.startswith('net'):
                networks.append({'interface': key, 'config': value})
        details['networks'] = networks

        # Recuperer les disques
        disks = []
        for key, value in config.items():
            if any(key.startswith(prefix) for prefix in ['scsi', 'sata', 'ide', 'virtio', 'rootfs', 'mp']):
                if isinstance(value, str) and ':' in value:
                    disks.append({'device': key, 'config': value})
        details['disks'] = disks

        return jsonify(details)

    except Exception as e:
        print(f"Erreur recuperation details VM: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes/<node>/rrddata')
def api_node_rrddata(node):
    """API: historique RRD d'un noeud (CPU, RAM, etc sur 24h)"""
    try:
        headers = get_headers()
        timeframe = request.args.get('timeframe', 'day')  # hour, day, week, month, year

        response = requests.get(
            f"{PROXMOX_API_URL}/nodes/{node}/rrddata",
            headers=headers,
            params={'timeframe': timeframe},
            verify=False,
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({'error': 'Impossible de recuperer les donnees RRD'}), 500

        data = response.json().get('data', [])

        # Formater les donnees pour les graphiques
        formatted = []
        for point in data:
            if point.get('time'):
                formatted.append({
                    'time': point.get('time'),
                    'cpu': round(point.get('cpu', 0) * 100, 1) if point.get('cpu') else 0,
                    'mem_used': point.get('memused', 0),
                    'mem_total': point.get('memtotal', 0),
                    'mem_percent': round((point.get('memused', 0) / max(point.get('memtotal', 1), 1)) * 100, 1) if point.get('memused') else 0,
                    'netin': point.get('netin', 0),
                    'netout': point.get('netout', 0),
                    'diskread': point.get('diskread', 0),
                    'diskwrite': point.get('diskwrite', 0)
                })

        return jsonify(formatted)

    except Exception as e:
        print(f"Erreur RRD node: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vm/<node>/<vmtype>/<int:vmid>/rrddata')
def api_vm_rrddata(node, vmtype, vmid):
    """API: historique RRD d'une VM/LXC (CPU, RAM, etc sur 24h)"""
    try:
        headers = get_headers()
        endpoint_type = "qemu" if vmtype.upper() == "VM" else "lxc"
        timeframe = request.args.get('timeframe', 'day')

        response = requests.get(
            f"{PROXMOX_API_URL}/nodes/{node}/{endpoint_type}/{vmid}/rrddata",
            headers=headers,
            params={'timeframe': timeframe},
            verify=False,
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({'error': 'Impossible de recuperer les donnees RRD'}), 500

        data = response.json().get('data', [])

        # Formater les donnees pour les graphiques
        formatted = []
        for point in data:
            if point.get('time'):
                formatted.append({
                    'time': point.get('time'),
                    'cpu': round(point.get('cpu', 0) * 100, 1) if point.get('cpu') else 0,
                    'mem_used': point.get('mem', 0),
                    'mem_max': point.get('maxmem', 0),
                    'mem_percent': round((point.get('mem', 0) / max(point.get('maxmem', 1), 1)) * 100, 1) if point.get('mem') else 0,
                    'netin': point.get('netin', 0),
                    'netout': point.get('netout', 0),
                    'diskread': point.get('diskread', 0),
                    'diskwrite': point.get('diskwrite', 0)
                })

        return jsonify(formatted)

    except Exception as e:
        print(f"Erreur RRD VM: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks')
def api_tasks():
    """API: liste des taches/actions recentes du cluster"""
    try:
        headers = get_headers()
        limit = request.args.get('limit', 50, type=int)

        # Recuperer les taches du cluster
        response = requests.get(
            f"{PROXMOX_API_URL}/cluster/tasks",
            headers=headers,
            verify=False,
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({'error': 'Impossible de recuperer les taches'}), 500

        tasks = response.json().get('data', [])

        # Trier par date (plus recent en premier) et limiter
        tasks.sort(key=lambda x: x.get('starttime', 0), reverse=True)
        tasks = tasks[:limit]

        # Formater les taches
        formatted = []
        for task in tasks:
            # Determiner le status
            status = 'running'
            if task.get('endtime'):
                status = 'success' if task.get('status') == 'OK' else 'error'

            # Formatter le type de tache
            task_type = task.get('type', 'unknown')
            description = task_type

            # Descriptions plus lisibles
            type_descriptions = {
                'qmstart': 'Demarrage VM',
                'qmstop': 'Arret VM',
                'qmreboot': 'Redemarrage VM',
                'qmshutdown': 'Extinction VM',
                'qmcreate': 'Creation VM',
                'qmdestroy': 'Suppression VM',
                'qmmigrate': 'Migration VM',
                'qmclone': 'Clone VM',
                'vzstart': 'Demarrage LXC',
                'vzstop': 'Arret LXC',
                'vzreboot': 'Redemarrage LXC',
                'vzshutdown': 'Extinction LXC',
                'vzcreate': 'Creation LXC',
                'vzdestroy': 'Suppression LXC',
                'vzmigrate': 'Migration LXC',
                'vzdump': 'Backup',
                'qmrestore': 'Restauration VM',
                'vzrestore': 'Restauration LXC',
                'aptupdate': 'Mise a jour APT',
                'startall': 'Demarrage global',
                'stopall': 'Arret global'
            }
            description = type_descriptions.get(task_type, task_type)

            formatted.append({
                'id': task.get('upid', ''),
                'type': task_type,
                'description': description,
                'status': status,
                'node': task.get('node', ''),
                'user': task.get('user', ''),
                'vmid': task.get('id', ''),
                'starttime': task.get('starttime', 0),
                'endtime': task.get('endtime', 0),
                'duration': (task.get('endtime', 0) - task.get('starttime', 0)) if task.get('endtime') else 0,
                'error': task.get('status', '') if task.get('status') != 'OK' else ''
            })

        return jsonify(formatted)

    except Exception as e:
        print(f"Erreur tasks: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"🚀 Supervision Proxmox démarrée sur http://0.0.0.0:5000")
    print(f"   Connecté à Proxmox: {PROXMOX_HOST}")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
