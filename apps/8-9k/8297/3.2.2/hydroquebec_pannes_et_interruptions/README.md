# Application Hydro-Québec - Pannes et Interruptions

## Description

Application Splunk pour la surveillance en temps réel des pannes électriques, interruptions planifiées et demande d'électricité d'Hydro-Québec.

## Fonctionnalités

### Collecte de Données
- **Pannes en cours**: Collecte automatique toutes les 15 minutes depuis l'API d'Hydro-Québec
- **Interruptions planifiées**: Collecte automatique toutes les 15 minutes
- **Demande d'électricité**: Collecte automatique toutes les 15 minutes de la consommation électrique en temps réel
- **Géolocalisation**: Récupération automatique des adresses via OpenStreetMap (avec cache)
- **Historique**: Conservation de tous les changements d'état

### Dashboards

#### 1. Pannes en Cours
- Carte géographique interactive du Québec
- Statistiques en temps réel (pannes actives, clients affectés)
- Graphiques d'évolution temporelle
- Analyse par cause et statut
- Tableau détaillé avec toutes les informations

#### 2. Interruptions Planifiées
- Carte des interruptions à venir
- Calendrier des interruptions prévues
- Alertes pour les prochaines 24-48 heures
- Statistiques par municipalité

#### 3. Demande d'Électricité
- Indicateurs clés (demande actuelle, maximum, minimum, moyenne)
- Graphique d'évolution temporelle
- Analyse par heure de la journée
- Variations min/max/moyenne
- Tableau historique détaillé

#### 4. Alertes et Notifications
- Configuration des alertes
- Historique des événements importants
- Statistiques et tendances

### Alertes Configurées

1. **Nouvelle panne détectée** (toutes les 5 minutes)
   - Déclenchée pour chaque nouvelle panne
   - Fournit les détails de la municipalité et du nombre de clients

2. **Panne importante** (toutes les 5 minutes)
   - Déclenchée quand plus de 100 clients sont affectés
   - Seuil configurable

3. **Interruption planifiée prochainement** (quotidienne à 8h00)
   - Liste les interruptions des prochaines 24 heures

## Installation

### Prérequis
- Splunk Enterprise 8.0 ou supérieur
- Python 3.7 ou supérieur
- Module Python `requests`

### Installation du module requests
```bash
$SPLUNK_HOME/bin/splunk cmd python3 -m pip install requests --break-system-packages
```

### Installation de l'application

#### Méthode 1: Interface Web (Recommandée)

1. Connectez-vous à Splunk Web
2. Allez dans **Apps** > **Manage Apps**
3. Cliquez sur **Install app from file**
4. Sélectionnez le fichier `hydroquebec_pannes_et_interruptions.tar.gz`
5. Cliquez sur **Upload**
6. Redémarrez Splunk si demandé

#### Méthode 2: Ligne de Commande

```bash
# Extraire l'application
cd $SPLUNK_HOME/etc/apps/
tar -xzf /chemin/vers/hydroquebec_pannes_et_interruptions.tar.gz

# Définir les permissions
chown -R splunk:splunk hydroquebec_pannes_et_interruptions
chmod +x hydroquebec_pannes_et_interruptions/bin/*.py

# Redémarrer Splunk
$SPLUNK_HOME/bin/splunk restart
```

### Vérification de l'Installation

#### 1. Vérifier que l'application est visible

```
Apps > Hydro-Québec - Pannes et Interruptions
```

#### 2. Vérifier que l'index est créé

Dans la barre de recherche Splunk:
```
| eventcount summarize=false index=hydroquebec
```

#### 3. Tester les scripts manuellement

```bash
# Test du collecteur de pannes
$SPLUNK_HOME/bin/splunk cmd python3 $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/hydroquebec_collector.py

# Test du collecteur d'interruptions
$SPLUNK_HOME/bin/splunk cmd python3 $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/hydroquebec_collector_interruptions.py

# Test du collecteur de demande
$SPLUNK_HOME/bin/splunk cmd python3 $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/hydroquebec_collector_demande.py
```

