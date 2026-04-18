"""
Backend tests for DELETE /api/producers/{id} and DELETE /api/collectors/{id}
Verifying role-based access control (admin & factory allowed; collector & producer forbidden).
"""
import requests
import uuid
import sys

BASE_URL = "https://milk-tracker-66.preview.emergentagent.com/api"
FACTORY_CODE = "principal"
ADMIN_EMAIL = "admin@milktracker.com"
ADMIN_PASSWORD = "admin123"

results = []


def log(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    msg = f"[{status}] {name} - {detail}" if detail else f"[{status}] {name}"
    print(msg)
    results.append((name, ok, detail))


def login(email, password):
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"factory_code": FACTORY_CODE, "email": email, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        return None, r
    return r.json()["access_token"], r


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_producer(token, suffix):
    payload = {
        "name": f"Produtor Teste {suffix}",
        "nickname": f"Nick{suffix}",
        "email": f"produtor_{suffix}@teste.com",
        "password": "senha123",
        "phone": "11999999999",
        "address": "Rua Teste, 123",
    }
    r = requests.post(f"{BASE_URL}/producers", json=payload, headers=headers(token), timeout=30)
    return r, payload


def create_collector(token, suffix):
    payload = {
        "name": f"Coletor Teste {suffix}",
        "email": f"coletor_{suffix}@teste.com",
        "password": "senha123",
        "phone": "11988888888",
    }
    r = requests.post(f"{BASE_URL}/collectors", json=payload, headers=headers(token), timeout=30)
    return r, payload


def delete_producer(token, pid):
    h = headers(token) if token else {}
    return requests.delete(f"{BASE_URL}/producers/{pid}", headers=h, timeout=30)


def delete_collector(token, cid):
    h = headers(token) if token else {}
    return requests.delete(f"{BASE_URL}/collectors/{cid}", headers=h, timeout=30)


def register_factory_user(admin_token, email, password, name):
    payload = {
        "email": email,
        "password": password,
        "role": "factory",
        "name": name,
        "nickname": "Fab",
    }
    return requests.post(
        f"{BASE_URL}/auth/register", json=payload, headers=headers(admin_token), timeout=30
    )


def main():
    suffix = uuid.uuid4().hex[:8]

    # 1. Admin login
    admin_token, r = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    log("Admin login", admin_token is not None, f"status={r.status_code}")
    if not admin_token:
        sys.exit(1)

    # 2. Admin: create + delete producer & collector
    r, _ = create_producer(admin_token, f"admin_{suffix}")
    log("Admin create producer", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    if r.status_code != 200:
        sys.exit(1)
    producer_admin_id = r.json()["id"]

    r, _ = create_collector(admin_token, f"admin_{suffix}")
    log("Admin create collector", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    if r.status_code != 200:
        sys.exit(1)
    collector_admin_id = r.json()["id"]

    r = delete_producer(admin_token, producer_admin_id)
    log("Admin DELETE producer returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

    r = delete_collector(admin_token, collector_admin_id)
    log("Admin DELETE collector returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

    # 3. Create factory-role user
    factory_email = f"factory_{suffix}@teste.com"
    factory_password = "factory123"
    r = register_factory_user(admin_token, factory_email, factory_password, "Fabrica Teste")
    log("Admin creates factory-role user", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

    # 4. Factory login and deletes
    factory_token, r = login(factory_email, factory_password)
    log("Factory login", factory_token is not None, f"status={r.status_code}")

    if factory_token:
        r, _ = create_producer(factory_token, f"fact_{suffix}")
        log("Factory create producer", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
        if r.status_code == 200:
            pid = r.json()["id"]
            r = delete_producer(factory_token, pid)
            log("Factory DELETE producer returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

        r, _ = create_collector(factory_token, f"fact_{suffix}")
        log("Factory create collector", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
        if r.status_code == 200:
            cid = r.json()["id"]
            r = delete_collector(factory_token, cid)
            log("Factory DELETE collector returns 200", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

    # 5. Create producer & collector targets for forbidden tests
    r, prod_payload2 = create_producer(admin_token, f"target_{suffix}")
    log("Admin create producer (target)", r.status_code == 200, f"status={r.status_code}")
    producer_target_id = r.json()["id"] if r.status_code == 200 else None
    producer_email = prod_payload2["email"]
    producer_password = prod_payload2["password"]

    r, coll_payload2 = create_collector(admin_token, f"target_{suffix}")
    log("Admin create collector (target)", r.status_code == 200, f"status={r.status_code}")
    collector_target_id = r.json()["id"] if r.status_code == 200 else None
    collector_email = coll_payload2["email"]
    collector_password = coll_payload2["password"]

    # 6. Collector role → expect 403
    collector_token, r = login(collector_email, collector_password)
    log("Collector login", collector_token is not None, f"status={r.status_code}")

    if collector_token and producer_target_id:
        r = delete_producer(collector_token, producer_target_id)
        log("Collector DELETE producer returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")

    if collector_token and collector_target_id:
        r = delete_collector(collector_token, collector_target_id)
        log("Collector DELETE collector returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")

    # 7. Producer role → expect 403
    producer_token, r = login(producer_email, producer_password)
    log("Producer login", producer_token is not None, f"status={r.status_code}")

    if producer_token and producer_target_id:
        r = delete_producer(producer_token, producer_target_id)
        log("Producer DELETE producer returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")

    if producer_token and collector_target_id:
        r = delete_collector(producer_token, collector_target_id)
        log("Producer DELETE collector returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")

    # 8. Unauthenticated deletes → expect 403
    if producer_target_id:
        r = delete_producer(None, producer_target_id)
        log("Unauthenticated DELETE producer returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")
    if collector_target_id:
        r = delete_collector(None, collector_target_id)
        log("Unauthenticated DELETE collector returns 403", r.status_code == 403, f"status={r.status_code} body={r.text[:200]}")

    # 9. Cleanup
    if producer_target_id:
        r = delete_producer(admin_token, producer_target_id)
        log("Cleanup: admin DELETE producer target", r.status_code in (200, 404), f"status={r.status_code}")
    if collector_target_id:
        r = delete_collector(admin_token, collector_target_id)
        log("Cleanup: admin DELETE collector target", r.status_code in (200, 404), f"status={r.status_code}")

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"SUMMARY: {passed}/{total} passed")
    print("=" * 60)
    for name, ok, detail in results:
        marker = "OK " if ok else "XX "
        print(f"{marker} {name}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
