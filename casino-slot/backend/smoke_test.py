import json
from app import app

def main():
    out = {}
    with app.test_client() as c:
        # new game
        r = c.post('/api/game/new', json={})
        assert r.status_code == 200, f"new_game failed: {r.status_code} {r.data}"
        new_game = r.get_json()
        session_id = new_game['session_id']
        out['session_id'] = session_id

        # deposit
        r = c.post('/api/wallet/deposit', json={
            'session_id': session_id,
            'amount': 50.0,
            'method': 'test'
        })
        assert r.status_code == 200, f"deposit failed: {r.status_code} {r.data}"
        out['deposit'] = r.get_json()

        # balance
        r = c.get(f'/api/wallet/balance/{session_id}')
        assert r.status_code == 200, f"balance failed: {r.status_code} {r.data}"
        out['balance'] = r.get_json()

        # spin
        r = c.post(f'/api/game/spin/{session_id}', json={'bet_amount': 1.5})
        assert r.status_code == 200, f"spin failed: {r.status_code} {r.data}"
        spin_res = r.get_json()
        out['spin_total_win'] = spin_res.get('total_win')
        out['spin_wallet_balance'] = spin_res.get('wallet_balance')
        out['spin_house_pool'] = spin_res.get('house_pool')

        # transactions
        r = c.get(f'/api/wallet/transactions/{session_id}')
        assert r.status_code == 200, f"transactions failed: {r.status_code} {r.data}"
        txs = r.get_json()['transactions']
        out['tx_count'] = len(txs)
        out['last_tx'] = txs[-1] if txs else None

        # bankroll
        r = c.get('/api/bankroll')
        assert r.status_code == 200, f"bankroll failed: {r.status_code} {r.data}"
        out['bankroll'] = r.get_json()

        # analytics event
        r = c.post('/api/analytics/event', json={
            'session_id': session_id,
            'name': 'test_event',
            'props': {'k': 'v'}
        })
        assert r.status_code == 200, f"analytics failed: {r.status_code} {r.data}"
        out['analytics'] = r.get_json()

    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