#### 4. Attendre la première collecte

Les scripts s'exécutent automatiquement toutes les 15 minutes. Vous pouvez aussi forcer une exécution:

```bash
$SPLUNK_HOME/bin/splunk _internal call /services/data/inputs/script/hydroquebec_collector.py/_reload
```

#### 5. Vérifier les données

Après quelques minutes, vérifiez que les données arrivent:

```
index=hydroquebec | head 10
```

## Configuration

### Index
L'application crée automatiquement l'index `hydroquebec`. Aucune configuration supplémentaire n'est nécessaire.

**Paramètres:**
- **Nom:** hydroquebec
- **Taille max:** 5 Go
- **Rétention:** 1 an

### Sourcetypes
- `hydroquebec:pannes` - Événements de pannes électriques
- `hydroquebec:interruption_planifie` - Événements d'interruptions planifiées
- `hydroquebec:demande` - Mesures de demande d'électricité

### Scripts de Collecte

Les scripts s'exécutent automatiquement toutes les 15 minutes:
- `hydroquebec_collector.py` - Collecte des pannes
- `hydroquebec_collector_interruptions.py` - Collecte des interruptions
- `hydroquebec_collector_demande.py` - Collecte de la demande d'électricité

### Cache de Géocodage

Pour éviter de surcharger l'API OpenStreetMap (limite: 1 requête/seconde), l'application maintient un cache des adresses déjà récupérées dans:
```
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/geocode_cache.pkl
```

### Gestion des États

Les états précédents des pannes, interruptions et demande sont stockés pour détecter les changements:
```
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/pannes_state.pkl
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/interruptions_state.pkl
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/demande_state.pkl
```

### Suivi de Version (v3.1.0+)

Pour optimiser la collecte et réduire le volume de données:
```
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/bis_version.txt
$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/aip_version.txt
```

## Configuration des Alertes

1. Allez dans **Settings** > **Searches, reports, and alerts**
2. Trouvez les alertes préfixées par "Hydro-Québec" ou cherchez dans l'app
3. Pour chaque alerte:
   - Cliquez sur **Edit** > **Edit Schedule**
   - Cochez **Schedule this search**
   - Configurez les actions (Email, Webhook, etc.)
   - **Save**

### Exemple: Configurer l'alerte Email

1. Ouvrez l'alerte "Nouvelle panne détectée"
2. Allez dans **Edit** > **Edit Actions** > **Add Actions** > **Email**
3. Configurez:
   - **To:** votre@email.com
   - **Subject:** Nouvelle panne Hydro-Québec détectée
   - **Message:** Inclure les résultats dans le message
4. **Save**

## Personnalisation

### Modifier le seuil d'alerte pour pannes importantes

1. **Settings** > **Searches, reports, and alerts**
2. Trouvez "Panne importante - Plus de 100 clients"
3. **Edit** > **Edit Search**
4. Changez `where clients > 100` par votre valeur souhaitée
5. **Save**

### Changer la fréquence de collecte

Éditer `$SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/inputs.conf`:

```ini
[script://./bin/hydroquebec_collector.py]
interval = 600  # 10 minutes au lieu de 15
```

Redémarrez Splunk après modification.

## Structure des Données

### Événement de Panne
```json
{
  "id_panne": "45.494453_-73.628187_2025-01-15 10:30:00",
  "nombre_clients": 150,
  "date_debut": "2025-01-15 10:30:00",
  "date_fin_estimee": "2025-01-15 14:00:00",
  "latitude": 45.494453,
  "longitude": -73.628187,
  "statut_code": "L",
  "statut": "Équipe au travail",
  "code_cause": "21",
  "cause_desc": "Conditions météorologiques",
  "id_municipalite": "66023",
  "municipalite": "Montréal",
  "region": "Québec",
  "code_postal": "H4B 1R6",
  "adresse": "6200, Avenue du Parc, Montréal, QC",
  "pays": "Canada",
  "date_collecte": "2025-01-15 10:32:15",
  "type_evenement": "panne"
}
```

