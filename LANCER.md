# CERS Capbreton — Guide de lancement

## Architecture

```
ProjetCers/
├── app.py              ← Interface Streamlit (inchangée)
├── api.py              ← API Flask (nouveau — port 5000)
├── php/
│   └── index.php       ← Front PHP (nouveau — port 8080 local / port 80 IIS)
├── uploads/            ← Fichiers temporaires (créé automatiquement)
├── outputs/            ← Rapports générés (créé automatiquement)
└── requirements.txt    ← Dépendances Python
```

## Prérequis

```bash
pip install -r requirements.txt
```

---

## TEST LOCAL

### Terminal 1 — Lancer l'API Flask
```bash
python api.py
```
→ L'API écoute sur **http://localhost:5000**

### Terminal 2 — Lancer le front PHP
```bash
cd php
php -S localhost:8080
```
→ Ouvrir **http://localhost:8080** dans le navigateur

### (Optionnel) Terminal 3 — Lancer Streamlit séparément
```bash
streamlit run app.py
```
→ Ouvre sur **http://localhost:8501**  
L'application Streamlit est indépendante du front PHP et de l'API Flask.

---

## TEST DE L'API

### Ping (vérification santé)
```bash
curl http://localhost:5000/ping
```
Réponse attendue :
```json
{"message":"CERS API opérationnelle","status":"ok"}
```

### Recherche de clubs
```bash
curl "http://localhost:5000/clubs/search?q=Toulouse"
```

### Liste des blessures
```bash
curl http://localhost:5000/blessures
```

### Test génération rapport (sans fichiers)
```bash
curl -X POST http://localhost:5000/generate \
  -F "sport=Rugby" \
  -F "nom_club=Test"
```
Réponse attendue :
```json
{"html_b64":"...","pdf_b64":"...","success":true}
```

---

## DÉPLOIEMENT IIS (Windows Server)

### 1. Installer les dépendances Python
```powershell
pip install -r requirements.txt
```

### 2. Lancer l'API Flask en arrière-plan (service Windows)
Option A — tâche planifiée Windows :
```powershell
schtasks /create /tn "CERS-API" /tr "python C:\inetpub\wwwroot\ProjetCers\api.py" /sc onstart /ru SYSTEM
schtasks /run /tn "CERS-API"
```

Option B — NSSM (service Windows recommandé) :
```powershell
nssm install CERS-API "python" "C:\inetpub\wwwroot\ProjetCers\api.py"
nssm start CERS-API
```

### 3. Configurer IIS pour le front PHP
1. Installer PHP via Web Platform Installer ou manuellement
2. Configurer PHP FastCGI dans IIS
3. Créer un site IIS pointant sur `C:\inetpub\wwwroot\ProjetCers\php\`
4. S'assurer que `index.php` est dans les documents par défaut
5. Vérifier que `php.ini` a `extension=fileinfo` activée

### 4. Vérifications IIS
```powershell
# Vérifier que PHP répond
curl http://localhost/index.php

# Vérifier que l'API répond (depuis le serveur)
curl http://localhost:5000/ping
```

### 5. Ajuster l'URL de l'API dans php/index.php
Si l'API tourne sur un autre hôte ou port :
```php
// Ligne 3 de php/index.php
$API_URL = "http://localhost:5000";  // ← modifier si besoin
```

---

## RÉSOLUTION DES PROBLÈMES COURANTS

### ❌ "API non joignable" (barre rouge en haut de l'interface)
**Cause :** L'API Flask n'est pas démarrée.  
**Solution :**
```bash
python api.py
```
Vérifier qu'aucun autre processus n'occupe le port 5000 :
```bash
# Windows
netstat -ano | findstr :5000
```

### ❌ Erreur SQLite "unable to open database file"
**Cause :** IIS n'a pas les droits d'écriture dans le dossier du projet.  
**Solution automatique :** `_get_db_path()` dans `database.py` essaie automatiquement :
1. Dossier du projet
2. `C:/ProgramData/CERS/`
3. Dossier home de l'utilisateur
4. Dossier temp système

Si aucun chemin ne fonctionne, vérifier les permissions NTFS :
```powershell
icacls "C:\inetpub\wwwroot\ProjetCers" /grant "IIS_IUSRS:(OI)(CI)F"
```

### ❌ "wkhtmltopdf non trouvé" (PDF non généré, HTML généré à la place)
**Cause :** wkhtmltopdf n'est pas installé sur Windows.  
**Solution :**
1. Télécharger depuis : https://wkhtmltopdf.org/downloads.html  
   → Choisir **"Windows (MSVC 2015) 64-bit"**
2. Installer dans `C:\Program Files\wkhtmltopdf\`
3. Vérifier : `wkhtmltopdf --version`

### ❌ CORS bloqué (front PHP ne peut pas contacter l'API)
**Cause :** Flask-CORS non installé ou CORS désactivé.  
**Solution :**
```bash
pip install flask-cors
```
L'API configure `CORS(app)` (toutes origines) dans `api.py`.

### ❌ Timeout sur la génération (rapports longs)
**Cause :** La génération du PDF avec graphiques peut durer 30–60 secondes.  
**Solution :** Augmenter les timeouts dans IIS et PHP :
```ini
; php.ini
max_execution_time = 120
max_input_time = 120
upload_max_filesize = 20M
post_max_size = 25M
```

---

## RÉSUMÉ DES PORTS

| Service           | Port local | Port IIS |
|-------------------|-----------|----------|
| API Flask         | 5000      | 5000     |
| Front PHP         | 8080      | 80       |
| Streamlit (optionnel) | 8501 | —    |
