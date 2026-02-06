# My Social Network API

API REST pour un réseau social développé avec FastAPI et MangoDB.


## Fonctionnalités

- Gestion des utilisateurs avec email unique
- Création et gestion d'événements en 3 étapes
- Création de groupes public, privé ou secret
- Fils de discussion liés aux groupes ou aux événements
- Albums photos avec commentaires
- Sondages
- Billetterie
- Liste de courses


## Installation

1. Cloner le repository
```bash
git clone https://github.com/emiliehhd/GenerativeIA_project.git
```

2. Créer un environnement virtuel et l'activer
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```
ou sous windows
```bash
venv\Scripts\activate     # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement dans `.env`

5. Démarrer MongoDB

6. Lancer l'API : `uvicorn app.main:app --reload`


## Sécurité

### Authentification et Autorisation

#### JWT (JSON Web Tokens)

Un système d'authentification par tokens JWT a été implémenté. Les utlisateurs doivent s'authentifier avec leur email et mot de passe pour obtenir un token. Le token doit être précisé dans l'en-tête des requêtes pour accéder aux fonctionnalités protégées. Pour modifier les évènements et gérer les groupes, l'autorisation est seulement fournies à l'administrateur.

#### Mots de passe

Les mots de passe des utilisateurs sont hachés avec bcrypt. Cela permet de ne pas stocker les mots de passe en clair et se protéger des attaques.

#### Valisation des entrées

Les données reçues par l'API sont validées avec Pydantic, afin d'éviter les injections et les données mal formatées. 
Cela passe par la validation du format des emails, le contrôle de longueur min et max des champs texte



### Améliorations Possibles

Pour la Production, il est envisageable de mettre en place :
 - un HTTPS avec certificats SSL
 - un rate limiting pour prévenir les attaques 
 - des logs
