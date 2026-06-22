# Notes de Version - Application Hydro-Québec

## Version 3.2.1 (Décembre 2025)

### Mise à jour Mineure: Standardisation User-Agent

Cette version apporte une correction mineure pour standardiser le User-Agent utilisé dans tous les collectors.

#### Changements

**User-Agent Standardisé:**
- ✅ Tous les collectors utilisent maintenant: `Splunk-HydroQuebec-Collector/3.x`
- ✅ Cohérence entre les 3 scripts de collecte (pannes, interruptions, demande)
- ✅ Format simplifié et conforme aux politiques OpenStreetMap/Nominatim
- ✅ Corrections des anciennes valeurs (1.0, 3.2.0, AdminTek)

**Fichiers Modifiés:**
- `bin/hydroquebec_collector.py` - 2 occurrences mises à jour
- `bin/hydroquebec_collector_interruptions.py` - 2 occurrences mises à jour
- `bin/hydroquebec_collector_demande.py` - 1 occurrence mise à jour

#### Impact

**✅ Rétrocompatible:**
- Aucun impact fonctionnel
- Aucune modification de configuration requise
- Aucun redémarrage nécessaire (si déjà en v3.2.0)
- Simple mise à jour cosmétique du User-Agent HTTP header

**Conformité:**
- Meilleure conformité avec les politiques d'utilisation de l'API Nominatim
- Identification cohérente de l'application auprès d'OpenStreetMap

---

## Version 3.2.0 (Décembre 2025)

### Nouvelle Fonctionnalité: Demande d'Électricité

Cette version ajoute la collecte et la visualisation de la demande d'électricité en temps réel au Québec.

#### Nouvelles Fonctionnalités

**1. Collecte de la Demande d'Électricité**
- ✅ Nouveau collector: `hydroquebec_collector_demande.py`
- ✅ Collecte automatique toutes les 15 minutes
- ✅ Détection des nouvelles mesures (évite les duplicatas)
- ✅ Gestion d'état: `demande_state.pkl`

**2. Nouveau Dashboard**
- ✅ Dashboard "Demande d'Électricité" complet
- ✅ Indicateurs clés (actuelle, max, min, moyenne)
- ✅ Graphiques d'évolution temporelle
- ✅ Analyse par heure de la journée
- ✅ Historique détaillé

**3. Nouveau Sourcetype**
- ✅ `hydroquebec:demande` - Mesures de demande électrique
- ✅ Structure JSON simple (demande_mw, date_mesure)

#### Documentation Ajoutée

- `API_DEMANDE_DOCUMENTATION.md` - Documentation complète de l'API
- `DEMANDE_FEATURE_SUMMARY.md` - Résumé de la fonctionnalité
- Mise à jour de `README.md` avec la nouvelle fonctionnalité

#### Impact et Compatibilité

**✅ Rétrocompatible:**
- Aucun impact sur les collectors existants
- Aucune modification des dashboards existants
- Utilise le même index `hydroquebec`
- Nouveau sourcetype indépendant

---

## Version 3.1.0 (Décembre 2025)

### Optimisation Majeure: Suivi de Version BIS/AIP

Cette version introduit une fonctionnalité majeure d'optimisation qui réduit significativement la charge sur Splunk.

#### Nouvelles Fonctionnalités

**1. Système de Suivi de Version**
- ✅ Les scripts vérifient maintenant si la version BIS/AIP a changé avant de collecter les données
- ✅ Collecte uniquement lorsque les données d'Hydro-Québec sont mises à jour
- ✅ Fichiers de suivi: `bis_version.txt` et `aip_version.txt` dans `/local/`
- ✅ Classe `VersionTracker` pour gérer le suivi entre les exécutions

**2. Logs Améliorés**
- Message clair quand la version est inchangée: "Version inchangée, aucune collecte nécessaire"
- Détection des nouvelles versions: "Nouvelle version détectée: {ancienne} -> {nouvelle}"
- Compteur précis du nombre d'événements envoyés à Splunk

**3. Compatibilité Améliorée**
- Ajout du fallback `backports.zoneinfo` dans le script des interruptions
- Cohérence entre les deux scripts de collecte
- Support pour Python 3.7+ (y compris anciennes versions sans zoneinfo)