### Événement d'Interruption Planifiée
```json
{
  "id_interruption": "INT_12345_45.494453_-73.628187",
  "id_avis": "12345",
  "nombre_clients": 50,
  "date_debut_prevue": "2025-01-16 08:00:00",
  "date_fin_prevue": "2025-01-16 16:00:00",
  "date_debut_reelle": "",
  "date_fin_reelle": "",
  "date_debut_reportee": "",
  "date_fin_reportee": "",
  "date_debut_reprogrammee": "",
  "date_fin_reprogrammee": "",
  "latitude": 45.494453,
  "longitude": -73.628187,
  "statut_code": "A",
  "statut": "Travail assigné",
  "code_cause": "10",
  "cause_desc": "Maintenance planifiée",
  "code_remarque": "",
  "id_municipalite": "66023",
  "municipalite": "Montréal",
  "region": "Québec",
  "code_postal": "H4B 1R6",
  "adresse": "6200, Avenue du Parc, Montréal, QC",
  "pays": "Canada",
  "date_collecte": "2025-01-15 10:32:15",
  "type_evenement": "interruption_planifiee"
}
```

### Événement de Demande d'Électricité
```json
{
  "demande_mw": 35123,
  "date_mesure": "2025-01-15 10:00:00",
  "type_evenement": "demande_electricite",
  "date_collecte": "2025-01-15 10:02:15"
}
```

## Documentation Technique - APIs Utilisées

### API Hydro-Québec - Pannes et Interruptions

#### URL de Base
```
https://pannes.hydroquebec.com/pannes/donnees/v3_0/
```

#### Endpoints

**1. Pannes en Cours**

Étape 1: Obtenir la Version
```
GET https://pannes.hydroquebec.com/pannes/donnees/v3_0/bisversion.json
```

Réponse:
```json
{
  "version": "20250115103000"
}
```

Étape 2: Obtenir les Pannes
```
GET https://pannes.hydroquebec.com/pannes/donnees/v3_0/bismarkers{VERSION}.json
```

**2. Interruptions Planifiées**

Étape 1: Obtenir la Version
```
GET https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipversion.json
```

Étape 2: Obtenir les Interruptions
```
GET https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipmarkers{VERSION}.json
```

#### Codes de Statut

| Code | Description (FR) | Description (EN) |
|------|------------------|------------------|
| A    | Travail assigné  | Work assigned    |
| L    | Équipe au travail | Crew at work    |
| R    | Équipe en route  | Crew en route    |

#### Codes de Cause

| Code | Description |
|------|-------------|
| 11-15, 58, 70, 72-74, 79 | Défaillance d'équipement |
| 21-22, 24-26 | Conditions météorologiques |
| 31-34, 41-44, 54-57 | Accident ou incident |
| 51 | Dommages causés par la végétation |
| 52-53 | Dommages causés par un animal |
| 10 | Code d'équipement (interruptions) |
| defaut | Cause inconnue |

#### Fréquence de Mise à Jour

- Données mises à jour toutes les **15 minutes**
- Recommandation: Collecte toutes les 15 minutes minimum

#### Limites et Restrictions

- Aucune authentification requise
- Aucune limite de taux connue
- Service gratuit et ouvert
- Disponibilité: 24/7

---

### API Hydro-Québec - Demande d'Électricité

#### URL
```
https://www.hydroquebec.com/data/documents-donnees/donnees-ouvertes/json/demande.json
```

#### Structure de la Réponse

```json
{
  "details": [
    {
      "valeur": 35123,
      "date": "2025-01-15 10:00"
    },
    {
      "valeur": 35456,
      "date": "2025-01-15 10:15"
    }
  ]
}
```

#### Champs

| Champ | Type | Description |
|-------|------|-------------|
| `valeur` | Integer | Demande d'électricité en mégawatts (MW) |
| `date` | String | Date et heure de la mesure (format: YYYY-MM-DD HH:MM) |

#### Couverture Géographique
- Province du Québec
- Exclut les régions alimentées par des réseaux autonomes
- Données calculées en temps réel par le Centre de contrôle du réseau d'Hydro-Québec

