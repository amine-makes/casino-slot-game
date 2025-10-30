import json
from app import app

def main():
    with app.test_client() as c:
        # new session
        r = c.post('/api/game/new', json={})
        assert r.status_code == 200
        session_id = r.get_json()['session_id']
        # initial balance
        r = c.get(f'/api/wallet/balance/{session_id}')
        bal0 = r.get_json()['balance']
        # deposit with idem key
        key = 'idem-abc-123'
        r1 = c.post('/api/wallet/deposit', json={'session_id': session_id, 'amount': 10.0}, headers={'Idempotency-Key': key})
        assert r1.status_code == 200
        resp1 = r1.get_json()
        # duplicate deposit
        r2 = c.post('/api/wallet/deposit', json={'session_id': session_id, 'amount': 10.0}, headers={'Idempotency-Key': key})
        assert r2.status_code == 200
        resp2 = r2.get_json()
        # ensure identical
        assert resp1 == resp2, f"Responses differ: {resp1} vs {resp2}"
        # balance should be increased only once
        r = c.get(f'/api/wallet/balance/{session_id}')
        bal1 = r.get_json()['balance']
        assert bal1 == round(bal0 + 10.0, 2), f"Balance doubled: {bal0} -> {bal1}"
        # Test spin idempotency
        key2 = 'idem-spin-001'
        r = c.post(f'/api/game/spin/{session_id}', json={'bet_amount': 1.0}, headers={'Idempotency-Key': key2})
        assert r.status_code == 200
        spin1 = r.get_json()
        r = c.post(f'/api/game/spin/{session_id}', json={'bet_amount': 1.0}, headers={'Idempotency-Key': key2})
        assert r.status_code == 200
        spin2 = r.get_json()
        assert spin1 == spin2, 'Spin responses should be identical for same idempotency key'
        print(json.dumps({
            'deposit_idempotent': True,
            'spin_idempotent': True,
            'final_balance': bal1
        }, indent=2))

if __name__ == '__main__':
    main()
