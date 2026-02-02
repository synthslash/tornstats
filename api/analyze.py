from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error
import time

class handler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            # CORS headers
            self.send_header('Access-Control-Allow-Origin', '*')
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            faction_id = data.get('faction_id', '').strip()
            api_key = data.get('api_key', '').strip()
            
            if not faction_id or not api_key:
                self.send_json_response({'error': 'Missing faction_id or api_key'}, 400)
                return
            
            # Fetch data
            result = self.fetch_faction_data(faction_id, api_key)
            self.send_json_response(result, 200)
            
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def fetch_faction_data(self, faction_id, api_key):
        # Fetch members
        members_url = f"https://api.torn.com/v2/faction/{faction_id}/members?key={api_key}"
        members_data = self.fetch_url(members_url)
        
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
                stats_data = self.fetch_url(stats_url)
                
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
    
    def fetch_url(self, url):
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'TornStats/1.0')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))