#### Améliorations de Performance

**Réduction de la Charge:**
- ~50-70% de réduction du volume de données indexées
- Économie estimée de 300-500 MB de stockage par an
- Moins d'appels au service de géocodage Nominatim
- Utilisation plus efficace du cache

**Comportement Intelligent:**
- Skip automatique quand la version est identique
- Collecte complète quand les données changent
- Adaptation automatique lors d'événements majeurs (tempêtes)

#### Impact et Compatibilité

**✅ Rétrocompatible:**
- Aucune modification requise des dashboards
- Aucune modification requise des alertes
- Les inputs continuent à s'exécuter toutes les 15 minutes
- Fonctionne avec toutes les configurations existantes

**Transparence:**
- Les utilisateurs ne voient aucune différence dans les dashboards
- Les alertes continuent de fonctionner normalement
- Les données sont identiques, simplement collectées plus intelligemment

#### Documentation

- **Nouveau:** `VERSION_TRACKING.md` - Documentation complète du système de suivi
- Mise à jour de `API_DOCUMENTATION.md` avec le nouveau flux
- Exemples de logs et de monitoring

#### Maintenance

**Nouveau Monitoring:**
```bash
# Vérifier les versions actuelles
cat $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/bis_version.txt
cat $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/aip_version.txt
```

**Forcer une Collecte:**
```bash
# Supprimer les fichiers de version si nécessaire
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/*_version.txt
```

#### Statistiques Estimées

**Avant (v3.0):**
- Collectes par jour: 96 (toutes les 15 min)
- Événements moyens par jour: ~1,920
- Stockage annuel: ~1.4 GB

**Après (v3.1):**
- Collectes effectives: ~30-50 par jour (quand version change)
- Événements moyens par jour: ~600-1,000
- Stockage annuel: ~0.5-0.9 GB
- **Économie: ~50-70%**

---

## Version 3.0.0 (Novembre 2025)

### Refonte Majeure

Version 3.0.0 représente une refonte complète avec plusieurs améliorations majeures.

#### Changements Majeurs
- Migration vers l'API v3_0 d'Hydro-Québec
- Ajout du champ `bis_id` et `bis_timestamp` pour les pannes
- Ajout du champ `aip_id` et `aip_timestamp` pour les interruptions
- Amélioration de la structure des données JSON

---

## Version 1.0.0 (Novembre 2025)

### Première Version Publique

Cette version initiale de l'application Hydro-Québec pour Splunk offre une surveillance complète des pannes électriques et interruptions planifiées au Québec.

### Fonctionnalités Principales

#### Collecte de Données
- ✅ Collecte automatique des pannes en cours (toutes les 15 minutes)
- ✅ Collecte automatique des interruptions planifiées (toutes les 15 minutes)
- ✅ Géolocalisation automatique des adresses via API OpenStreetMap
- ✅ Cache intelligent pour minimiser les requêtes API
- ✅ Détection des changements et mise à jour de l'historique
- ✅ Respect de la limite de 1 requête/seconde pour l'API Nominatim

#### Dashboards

**Dashboard Pannes en Cours:**
- Carte géographique interactive du Québec
- 4 indicateurs clés (pannes actives, clients affectés, nouvelles pannes, durée moyenne)
- Filtres par région et municipalité
- Graphiques de répartition par cause et statut
- Évolution temporelle sur 24 heures
- Top 10 des municipalités affectées
- Tableau détaillé avec toutes les informations

**Dashboard Interruptions Planifiées:**
- Carte géographique des interruptions à venir
- 4 indicateurs clés (interruptions à venir, clients affectés, prochaines 24h, en cours)
- Calendrier sur 14 jours
- Graphiques d'analyse par jour
- Top 10 des municipalités
- Tableaux détaillés avec priorisation 24-48h

**Dashboard Alertes:**
- Vue d'ensemble de la configuration des alertes
- Documentation intégrée
- Historique des nouvelles pannes (24h)
- Pannes importantes en cours
- Interruptions prochaines (24h)
- Statistiques et tendances sur 7 jours

#### Système d'Alertes

**3 Alertes Préconfigurées:**

