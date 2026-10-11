# Décisions techniques

## Stack retenue
- Base de données : CockroachDB (sharding, réplication, CP, transactions sérialisables)
- Langage API : Python 3.11+
- Framework API : FastAPI
- Driver DB : psycopg2 ou asyncpg
- Communication : REST
- Conteneurs : Docker + Docker Compose
- Test de charge : Locust ou script Python asyncio
- Versioning : Git + GitHub
