# Base de Connaissance : Intégration SAUR HomeAssistant

Ce document synthétise l'analyse du projet `saur-homeassistant`, une intégration personnalisée pour Home Assistant.

## 1. Objectif du Projet

L'objectif de cette intégration est de récupérer les données de consommation d'eau depuis le service en ligne de la SAUR et de les afficher sous forme d'un capteur (`sensor`) dans Home Assistant.

L'intégration fonctionne en mode `cloud_polling`, ce qui signifie qu'elle interroge périodiquement une API cloud pour obtenir les données.

## 2. Structure des Fichiers Clés

- **`manifest.json`**: Fichier de déclaration standard pour une intégration Home Assistant.
  - **`domain`**: `saur_homeassistant` (l'identifiant unique de l'intégration).
  - **`name`**: "SAUR HomeAssistant" (le nom affiché à l'utilisateur).
  - **`config_flow`**: `true`, indique que la configuration se fait via l'interface utilisateur de Home Assistant.
  - **`iot_class`**: `cloud_polling`, confirme que l'intégration récupère des données depuis un service cloud.
  - **`codeowners`**: `@LouisForaux`.
  - **`requirements`**: `[]`, l'intégration n'a pas de dépendances Python externes.

- **`const.py`**: Stocke les constantes du projet.
  - **`DOMAIN`**: `saur_homeassistant`.
  - **`AUTH_URL`**: `https://apib2c.azure.saurclient.fr/admin/auth` (l'endpoint pour l'authentification).
  - **`CONSUMPTION_URL`**: `https://apib2c.azure.saurclient.fr/deli/section_subscription/{}/consumptions/weekly?year={}&month={}&day={}` (l'endpoint pour récupérer la consommation hebdomadaire).

- **`config_flow.py`**: Gère le processus de configuration via l'interface utilisateur.
  - Demande à l'utilisateur son **email** et son **mot de passe**.
  - Crée une entrée de configuration (`ConfigEntry`) avec les identifiants fournis.
  - **Point important**: Le code contient un `TODO` indiquant que la validation des identifiants n'est pas encore implémentée. L'intégration sauvegarde la configuration sans vérifier si l'email et le mot de passe sont corrects.

- **`sensor.py`**: Définit l'entité capteur qui sera visible dans Home Assistant.
  - Crée un `WaterConsumptionSensor`.
  - Utilise un `CoordinatorEntity` pour recevoir les données du coordinateur de mise à jour.
  - **Unité de mesure**: Mètres cubes (`UnitOfVolume.CUBIC_METERS`).
  - **Classe d'appareil**: `SensorDeviceClass.WATER`.
  - **Classe d'état**: `SensorStateClass.TOTAL_INCREASING`, ce qui suggère que la valeur est un compteur cumulatif.

- **`__init__.py`**: (Contenu inféré à partir des autres fichiers) Gère la mise en place de l'intégration.
  - Contient probablement la fonction `async_setup_entry` qui initialise un `DataUpdateCoordinator`.
  - Le coordinateur est responsable de :
    1. S'authentifier auprès de l'API SAUR.
    2. Appeler périodiquement l'endpoint de consommation.
    3. Stocker les données récupérées pour que le capteur puisse les utiliser.

## 3. Fonctionnement Détaillé

1.  **Installation & Configuration** :
    - L'utilisateur ajoute l'intégration à Home Assistant.
    - Via l'interface, il fournit son email et son mot de passe SAUR.
    - Le `config_flow` sauvegarde ces informations dans une `ConfigEntry` sans les valider.

2.  **Initialisation** :
    - La fonction `async_setup_entry` dans `__init__.py` est appelée.
    - Elle crée une instance du `DataUpdateCoordinator`. Ce coordinateur est chargé de gérer les appels API en arrière-plan.

3.  **Collecte des Données (Polling)** :
    - Le `DataUpdateCoordinator` exécute sa tâche de mise à jour à intervalle régulier.
    - Il utilise l'email et le mot de passe pour s'authentifier sur `AUTH_URL`.
    - Une fois authentifié (et après avoir probablement récupéré un token et un identifiant de contrat), il appelle `CONSUMPTION_URL` pour obtenir les dernières données de consommation.
    - Les données récupérées (valeur, date de début, date de fin) sont stockées dans `coordinator.data`.

4.  **Mise à jour du Capteur** :
    - Le `WaterConsumptionSensor`, étant un `CoordinatorEntity`, est automatiquement notifié par le coordinateur lorsque de nouvelles données sont disponibles.
    - La valeur du capteur (`native_value`) est mise à jour avec la consommation en m³.
    - Les attributs supplémentaires (`extra_state_attributes`) sont mis à jour avec les dates de la période de consommation.

## 4. Points d'Amélioration et TODOs Identifiés

- **Validation des identifiants** : Le point le plus critique est l'absence de validation des identifiants dans le `config_flow.py`. Une authentification échouée devrait retourner une erreur à l'utilisateur.
- **Gestion des erreurs** : Le code ne semble pas avoir de gestion robuste des erreurs (ex: API SAUR indisponible, identifiants incorrects après la configuration initiale, pas de nouvelles données).
- **Documentation** : Le `README.md` est vide. Il devrait contenir des instructions d'installation et de configuration.
- **Configuration du Contrat** : L'URL de consommation (`CONSUMPTION_URL`) nécessite un identifiant de souscription (`section_subscription/{}`). Le code doit gérer la récupération de cet identifiant après l'authentification, surtout si un utilisateur a plusieurs contrats.