#### Fréquence de Mise à Jour
- Nouvelle mesure: Toutes les 15 minutes
- Délai de publication: ~2-5 minutes après la mesure

#### Valeurs Typiques

**Demande Normale (sans pointe):**
- Nuit (0h-6h): 20,000 - 25,000 MW
- Jour (9h-17h): 30,000 - 35,000 MW
- Soirée (18h-22h): 35,000 - 38,000 MW

**Pointes de Consommation:**
- Vagues de froid: 38,000 - 42,000 MW
- Record historique: ~42,000 MW (hiver)

---

### API Nominatim (OpenStreetMap)

#### URL de Base
```
https://nominatim.openstreetmap.org/
```

#### Endpoint: Reverse Geocoding

**Requête:**
```
GET https://nominatim.openstreetmap.org/reverse
```

**Paramètres:**
```
lat=45.494453                    # Latitude (requis)
lon=-73.628187                   # Longitude (requis)
format=json                      # Format de réponse (requis)
addressdetails=1                 # Inclure détails d'adresse
accept-language=fr              # Langue préférée
```

**Headers Requis:**
```
User-Agent: Splunk-HydroQuebec-Collector/3.x
```

#### Limites et Restrictions

**Limite de Taux:**
- **1 requête par seconde maximum**
- Notre implémentation respecte cette limite avec `time.sleep(1.1)`

**User-Agent Obligatoire:**
- Requis pour identifier l'application
- Format: `Application/Version`
- Notre valeur: `Splunk-HydroQuebec-Collector/3.x`

**Usage Acceptable:**
- ✅ Usage non-commercial
- ✅ Caching des résultats (fortement recommandé)
- ✅ Respecter les limites de taux
- ❌ Bulk geocoding sans cache
- ❌ Usage commercial sans accord

**Politiques:**
- Licence: ODbL 1.0 (Open Database License)
- Attribution: OpenStreetMap contributors
- Documentation: https://nominatim.org/

#### Optimisations Implémentées

1. **Cache Persistant:**
   - Fichier: `local/geocode_cache.pkl`
   - Format: pickle (Python)
   - Clé: Coordonnées arrondies à 4 décimales
   - Expiration: Aucune (manuel)

2. **Arrondi des Coordonnées:**
   - Précision: 4 décimales (~11 mètres)
   - Améliore le taux de cache hit
   - Acceptable pour notre cas d'usage

3. **Gestion d'Erreurs:**
   - Timeout: 10 secondes
   - Retry: Non (évite la charge)
   - Fallback: Coordonnées brutes si échec

4. **Rate Limiting:**
   - Pause: 1.1 seconde entre requêtes
   - Évite les bans temporaires
   - Garantit la conformité

## Requêtes SPL Utiles

### Pannes

**Pannes Actives:**
```spl
index=hydroquebec sourcetype=hydroquebec:pannes 
| stats count as "Pannes Actives", sum(nombre_clients) as "Clients Affectés"
```

**Top Municipalités:**
```spl
index=hydroquebec sourcetype=hydroquebec:pannes 
| stats sum(nombre_clients) as clients by municipalite 
| sort -clients 
| head 10
```

**Évolution sur 24h:**
```spl
index=hydroquebec sourcetype=hydroquebec:pannes earliest=-24h
| timechart span=1h count as pannes, sum(nombre_clients) as clients
```

### Interruptions

**Prochaines 24 heures:**
```spl
index=hydroquebec sourcetype=hydroquebec:interruption_planifie 
| eval debut_epoch=strptime(date_debut_prevue, "%Y-%m-%d %H:%M:%S")
| where debut_epoch > now() AND debut_epoch < (now() + 86400)
| table municipalite, date_debut_prevue, date_fin_prevue, nombre_clients
```

**Interruptions en cours:**
```spl
index=hydroquebec sourcetype=hydroquebec:interruption_planifie 
| eval debut=strptime(date_debut_prevue, "%Y-%m-%d %H:%M:%S"), fin=strptime(date_fin_prevue, "%Y-%m-%d %H:%M:%S")
| where debut < now() AND fin > now()
| stats count
```

