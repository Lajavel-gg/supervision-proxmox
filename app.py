#!/usr/bin/env python3
"""
Supervision Proxmox - API et Dashboard
Alpine LXC compatible
"""

import os
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template, jsonify

app = Flask(__name__)

def run_cmd(cmd):
    """Exécuter une commande shell"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        print(f"Erreur: {e}")
        return None

def get_vms():
    """Récupérer la liste des VMs/containers"""
    vms = []
    
    # VMs QEMU
    qm_output = run_cmd("qm list | tail -n +2")
    if qm_output:
        for line in qm_output.split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3:
                vms.append({
                    'id': parts[0],
                    'name': parts[1],
                    'type': 'VM',
                    'status': parts[2],
                    'uptime': parts[3] if len(parts) > 3 else 'N/A'
                })
    
    # Containers LXC
    pct_output = run_cmd("pct list | tail -n +2")
    if pct_output:
        for line in pct_output.split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3:
                vms.append({
                    'id': parts[0],
                    'name': parts[1],
                    'type': 'LXC',
                    'status': parts[2],
                    'uptime': parts[3] if len(parts) > 3 else 'N/A'
                })
    
    return vms

def get_cluster_status():
    """Status du cluster"""
    try:
        vms = get_vms()
        return {
            'timestamp': datetime.now().isoformat(),
            'total_vms': len(vms),
            'running': len([v for v in vms if v['status'] == 'running']),
            'stopped': len([v for v in vms if v['status'] != 'running'])
        }
    except Exception as e:
        return {'error': str(e), 'total_vms': 0, 'running': 0, 'stopped': 0}

@app.route('/')
def dashboard():
    """Dashboard principal"""
    return render_template('index.html')

@app.route('/api/vms')
def api_vms():
    """API: liste des VMs"""
    return jsonify(get_vms())

@app.route('/api/status')
def api_status():
    """API: status général"""
    return jsonify(get_cluster_status())

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Supervision Proxmox démarrée sur http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
