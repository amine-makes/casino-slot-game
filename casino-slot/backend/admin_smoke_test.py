import os
import json

# Ensure admin token is set before importing app
os.environ['ADMIN_TOKEN'] = os.environ.get('ADMIN_TOKEN', 'test_admin_token')

from app import app  # noqa: E402

def main():
    token = os.environ['ADMIN_TOKEN']
    out = {}
    with app.test_client() as c:
        # Create a session and send an event to ensure data exists
        r = c.post('/api/game/new', json={})
        assert r.status_code == 200, f"new_game failed: {r.status_code} {r.data}"
        session_id = r.get_json()['session_id']
        r = c.post('/api/analytics/event', json={
            'session_id': session_id,
            'name': 'admin_test_event',
            'props': {'foo': 'bar'}
        })
        assert r.status_code == 200, f"event failed: {r.status_code} {r.data}"
        out['event'] = r.get_json()

        # Summary
        r = c.get('/api/analytics/summary', headers={'X-Admin-Token': token})
        assert r.status_code == 200, f"summary failed: {r.status_code} {r.data}"
        out['summary'] = r.get_json()

        # Events list
        r = c.get('/api/analytics/events?limit=5', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200, f"events failed: {r.status_code} {r.data}"
        out['events'] = r.get_json()

    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
