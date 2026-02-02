from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error
import time

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            faction_id = data.get('faction_id')
            api_key = data.get('api_key')
            
            if not faction_id or not api_key:
                self.send_error_response('Missing faction_id or api_key', 400)
                return
            
            # Fetch faction data
            result = self.fetch_faction_data(faction_id, api_key)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_error_response(str(e), 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def fetch_faction_data(self, faction_id, api_key):
        # Fetch faction members
        members_url = f"https://api.torn.com/v2/faction/{faction_id}/members?key={api_key}"
        members_data = self.fetch_json(members_url)
        
        if 'error' in members_data:
            raise Exception(f"Torn API Error: {members_data['error'].get('error', 'Unknown error')}")
        
        # Extract member IDs
members_raw = members_data.get('members', {})
member_list = []

# Check if members is a dict or list
if isinstance(members_raw, dict):
    # v2 API returns dict: {"123": {...}, "456": {...}}
    for member_id, member_info in members_raw.items():
        member_list.append({
            'id': int(member_id),
            'name': member_info.get('name', 'Unknown'),
            'level': member_info.get('level', 0)
        })
elif isinstance(members_raw, list):
    # Some APIs return list: [{"id": 123, ...}, {"id": 456, ...}]
    for member_info in members_raw:
        member_list.append({
            'id': int(member_info.get('id', 0)),
            'name': member_info.get('name', 'Unknown'),
            'level': member_info.get('level', 0)
        })
        
        # Fetch stats for each member
        stats_keys = ['attackswon', 'defendswon', 'useractivity', 'xantaken', 'attackslost', 'defendslost']
        
        for member in member_list:
            try:
                # Fetch current stats (v1 API with stat parameter)
                stats_url = f"https://api.torn.com/user/{member['id']}?selections=personalstats&stat={','.join(stats_keys)}&key={api_key}"
                stats_data = self.fetch_json(stats_url)
                
                if 'error' not in stats_data:
                    personal_stats = stats_data.get('personalstats', {})
                    member['attackswon'] = personal_stats.get('attackswon', 0)
                    member['defendswon'] = personal_stats.get('defendswon', 0)
                    member['useractivity'] = personal_stats.get('useractivity', 0)
                    member['xantaken'] = personal_stats.get('xantaken', 0)
                    member['attackslost'] = personal_stats.get('attackslost', 0)
                    member['defendslost'] = personal_stats.get('defendslost', 0)
                else:
                    # If error, set defaults
                    member['attackswon'] = 0
                    member['defendswon'] = 0
                    member['useractivity'] = 0
                    member['xantaken'] = 0
                    member['attackslost'] = 0
                    member['defendslost'] = 0
                
                # Rate limiting (700ms between requests)
                time.sleep(0.7)
                
            except Exception as e:
                print(f"Error fetching stats for {member['name']}: {e}")
                member['attackswon'] = 0
                member['defendswon'] = 0
                member['useractivity'] = 0
                member['xantaken'] = 0
                member['attackslost'] = 0
                member['defendslost'] = 0
        
        return {
            'faction_id': faction_id,
            'members': member_list
        }
    
    def fetch_json(self, url):
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'TornStatsApp/1.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                return json.loads(error_body)
            except:
                raise Exception(f"HTTP Error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def send_error_response(self, message, status=500):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())