1. **Nouvelle panne détectée**
   - Fréquence: Toutes les 5 minutes
   - Condition: Panne détectée dans les 10 dernières minutes
   - Informations: Municipalité, adresse, clients affectés, cause, statut

2. **Panne importante - Plus de 100 clients**
   - Fréquence: Toutes les 5 minutes
   - Condition: Plus de 100 clients sans électricité (seuil configurable)
   - Informations: Détails complets triés par nombre de clients

3. **Interruption planifiée prochainement**
   - Fréquence: Quotidienne à 8h00
   - Condition: Interruption planifiée dans les 24 prochaines heures
   - Informations: Horaires, municipalité, adresse, clients affectés

#### Données Collectées

**Champs des Pannes:**
- ID unique de la panne
- Nombre de clients affectés
- Dates de début et fin estimée
- Coordonnées géographiques (latitude/longitude)
- Statut (Travail assigné, Équipe au travail, Équipe en route)
- Cause (avec description en français)
- Localisation complète (municipalité, région, adresse, code postal)
- Historique des changements

**Champs des Interruptions:**
- ID unique de l'interruption
- Numéro d'avis
- Nombre de clients affectés
- Dates prévues, réelles, reportées et reprogrammées
- Coordonnées géographiques
- Statut et cause
- Localisation complète
- Historique des modifications

#### Optimisations

- **Cache de géocodage:** Évite les requêtes répétées pour les mêmes coordonnées
- **Détection des changements:** Envoie uniquement les nouvelles pannes ou mises à jour
- **Respect des limites API:** Pause de 1.1 seconde entre requêtes Nominatim
- **Arrondi des coordonnées:** Améliore l'efficacité du cache (4 décimales)
- **Gestion d'état:** Suivi des pannes et interruptions actives

### Configuration

#### Index
- **Nom:** hydroquebec
- **Taille max:** 5 Go
- **Rétention:** 1 an

#### Sourcetypes
- `hydroquebec:pannes` - Format JSON avec extraction automatique
- `hydroquebec:interruption_planifie` - Format JSON avec extraction automatique

#### Permissions
- Lecture: Tous les utilisateurs
- Écriture: Administrateurs et Power Users

### Langues

- ✅ Interface complète en français
- ✅ Noms de champs en français
- ✅ Descriptions des causes en français
- ✅ Documentation en français
- ✅ Commentaires de code en français

### Prérequis Techniques

- Splunk Enterprise 8.0 ou supérieur
- Python 3.7 ou supérieur (inclus avec Splunk)
- Module Python `requests`
- Connexion internet pour accès aux APIs

### Installation

Voir le fichier `INSTALLATION.md` pour les instructions détaillées.

### Limitations Connues

1. **Géocodage:**
   - Limite de 1 requête/seconde vers l'API Nominatim
   - Les nouvelles adresses peuvent prendre du temps à être géocodées si beaucoup de pannes
   - Cache partagé entre pannes et interruptions

2. **Données:**
   - Dépend de la disponibilité de l'API Hydro-Québec
   - Les coordonnées fournies par Hydro-Québec sont approximatives
   - Certaines adresses peuvent être incomplètes selon la qualité du géocodage

3. **Performance:**
   - La première exécution peut prendre plusieurs minutes (géocodage)
   - Les exécutions suivantes sont beaucoup plus rapides (cache)

### Problèmes Connus

- Aucun problème majeur identifié dans cette version

### Améliorations Futures (Roadmap)

**Version 1.1 (Prévue):**
- Ajout de notifications Webex Teams
- Export automatique en PDF des rapports
- Dashboard de statistiques historiques (mensuel/annuel)
- Intégration avec d'autres sources de données météo

**Version 1.2 (Prévue):**
- Prédiction des pannes basée sur l'historique
- API RESTful pour intégration externe
- Application mobile companion
- Alertes géographiques personnalisées

### Remerciements

- Hydro-Québec pour leur API de données ouvertes
- OpenStreetMap et Nominatim pour le géocodage
- La communauté Splunk

### Support et Contributions

Pour signaler des bugs ou suggérer des améliorations:
1. Utiliser le système de feedback Splunk
2. Contacter: alexandre@argeris.net

---

**Auteur:** alexandre@argeris.net  
**Date de Release:** Novembre 2025  
**Licence:** Apache License 2.0
