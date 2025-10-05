# 🗄️ Gestion des bases de données – AI Regulatory Chatbot

Ce document décrit la stratégie de gestion des bases de données pour le projet **AI Regulatory Chatbot**.  
Les bases de données sont essentielles pour :  
- stocker et interroger efficacement les informations réglementaires,  
- assurer la cohérence des réponses générées par l’IA,  
- gérer les utilisateurs, historiques et logs.

---

## 1. Introduction

Le projet repose sur deux types de bases de données complémentaires :  

- **Base vectorielle** → utilisée pour la recherche sémantique (retrieval) dans les textes réglementaires.  
- **Base relationnelle** → utilisée pour stocker les utilisateurs, historiques de requêtes et métadonnées.  

Ces deux briques constituent le socle technique du pipeline RAG (*Retrieval-Augmented Generation*).

---

## 2. Bases vectorielles

### Objectif
Stocker les embeddings générés à partir des documents (PDF réglementaires) afin de retrouver rapidement les passages pertinents lors d’une question utilisateur.

### Choix possibles
- **🌲 Pinecone**  
  - SaaS (cloud, clé en main).  
  - Avantages : simplicité, scalabilité automatique, pas de maintenance.  
  - Inconvénients : payant (~50$/mois minimum).  

- **🔶 Qdrant**  
  - Open-source, self-host via Docker.  
  - Avantages : gratuit, flexible, contrôle total des données.  
  - Inconvénients : nécessite de gérer l’hébergement, les sauvegardes et les mises à jour.  

### Stratégie
- **POC rapide** → Pinecone (mise en place en quelques minutes).  
- **Prod économique** → Qdrant auto-hébergé (Docker, serveur dédié ou cloud).  

---

## 3. Bases relationnelles (optionnelles mais recommandées)

### Objectif
- Suivi des utilisateurs.  
- Historique des requêtes.  
- Logs de performance.  

### Choix
- **Supabase** (PostgreSQL managé)  
  - Avantages : plan gratuit, API prête à l’emploi, intégration facile avec Python/Streamlit.  
  - Inconvénients : dépendance à une plateforme externe.  

- **PostgreSQL auto-hébergé** (si besoin d’indépendance).  

### Stratégie
- Pour le POC → Supabase (gratuit et simple).  
- Pour une montée en charge → PostgreSQL hébergé chez un cloud provider.  

---

## 4. Stockage documentaire

- **Repo GitHub** → contient uniquement des **extraits légers** (< 10 Mo) pour les tests.  
- **Drive/OneDrive/S3** → héberge les documents lourds (codes consolidés, rapports complets).  
- **`docs/_metadata/sources.json`** → centralise les informations (titre, niveau juridique, thématique, lien Drive ou chemin local).  

Exemple d’entrée `sources.json` :  
```json
{
  "id": "EU-2021-1119",
  "titre": "Règlement (UE) 2021/1119 – European Climate Law",
  "niveau": "eu",
  "juridiction": "UE",
  "thematique": "emissions_climat",
  "annee": 2021,
  "lang": "fr",
  "source_url": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32021R1119",
  "storage": "drive",
  "drive_url": "https://drive.google.com/file/d/XXXX/view?usp=sharing",
  "local_excerpt": "docs/eu/emissions_climat/EU__emissions_climat__climate-law__2021__fr_excerpt.pdf",
  "notes": "Extrait conservé localement pour tests ; document complet sur Drive."
}
