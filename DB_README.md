# 🗄️ Gestion des bases de données – AI Regulatory Chatbot

Ce document décrit la **stratégie de gestion et d’indexation des données** du projet **TeknoAI**, un chatbot d’analyse réglementaire intelligent.  
Le système s’appuie sur une **base vectorielle Pinecone** pour la recherche sémantique des textes juridiques, et sur une **base relationnelle optionnelle** pour le suivi des documents, logs et métadonnées.

---
## 📑 Sommaire

1. [Introduction](#1-introduction)
2. [Bases vectorielles — Pinecone 🌲](#2-bases-vectorielles--pinecone-)
3. [Bases relationnelles (optionnelles)](#3-bases-relationnelles-optionnelles)
4. [Organisation documentaire](#4-organisation-documentaire)
5. [Variables d’environnement](#5-variables-denvironnement)
6. [Pipeline d’ingestion](#6-pipeline-dingestion)
7. [Bonnes pratiques](#7-bonnes-pratiques)
8. [Évolutions prévues](#8-évolutions-prévues)

---

## 1. Introduction

TeknoAI vise à **rendre accessibles et interrogeables les corpus juridiques belges et européens** :  
codes régionaux, décrets, publications officielles, et règlements européens.

Les documents sources (PDF) sont :
1. Nettoyés et convertis en texte,  
2. Découpés en passages ("chunks"),  
3. Transformés en vecteurs d’embedding,  
4. Stockés et indexés dans Pinecone pour la recherche sémantique.

Le projet repose sur deux types de bases de données complémentaires :  

- **Base vectorielle** → utilisée pour la recherche sémantique (retrieval) dans les textes réglementaires.  
- **Base relationnelle** → utilisée pour stocker les utilisateurs, historiques de requêtes et métadonnées. (optionnelle)

Ces deux briques constituent le socle technique du pipeline RAG (*Retrieval-Augmented Generation*).

---

## 2. Bases vectorielles — Pinecone 🌲

### 🎯 Objectif
Stocker les **embeddings vectoriels** issus des passages réglementaires afin de permettre une **recherche contextuelle** et non basée sur des mots-clés exacts.

### 🪵 Choix technologique
- **Pinecone (SaaS)** : base de données vectorielle managée et serverless.  
- **Modèle d’embedding** : `text-embedding-3-small` (OpenAI).  

#### ✅ Avantages
- Aucun serveur à gérer ni maintenance.
- Scalabilité automatique (petit à très grand volume).
- Recherche sémantique rapide et filtrée (par namespace).
- Intégration native avec Python et OpenAI.

---

### 🧩 Structure d’un enregistrement vectoriel

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | Identifiant unique du passage |
| `values` | Array[float] | Vecteur numérique (embedding) |
| `metadata` | JSON | Contexte : source, page, type, texte, etc. |
| `namespace` | String | Contexte thématique (ex. `wallonie_eau`, `ue_dechets`) |

**Exemple JSON :**
```json
{
  "id": "uuid-123",
  "values": [0.123, -0.052, ...],
  "metadata": {
    "source": "Code_de_l_Eau_coordonne.pdf",
    "page": 42,
    "jurisdiction": "wallonie",
    "topic": "eau",
    "text": "Art. D.1er — L’eau fait partie du patrimoine commun..."
  },
  "namespace": "wallonie_eau"
}  

🗂️ Organisation par namespace

Chaque corpus est indexé sous un namespace distinct pour garder une structure claire :

Namespace	Description
wallonie_eau	Code de l’Eau coordonné (Région wallonne)
wallonie_env	Code de l’Environnement (parties décrétale et réglementaire)
subsoil	Décret sur la gestion des ressources du sous-sol
moniteur_belge	Publications fédérales
ue_directives	Législation européenne (extension future)

---

## 3. Bases relationnelles (optionnelles)

### Objectif
Stocker les métadonnées structurées (titres, types, juridictions),
ainsi que les logs d’ingestion et l’historique des indexations.
- Suivi des utilisateurs.  
- Historique des requêtes.  
- Logs de performance.  

### Choix
- **Supabase** (PostgreSQL managé)  
  - Avantages : plan gratuit, API prête à l’emploi, intégration facile avec Python/Streamlit.  
  - Inconvénients : dépendance à une plateforme externe.  

- **PostgreSQL auto-hébergé** (si besoin d’indépendance).  

🗃️ Exemple de schéma SQL simplifié:
documents
  id (PK)
  title
  jurisdiction
  topic
  namespace
  local_path
  status
  created_at

chunks
  id (PK)
  document_id (FK)
  text
  page
  pinecone_id
  created_at

ingestion_logs
  id (PK)
  document_id (FK)
  date
  status
  message


### Stratégie
- Pour le POC → Supabase (gratuit et simple).  
- Pour une montée en charge → PostgreSQL hébergé chez un cloud provider.  

---

## 4. Organisation documentaire
 
 📁 Arborescence des données
 teknoai/
├── data/
│   ├── raw/               # PDF sources officiels (non versionnés)
│   ├── txt/               # Textes extraits (.txt)
│
├── processed/
│   ├── chunks/            # Fragments découpés
│   ├── embeddings/        # Vecteurs temporaires
│   └── uploads/           # Logs d’indexation
│
├── corpus/
│   └── documents.yaml     # Métadonnées (titre, juridiction, chemin)
│
└── pinecone/
    ├── create_index.py
    ├── ingest_yaml.py
    ├── search_test.py
    └── rag_answer.py


📄 Exemple d’entrée corpus/documents.yaml

- id: wallonie-eau-code
  title: "Code de l’Eau coordonné"
  jurisdiction: "wallonie"
  topic: "eau"
  file: "data/raw/Code_de_l_Eau_coordonne.pdf"
  namespace: "wallonie_eau"
  source_url: "https://environnement.wallonie.be/"

 stockage documentaire:
- **Repo GitHub** → contient uniquement des **extraits légers** (< 10 Mo) pour les tests.  
- **Drive/OneDrive/S3** → héberge les documents lourds (codes consolidés, rapports complets).  
- **`docs/_metadata/sources.json`** → centralise les informations (titre, niveau juridique, thématique, lien Drive ou chemin local).  


🚫 Politique de stockage

Les PDF lourds sont exclus de Git (data/raw/ dans .gitignore).

Seuls les fichiers YAML, scripts et logs légers sont versionnés.

Un stockage externe (Drive, S3, ou SharePoint) peut héberger les PDF complets.



🔐 5. Variables d’environnement

Les clés et configurations sont centralisées dans .env
(non versionné, mais un .env.example est fourni).


🔍 6. Pipeline d’ingestion
Étape	Script	Résultat
1️⃣ Extraction du texte	utils/pdf_extractor.py	.txt généré dans data/txt/
2️⃣ Découpage en chunks	utils/chunking.py	Fichiers JSON dans processed/chunks/
3️⃣ Embedding + upsert	pinecone/ingest_yaml.py	Indexation dans Pinecone
4️⃣ Recherche sémantique	pinecone/search_test.py	Résultats classés par similarité
5️⃣ RAG complet	pinecone/rag_answer.py	Réponse contextuelle + citation source


🧠 7. Bonnes pratiques

✅ À faire :

Utiliser des noms de fichiers sans accents ni espaces.

Respecter les namespaces cohérents (wallonie_eau, wallonie_env, etc.).

Commit régulier des YAML, scripts et configs.

Sauvegarder les logs d’upload (processed/uploads/).

🚫 À éviter :

Versionner les PDF ou embeddings volumineux.

Modifier directement les fichiers processed/.

Insérer des clés API dans le code source.

🚀 8. Évolutions prévues

 Interface Streamlit pour interroger Pinecone.

 Dashboard de suivi d’ingestion et de requêtes.

 Export CSV / JSON des résultats.

 Intégration optionnelle d’une base SQL.

 Indexation de nouveaux corpus (UE, Bruxelles, Fédéral).