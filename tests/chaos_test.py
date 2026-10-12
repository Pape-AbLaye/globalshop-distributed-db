"""
Chaos Engineering : coupe un nœud CockroachDB pendant une écriture.
Vérifie que le cluster survit (failover) et reste cohérent.
"""
import asyncio
import uuid
import httpx

API = "http://localhost:8000"
STOCK_INITIAL = 30
NB_ACHATS = 20


async def preparer():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{API}/clients",
            json={
                "nom": "Chaos Client",
                "email": f"chaos-{uuid.uuid4().hex[:8]}@example.com",
                "region": "Afrique",
            },
        )
        r.raise_for_status()
        client_id = r.json()["id"]

        r = await client.post(
            f"{API}/produits",
            json={
                "nom": f"Chaos Produit {uuid.uuid4().hex[:6]}",
                "prix": 10.0,
                "stock": STOCK_INITIAL,
                "region_stock": "Afrique",
            },
        )
        r.raise_for_status()
        produit_id = r.json()["id"]

    return client_id, produit_id


async def acheter(client_id, produit_id):
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                f"{API}/commandes",
                json={"client_id": client_id, "produit_id": produit_id, "quantite": 1},
            )
            return r.status_code
    except Exception as e:
        return f"ERR: {type(e).__name__}"


async def main():
    print("→ Préparation : création d'un client et d'un produit avec stock", STOCK_INITIAL)
    client_id, produit_id = await preparer()
    print(f"  produit_id = {produit_id}\n")

    print("👉  AU 3e ACHAT (index 3), coupe `roach3` dans un AUTRE terminal avec :")
    print("    docker stop roach3\n")

    codes = []
    for i in range(NB_ACHATS):
        code = await acheter(client_id, produit_id)
        codes.append(code)
        print(f"  [{i + 1:02d}/{NB_ACHATS}] code = {code}")
        await asyncio.sleep(0.5)

    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.get(f"{API}/catalogue")
        stock_final = next(
            (p["stock"] for p in r.json() if p["id"] == produit_id), None
        )

    succes = codes.count(201)
    refus = codes.count(409)
    erreurs = [c for c in codes if c not in (201, 409)]

    print()
    print("===== RÉSULTATS =====")
    print(f"Succès   : {succes} (201)")
    print(f"Refus    : {refus} (409)")
    print(f"Erreurs  : {erreurs if erreurs else 'aucune'}")
    print(f"Stock final : {stock_final} (initial = {STOCK_INITIAL})")
    print()

    if stock_final is None:
        print("❌ Produit introuvable")
    elif stock_final < 0:
        print("❌ SURVENTE / INCOHÉRENCE")
    elif stock_final == STOCK_INITIAL - succes:
        print("✅ COHÉRENCE PRÉSERVÉE malgré la panne")
    else:
        print(f"⚠️  Incohérence : stock={stock_final}, succes={succes}")


if __name__ == "__main__":
    asyncio.run(main())