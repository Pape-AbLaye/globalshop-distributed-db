from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from app.db import get_connection

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

# ---------- Endpoints ----------

@app.get("/")
def root():
    return {"message": "GlobalShop API opérationnelle"}

@app.post("/clients", status_code=201)
def creer_client(client: ClientIn):
    try:
        conn = get_connection()
        rows = conn.run(
            "INSERT INTO clients (nom, email, region) VALUES (:nom, :email, :region) RETURNING id",
            nom=client.nom,
            email=client.email,
            region=client.region,
        )
        client_id = rows[0][0]
        conn.close()
        return {"id": str(client_id), "nom": client.nom, "email": client.email, "region": client.region}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/produits", status_code=201)
def creer_produit(produit: ProduitIn):
    try:
        conn = get_connection()
        rows = conn.run(
            "INSERT INTO produits (nom, prix, stock, region_stock) VALUES (:nom, :prix, :stock, :region_stock) RETURNING id",
            nom=produit.nom,
            prix=produit.prix,
            stock=produit.stock,
            region_stock=produit.region_stock,
        )
        produit_id = rows[0][0]
        conn.close()
        return {"id": str(produit_id), **produit.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))