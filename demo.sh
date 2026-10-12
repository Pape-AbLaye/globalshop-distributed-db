#!/usr/bin/env bash
# =========================================================
# GlobalShop — Démonstration automatisée
# =========================================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_step() { echo -e "\n${YELLOW}==> $1${NC}"; }
echo_ok()   { echo -e "${GREEN}✅ $1${NC}"; }
echo_err()  { echo -e "${RED}❌ $1${NC}"; }

# ---------------------------------------------------------
# 1) Vérifier Docker
# ---------------------------------------------------------
echo_step "Vérification de Docker"
if ! docker info > /dev/null 2>&1; then
  echo_err "Docker Desktop n'est pas démarré. Lance-le puis relance ce script."
  exit 1
fi
echo_ok "Docker est opérationnel"

# ---------------------------------------------------------
# 2) Démarrer le cluster CockroachDB
# ---------------------------------------------------------
echo_step "Démarrage du cluster CockroachDB (4 nœuds)"
docker compose up -d
echo "  Attente de 20 secondes pour que les nœuds se synchronisent..."
sleep 20

# Initialiser le cluster seulement si nécessaire
echo "  Vérification de l'état d'initialisation..."
if docker exec roach1 ./cockroach node status --insecure > /dev/null 2>&1; then
  echo_ok "Le cluster est déjà initialisé"
else
  echo "  Initialisation du cluster..."
  docker exec -it roach1 ./cockroach init --insecure || true
  sleep 5
fi

echo_ok "Cluster démarré"
docker exec -it roach1 ./cockroach node status --insecure

# ---------------------------------------------------------
# 3) Charger le schéma + données initiales (idempotent)
# ---------------------------------------------------------
echo_step "Chargement du schéma et des données initiales"
MSYS_NO_PATHCONV=1 docker cp db/init.sql roach1:/tmp/init.sql > /dev/null
MSYS_NO_PATHCONV=1 docker exec -i roach1 ./cockroach sql --insecure --file=/tmp/init.sql 2>&1 | tail -5 || true
echo_ok "Base initialisée (tables créées si absentes)"

# ---------------------------------------------------------
# 4) Lancer l'API FastAPI en arrière-plan
# ---------------------------------------------------------
echo_step "Lancement de l'API FastAPI"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || true
fi

uvicorn app.main:app --port 8000 > /tmp/uvicorn_demo.log 2>&1 &
UVICORN_PID=$!
echo "  PID uvicorn = $UVICORN_PID"
echo "  Attente du démarrage (10 s)..."
sleep 10

# Vérifier que l'API répond
for i in 1 2 3 4 5; do
  if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    break
  fi
  echo "  Attente supplémentaire..."
  sleep 3
done

if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
  echo_err "L'API ne répond pas. Voir /tmp/uvicorn_demo.log"
  kill $UVICORN_PID 2>/dev/null || true
  exit 1
fi
echo_ok "API opérationnelle (http://localhost:8000/docs)"

# ---------------------------------------------------------
# 5) Démonstration : client → produit → commande
# ---------------------------------------------------------
echo_step "Démonstration : inscription d'un client"
CLIENT_JSON=$(curl -s -X POST http://localhost:8000/clients \
  -H "Content-Type: application/json" \
  -d "{\"nom\":\"Demo Client\",\"email\":\"demo-$(date +%s)@example.com\",\"region\":\"Afrique\"}")
echo "$CLIENT_JSON"
CLIENT_ID=$(echo "$CLIENT_JSON" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
echo_ok "Client créé : $CLIENT_ID"

echo_step "Création d'un produit (stock = 3)"
PRODUIT_JSON=$(curl -s -X POST http://localhost:8000/produits \
  -H "Content-Type: application/json" \
  -d "{\"nom\":\"Produit Demo\",\"prix\":25.00,\"stock\":3,\"region_stock\":\"Afrique\"}")
echo "$PRODUIT_JSON"
PRODUIT_ID=$(echo "$PRODUIT_JSON" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)
echo_ok "Produit créé : $PRODUIT_ID"

echo_step "Passage d'une commande (quantité = 2)"
COMMANDE_JSON=$(curl -s -X POST http://localhost:8000/commandes \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"$CLIENT_ID\",\"produit_id\":\"$PRODUIT_ID\",\"quantite\":2}")
echo "$COMMANDE_JSON"
echo_ok "Commande passée"

echo_step "Tentative de survente (quantité = 5, stock restant = 1)"
SURVENTE_RESPONSE=$(curl -s -X POST http://localhost:8000/commandes \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"$CLIENT_ID\",\"produit_id\":\"$PRODUIT_ID\",\"quantite\":5}")
echo "$SURVENTE_RESPONSE"

if echo "$SURVENTE_RESPONSE" | grep -q "Stock insuffisant"; then
  echo_ok "Survente correctement refusée (anti-overselling fonctionne)"
else
  echo_err "ATTENTION : la survente n'a pas été refusée"
fi

# ---------------------------------------------------------
# 6) Vérification finale côté base
# ---------------------------------------------------------
echo_step "Vérification côté CockroachDB"
docker exec -it roach1 ./cockroach sql --insecure \
  -e "USE globalshop; SELECT nom, stock FROM produits WHERE id='$PRODUIT_ID';"

# ---------------------------------------------------------
# 7) Résumé
# ---------------------------------------------------------
echo
echo -e "${GREEN}=========================================================${NC}"
echo -e "${GREEN}   DÉMONSTRATION TERMINÉE AVEC SUCCÈS${NC}"
echo -e "${GREEN}=========================================================${NC}"
echo
echo "  Interface web CockroachDB : http://localhost:8080"
echo "  Documentation API FastAPI : http://localhost:8000/docs"
echo
echo "  Pour arrêter :"
echo "    - Ctrl+C dans ce terminal pour stopper l'API"
echo "    - docker compose down pour arrêter le cluster"
echo

# Garde l'API en vie jusqu'à Ctrl+C
wait $UVICORN_PID