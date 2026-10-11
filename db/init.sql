

CREATE DATABASE IF NOT EXISTS globalshop;
USE globalshop;

CREATE TABLE IF NOT EXISTS clients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom         STRING NOT NULL,
    email       STRING NOT NULL UNIQUE,
    region      STRING NOT NULL,
    created_at  TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS produits (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom           STRING NOT NULL,
    prix          DECIMAL(10,2) NOT NULL,
    stock         INT NOT NULL DEFAULT 0,
    region_stock  STRING NOT NULL,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commandes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL REFERENCES clients(id),
    produit_id  UUID NOT NULL REFERENCES produits(id),
    quantite    INT NOT NULL CHECK (quantite > 0),
    statut      STRING NOT NULL DEFAULT 'en_cours',
    date        TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS factures (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commande_id  UUID NOT NULL REFERENCES commandes(id),
    montant      DECIMAL(10,2) NOT NULL,
    date         TIMESTAMP DEFAULT now()
);

-- Données de test

INSERT INTO clients (nom, email, region) VALUES
    ('Ali Diop',      'ali@example.com',   'Afrique'),
    ('Marie Dupont',  'marie@example.com', 'Europe'),
    ('John Smith',    'john@example.com',  'Amérique'),
    ('Yuki Tanaka',   'yuki@example.com',  'Asie');

INSERT INTO produits (nom, prix, stock, region_stock) VALUES
    ('Casque Bluetooth',  49.99, 100, 'Afrique'),
    ('Clavier mécanique', 89.90,  50, 'Europe'),
    ('Souris sans fil',   19.99, 200, 'Amérique'),
    ('Écran 27 pouces',  199.00,  30, 'Asie');