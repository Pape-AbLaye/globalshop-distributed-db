"""
Test de charge : 100 requêtes d'achat sur un même produit.
Concurrence limitée à 5 pour ne pas saturer pg8000 + CockroachDB sur un PC unique.
"""
import asyncio
import time
import uuid
import httpx

API = "http://127.0.0.1:8000"
STOCK_INITIAL = 50
NB_REQUETES = 100
CONCURRENCE_MAX = 5


async def preparer():
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{API}/clients",
            json={
                "nom": "Load Test Client",
                "email": f"load-{uuid.uuid4().hex[:8]}@example.com",
                "region": "Afrique",
            },
        )
        r.raise_for_status()
        client_id = r.json()["id"]

        r = await client.post(
            f"{API}/produits",
            json={
                "nom": f"Produit Load Test {uuid.uuid4().hex[:6]}",
                "prix": 10.0,
                "stock": STOCK_INITIAL,
                "region_stock": "Afrique",
            },
        )
        r.raise_for_status()
        produit_id = r.json()["id"]

    return client_id, produit_id


async def acheter(sem, client_id, produit_id):
    async with sem:
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                r = await client.post(
                    f"{API}/commandes",
                    json={
                        "client_id": client_id,
                        "produit_id": produit_id,
                        "quantite": 1,
                    },
                )
                return r.status_code
        except Exception as e:
            return f"ERR: {type(e).__name__}"


async def main():
    print("→ Préparation : création d'un client et d'un produit avec stock", STOCK_INITIAL)
    client_id, produit_id = await preparer()
    print(f"  client_id  = {client_id}")
    print(f"  produit_id = {produit_id}")

    print(f"\n→ Lancement de {NB_REQUETES} achats (max {CONCURRENCE_MAX} en parallèle)...")
    sem = asyncio.Semaphore(CONCURRENCE_MAX)

    start = time.perf_counter()
    codes = await asyncio.gather(
        *[acheter(sem, client_id, produit_id) for _ in range(NB_REQUETES)]
    )
    duree = time.perf_counter() - start

    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.get(f"{API}/catalogue")
        produits = r.json()
        stock_final = next((p["stock"] for p in produits if p["id"] == produit_id), None)

    succes = codes.count(201)
    refus = codes.count(409)
    timeouts = sum(1 for c in codes if c == "ERR: ReadTimeout")
    erreurs_500 = codes.count(500)
    autres = [
        c for c in codes
        if c not in (201, 409, 500) and c != "ERR: ReadTimeout"
    ]

    print()
    print("===== RÉSULTATS =====")
    print(f"Durée totale        : {duree:.2f} s")
    print(f"Requêtes envoyées   : {NB_REQUETES}")
    print(f"Commandes réussies  : {succes} (201)")
    print(f"Commandes refusées  : {refus} (409)")
    print(f"Timeouts client     : {timeouts}")
    print(f"Erreurs serveur     : {erreurs_500} (500)")
    print(f"Autres              : {autres if autres else 'aucun'}")
    print()
    print(f"Stock initial       : {STOCK_INITIAL}")
    print(f"Stock final réel    : {stock_final}")
    print(f"Diminution observée : {STOCK_INITIAL - (stock_final or 0)}")
    print()

    if stock_final is None:
        print("❌ Impossible de retrouver le produit")
    elif stock_final < 0:
        print("❌ SURVENTE DÉTECTÉE : stock négatif !")
    elif stock_final == 0:
        print("✅ TEST RÉUSSI : aucune survente, stock exactement épuisé")
    else:
        print(f"⚠️  Résultat partiel : stock={stock_final}, succes={succes}, refus={refus}")


if __name__ == "__main__":
    asyncio.run(main())