### Demande d'Électricité

**Demande Actuelle:**
```spl
index=hydroquebec sourcetype=hydroquebec:demande 
| stats latest(demande_mw) as "Demande Actuelle (MW)"
```

**Évolution 24h:**
```spl
index=hydroquebec sourcetype=hydroquebec:demande earliest=-24h
| timechart span=15m latest(demande_mw) as "Demande"
```

**Statistiques:**
```spl
index=hydroquebec sourcetype=hydroquebec:demande 
| stats 
    latest(demande_mw) as actuelle,
    max(demande_mw) as maximum,
    min(demande_mw) as minimum,
    avg(demande_mw) as moyenne
```

**Analyse par Heure:**
```spl
index=hydroquebec sourcetype=hydroquebec:demande 
| eval heure=strftime(strptime(date_mesure, "%Y-%m-%d %H:%M"), "%H")
| stats avg(demande_mw) as demande_moyenne by heure
| sort heure
```

**Pointes de Consommation:**
```spl
index=hydroquebec sourcetype=hydroquebec:demande 
| where demande_mw > 38000
| table date_mesure, demande_mw
```

## Dépannage

### Les scripts ne s'exécutent pas

**Solution 1:** Vérifier les permissions
```bash
chmod +x $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/*.py
```

**Solution 2:** Vérifier les logs
```bash
tail -f $SPLUNK_HOME/var/log/splunk/splunkd.log | grep hydroquebec
```

### Aucune donnée n'apparaît

**Solution 1:** Vérifier que l'index existe
```
| eventcount summarize=false index=hydroquebec
```

**Solution 2:** Exécuter manuellement les scripts
```bash
$SPLUNK_HOME/bin/splunk cmd python3 $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/hydroquebec_collector.py
```

**Solution 3:** Vérifier les permissions
```bash
ls -la $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/bin/
# Les fichiers .py doivent être exécutables (-rwxr-xr-x)
```

### Erreur "module 'requests' not found"

**Solution:** Installer le module requests
```bash
$SPLUNK_HOME/bin/splunk cmd python3 -m pip install requests --break-system-packages
```

### Problèmes de géocodage

Si vous atteignez la limite de l'API OpenStreetMap:
- Le cache réduit automatiquement les requêtes répétées
- Les coordonnées sont arrondies à 4 décimales pour améliorer le cache
- Une pause de 1.1 seconde est respectée entre chaque requête

**Vérifier le cache:**
```bash
ls -la $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/geocode_cache.pkl
```

**Augmenter l'intervalle si nécessaire:**
Modifier `inputs.conf` pour passer à 30 minutes au lieu de 15.

### Trop de requêtes vers Nominatim

**Solution 1:** Le cache est automatique. Si le problème persiste:
1. Vérifiez que le cache fonctionne: `ls -la $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/geocode_cache.pkl`
2. Augmentez l'intervalle de collecte à 30 minutes
3. Les nouvelles adresses prendront plus de temps à être géocodées (1 requête/seconde max)

### Aucune nouvelle donnée pour la demande

**Vérifier:**

1. Connectivité à l'API
   ```bash
   curl https://www.hydroquebec.com/data/documents-donnees/donnees-ouvertes/json/demande.json
   ```

2. Dernière exécution du script
   ```bash
   grep "hydroquebec_collector_demande" $SPLUNK_HOME/var/log/splunk/splunkd.log | tail -20
   ```

3. État du fichier
   ```bash
   cat $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/demande_state.pkl
   ```

### Forcer une Nouvelle Collecte

```bash
# Supprimer les fichiers d'état
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/pannes_state.pkl
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/interruptions_state.pkl
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/demande_state.pkl

# Supprimer les fichiers de version (v3.1.0+)
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/bis_version.txt
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/aip_version.txt
```

## Maintenance

### Nettoyer le cache de géocodage

Si le cache devient trop volumineux:
```bash
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/geocode_cache.pkl
```
Le cache sera recréé automatiquement.

