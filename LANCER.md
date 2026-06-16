# Procédure de Lancement et Déploiement de l'Application CERS

## Introduction

Ce document décrit la procédure stricte pour démarrer, mettre à jour et déployer l'application de génération de rapports du **Centre Européen de Rééducation du Sportif (CERS)** sur l'infrastructure interne.

L'application comporte deux couches :
- **Frontend PHP** (formulaire de saisie, gestion des fichiers) — servi par IIS
- **API Flask Python** (génération du rapport HTML/PDF) — processus Python en arrière-plan

---

## Environnements Disponibles

| Environnement | URL | Usage |
|---|---|---|
| **Cloud — Production Streamlit** | https://projetcers.streamlit.app/ | Accès externe, sans IIS |
| **Intranet Local — Serveur IIS** | http://10.12.16.17/rapportcers/php | Réseau interne CERS uniquement |

---

## IMPORTANT : Changement d'Adresse IP (Etape Critique)

**A lire absolument en cas de migration reseau ou de modification d'infrastructure.**

Lorsque **Sylvain** (service informatique) modifie l'infrastructure reseau ou attribue une nouvelle IP fixe au serveur :

1. Ouvrir **IIS Manager** (`inetmgr` dans Executer / Win+R)
2. Aller dans **Sites > rapportcers > Liaisons (Bindings)**
3. Modifier l'adresse IP : remplacer l'ancienne valeur par la **nouvelle IP fixe**
4. Mettre a jour `php/index.php` : chercher `10.12.16.17` et remplacer par la nouvelle IP
5. Mettre a jour ce fichier `lancer.md` avec la nouvelle IP
6. **Sylvain associera ensuite un alias reseau simplifie** (ex : `http://cers-rapports/`) pour que les praticiens n'aient pas a retenir l'adresse IP

**IP fixe actuelle : `10.12.16.17`**

---

## Prerequis Systeme

- **Python 3.11** : `C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe`
- **PHP 8.2** : `C:\php\php.exe`
- **IIS** avec le module FastCGI et le handler PHP actives
- **wkhtmltopdf** installe et dans le PATH systeme (pour la generation PDF)
- Dossier projet : `C:\Users\HP\Documents\CERS\ProjetCers\`

---

## Lancement Manuel (Developpement / Test Local)

### 1. Demarrer l'API Flask (port 5000)

```batch
cd C:\Users\HP\Documents\CERS\ProjetCers
C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe api.py
```

Verification : http://localhost:5000/ping doit retourner `{"status":"ok"}`

### 2. Demarrer le Frontend PHP (port 8080, developpement uniquement)

```batch
cd C:\Users\HP\Documents\CERS\ProjetCers\php
C:\php\php.exe -S localhost:8080
```

Acces : http://localhost:8080

### 3. Application Streamlit (optionnel)

```batch
cd C:\Users\HP\Documents\CERS\ProjetCers
streamlit run app.py
```

---

## Deploiement sur IIS (Production Intranet)

### Etape 1 — Mettre a jour le code source

```batch
cd C:\Users\HP\Documents\CERS\ProjetCers
git pull origin main
```

### Etape 2 — Installer les dependances Python

```batch
C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt --quiet
```

### Etape 3 — Configurer IIS

- **Repertoire physique** : `C:\Users\HP\Documents\CERS\ProjetCers\php`
- **Pool d'applications** : PHP 8.2 via FastCGI
- **Liaison** : IP `10.12.16.17`, Port `80`, Chemin `/rapportcers`
- Verifier que `web.config` est present dans le dossier `php\`

### Etape 4 — Lancer l'API Flask en service Windows (NSSM recommande)

```batch
nssm install CersFlaskAPI "C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe"
nssm set CersFlaskAPI AppParameters "C:\Users\HP\Documents\CERS\ProjetCers\api.py"
nssm set CersFlaskAPI AppDirectory "C:\Users\HP\Documents\CERS\ProjetCers"
nssm start CersFlaskAPI
```

> Sans NSSM : creer une tache planifiee Windows qui lance `python api.py` au demarrage du systeme.

### Etape 5 — Redemarrer IIS

```batch
iisreset /restart
```

### Etape 6 — Test de connectivite

```batch
ping 10.12.16.17
curl http://localhost:5000/ping
curl http://10.12.16.17/rapportcers/php
```

---

## Fichier web.config (IIS — PHP FastCGI)

Placer ce fichier dans `C:\Users\HP\Documents\CERS\ProjetCers\php\web.config` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="PHP_via_FastCGI"
           path="*.php"
           verb="*"
           modules="FastCgiModule"
           scriptProcessor="C:\php\php-cgi.exe"
           resourceType="Either" />
    </handlers>
    <defaultDocument>
      <files>
        <add value="index.php" />
      </files>
    </defaultDocument>
  </system.webServer>
</configuration>
```

---

## Deploiement, Tests et Commit Automatises

Executer le script `deploy_iis.bat` a la racine du projet :

```batch
deploy_iis.bat
```

Ce script effectue automatiquement :
1. `git add .` + `git commit` avec message horodate
2. Redemarrage IIS (`iisreset /restart`)
3. Test de connectivite ping sur `10.12.16.17`
4. Verification que l'API Flask repond sur `localhost:5000/ping`

---

## Depannage Rapide

| Symptome | Cause probable | Solution |
|---|---|---|
| Page blanche sur IIS | PHP non configure en FastCGI | Verifier le handler PHP dans IIS Manager |
| Erreur 500 sur `/generate` | API Flask non demarree | Lancer `python api.py` ou verifier le service NSSM |
| PDF non genere | wkhtmltopdf absent ou mauvais PATH | Verifier `wkhtmltopdf --version` dans cmd |
| 403 Forbidden sur IIS | Permissions NTFS insuffisantes | `icacls php\ /grant "IIS_IUSRS:(OI)(CI)RX"` |
| IP inaccessible depuis le reseau | IP changee sans mise a jour | Voir section "Changement d'Adresse IP" ci-dessus |
| Rapport GPS vide | Format PDF Catapult non reconnu | Verifier le dump console Flask apres upload |

---

## Contacts

- **Developpement / Application** : Lina Ouazzani
- **Infrastructure reseau / IIS** : Sylvain (service informatique CERS)
