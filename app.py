from flask import Flask, request, jsonify, send_from_directory
import json
import urllib.request
import urllib.error
import time

app = Flask(__name__, static_folder='.')

# Serve index.html at root
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Serve static files (CSS, JS, etc.)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# API endpoint
@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    
    try:
        data = request.get_json()
        faction_id = data.get('faction_id', '').strip()
        api_key = data.get('api_key', '').strip()
        
        if not faction_id or not api_key:
            return jsonify({'error': 'Missing faction_id or api_key'}), 400
        
        # Fetch faction data
        result = fetch_faction_data(faction_id, api_key)
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_faction_data(faction_id, api_key):
    # Fetch members
    members_url = f"https://api.torn.com/v2/faction/{faction_id}/members?key={api_key}"
    members_data = fetch_url(members_url)
    
    if 'error' in members_data:
        raise Exception(f"Torn API Error: {members_data['error'].get('error', 'Unknown')}")
    
    # Parse members
    members_raw = members_data.get('members', {})
    member_list = []
    
    if isinstance(members_raw, dict):
        for member_id, info in members_raw.items():
            member_list.append({
                'id': int(member_id),
                'name': info.get('name', 'Unknown'),
                'level': info.get('level', 0)
            })
    elif isinstance(members_raw, list):
        for info in members_raw:
            member_list.append({
                'id': int(info.get('id', 0)),
                'name': info.get('name', 'Unknown'),
                'level': info.get('level', 0)
            })
    
    # Fetch stats for each member
    stats_keys = ['attackswon', 'defendswon', 'useractivity', 'xantaken']
    
    for member in member_list:
        try:
            stats_url = f"https://api.torn.com/user/{member['id']}?selections=personalstats&stat={','.join(stats_keys)}&key={api_key}"
            stats_data = fetch_url(stats_url)
            
            if 'personalstats' in stats_data:
                ps = stats_data['personalstats']
                member['attackswon'] = ps.get('attackswon', 0)
                member['defendswon'] = ps.get('defendswon', 0)
                member['useractivity'] = ps.get('useractivity', 0)
                member['xantaken'] = ps.get('xantaken', 0)
            else:
                member['attackswon'] = 0
                member['defendswon'] = 0
                member['useractivity'] = 0
                member['xantaken'] = 0
            
            time.sleep(0.7)  # Rate limit
            
        except:
            member['attackswon'] = 0
            member['defendswon'] = 0
            member['useractivity'] = 0
            member['xantaken'] = 0
    
    return {
        'faction_id': faction_id,
        'members': member_list
    }

def fetch_url(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'TornStats/1.0')
    
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)