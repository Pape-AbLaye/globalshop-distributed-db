from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from app.db import get_connection, release_connection

# Augmente le pool de threads d'anyio (défaut = 40 → 200)
try:
    import anyio.to_thread
    anyio.to_thread.current_default_thread_limiter().total_tokens = 200
except Exception:
    pass

app = FastAPI(title="GlobalShop API", version="0.1.0")


# ---------- Modèles Pydantic ----------

class ClientIn(BaseModel):
    nom: str
    email: EmailStr
    region: str


class ProduitIn(BaseModel):
    nom: str
    prix: float
    stock: int
    region_stock: str


class CommandeIn(BaseModel):
    client_id: str
    produit_id: str
    quantite: int


# ---------- Endpoints ----------

@app.get("/")
def root():
    return {"message": "GlobalShop API opérationnelle"}


@app.post("/clients", status_code=201)
def creer_client(client: ClientIn):
    conn = get_connection()
    try:
        rows = conn.run(
            "INSERT INTO clients (nom, email, region) VALUES (:nom, :email, :region) RETURNING id",
            nom=client.nom,
            email=client.email,
            region=client.region,
        )
        client_id = rows[0][0]
        return {
            "id": str(client_id),
            "nom": client.nom,
            "email": client.email,
            "region": client.region,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn)


@app.post("/produits", status_code=201)
def creer_produit(produit: ProduitIn):
    conn = get_connection()
    try:
        rows = conn.run(
            "INSERT INTO produits (nom, prix, stock, region_stock) "
            "VALUES (:nom, :prix, :stock, :region_stock) RETURNING id",
            nom=produit.nom,
            prix=produit.prix,
            stock=produit.stock,
            region_stock=produit.region_stock,
        )
        produit_id = rows[0][0]
        return {"id": str(produit_id), **produit.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn)


@app.get("/catalogue")
def catalogue():
    conn = get_connection()
    try:
        rows = conn.run(
            "SELECT id, nom, prix, stock, region_stock FROM produits ORDER BY nom"
        )
        return [
            {
                "id": str(r[0]),
                "nom": r[1],
                "prix": float(r[2]),
                "stock": r[3],
                "region_stock": r[4],
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn)


@app.post("/commandes", status_code=201)
def passer_commande(commande: CommandeIn):
    if commande.quantite <= 0:
        raise HTTPException(status_code=400, detail="La quantité doit être > 0")

    conn = get_connection()
    valid = True
    try:
        conn.run("BEGIN")

        updated = conn.run(
            "UPDATE produits SET stock = stock - :q "
            "WHERE id = :pid AND stock >= :q "
            "RETURNING id, prix, stock",
            q=commande.quantite,
            pid=commande.produit_id,
        )

        if not updated:
            conn.run("ROLLBACK")
            raise HTTPException(
                status_code=409, detail="Stock insuffisant — vente refusée"
            )

        prix_unitaire = updated[0][1]
        montant = float(prix_unitaire) * commande.quantite

        cmd_rows = conn.run(
            "INSERT INTO commandes (client_id, produit_id, quantite, statut) "
            "VALUES (:cid, :pid, :q, 'confirmee') RETURNING id",
            cid=commande.client_id,
            pid=commande.produit_id,
            q=commande.quantite,
        )
        commande_id = cmd_rows[0][0]

        fac_rows = conn.run(
            "INSERT INTO factures (commande_id, montant) VALUES (:cid, :m) RETURNING id",
            cid=commande_id,
            m=montant,
        )
        facture_id = fac_rows[0][0]

        conn.run("COMMIT")

        return {
            "commande_id": str(commande_id),
            "facture_id": str(facture_id),
            "produit_id": commande.produit_id,
            "quantite": commande.quantite,
            "montant": montant,
            "statut": "confirmee",
        }

    except HTTPException:
        try:
            conn.run("ROLLBACK")
        except Exception:
            valid = False
        raise
    except Exception as e:
        valid = False
        try:
            conn.run("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn, valid=valid)