### Nettoyer les états des pannes

Pour forcer une resynchronisation complète:
```bash
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/pannes_state.pkl
rm $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/interruptions_state.pkl
```

### Monitoring

**Vérifier les versions actuelles (v3.1.0+):**
```bash
cat $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/bis_version.txt
cat $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/aip_version.txt
```

**Métriques à Monitorer:**
```splunk
index=_internal source=*splunkd.log hydroquebec
| stats count by log_level
```

```splunk
index=hydroquebec
| stats count by sourcetype, type_evenement
| timechart span=1h sum(count) by sourcetype
```

**Santé du Cache:**
```bash
ls -lh $SPLUNK_HOME/etc/apps/hydroquebec_pannes_et_interruptions/local/*.pkl
```

Taille attendue:
- `geocode_cache.pkl`: 10-100 KB (varie selon usage)
- `pannes_state.pkl`: 10-50 KB
- `interruptions_state.pkl`: 5-20 KB
- `demande_state.pkl`: <1 KB

## Mises à Jour

Pour mettre à jour l'application:

1. **Sauvegarder vos configurations:** 
   - Exporter vos alertes modifiées
   - Sauvegarder `local/inputs.conf` si modifié

2. **Désinstaller l'ancienne version:**
   - Apps > Manage Apps > Hydro-Québec > Uninstall

3. **Installer la nouvelle version** (voir instructions ci-dessus)

4. **Restaurer vos configurations**

## Performance et Capacité

### Scénarios de Charge

**Scénario 1: Opération Normale**
- Pannes actives: ~10-50
- Nouvelles pannes par collecte: ~2-5
- Temps de géocodage: ~5-10 secondes (nouvelles adresses)
- Temps total: ~15-20 secondes par collecte

**Scénario 2: Tempête Majeure**
- Pannes actives: ~200-500
- Nouvelles pannes par collecte: ~50-100
- Temps de géocodage: ~60-120 secondes (nouvelles adresses)
- Temps total: ~90-150 secondes par collecte
- Note: Le cache réduit rapidement ce temps

**Scénario 3: Après Cache Établi**
- Cache hit rate: >90%
- Nouvelles adresses: <5 par collecte
- Temps de géocodage: ~5 secondes
- Temps total: ~10 secondes par collecte

### Capacité de Stockage Splunk

**Estimation par Événement:**
- Taille moyenne: ~800 bytes JSON
- Avec overhead Splunk: ~1 KB par événement

**Estimation Annuelle:**
- Collectes/jour: 96 (toutes les 15 min)
- Événements/collecte: ~20 (moyenne)
- Événements/jour: ~1,920
- Événements/an: ~700,800
- Stockage brut: ~700 MB/an
- Avec index: ~1.4 GB/an

**Note:** Avec l'optimisation de suivi de version (v3.1.0+), le volume est réduit de 50-70%.

## Support

Pour toute question ou problème:
1. Consulter les logs Splunk
2. Vérifier la documentation de l'API Hydro-Québec: https://donnees.hydroquebec.com
3. Vérifier la documentation de Nominatim: https://nominatim.org/
4. Consulter le portail de données ouvertes d'Hydro-Québec: https://www.hydroquebec.com/documents-data/open-data/

## Références

- **Portail de données ouvertes**: https://donnees.hydroquebec.com
- **Documentation officielle**: https://www.hydroquebec.com/documents-data/open-data/
- **Dataset demande**: https://donnees.hydroquebec.com/explore/dataset/demande-electricite-quebec/
- **OpenStreetMap**: https://www.openstreetmap.org/
- **Nominatim**: https://nominatim.org/

## Licence

Cette application est distribuée sous licence Apache License 2.0.

Les données proviennent d'Hydro-Québec et sont soumises à leurs conditions d'utilisation:

> Les données fournies représentent des données brutes, sont sans garantie de qualité et peuvent être modifiées sans préavis.

## Auteur

alexandre@argeris.net

## Version

3.2.1 - Décembre 2025
