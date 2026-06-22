#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import time
import os
import pickle
from datetime import datetime
from pathlib import Path

# Gestion du timezone avec fallback pour anciennes versions Python
try:
    from zoneinfo import ZoneInfo
    TZ_AVAILABLE = True
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
        TZ_AVAILABLE = True
    except ImportError:
        TZ_AVAILABLE = False
        print("WARN: Module zoneinfo non disponible. Utilisation du timezone local du serveur.", file=sys.stderr)
        print("WARN: Pour installer: /opt/splunk/bin/splunk cmd python3 -m pip install backports.zoneinfo", file=sys.stderr)

try:
    import requests
except ImportError:
    print("ERROR: Le module 'requests' n'est pas installé. Installez-le avec: pip install requests", file=sys.stderr)
    sys.exit(1)


class GeocodeCache:
    """Cache pour les adresses géocodées"""
    
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self):
        """Charger le cache depuis le fichier"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"WARN: Impossible de charger le cache: {e}", file=sys.stderr)
                return {}
        return {}
    
    def _save_cache(self):
        """Sauvegarder le cache dans le fichier"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            print(f"WARN: Impossible de sauvegarder le cache: {e}", file=sys.stderr)
    
    def get_key(self, lat, lon):
        """Générer une clé de cache basée sur les coordonnées (arrondie à 4 décimales)"""
        return f"{round(lat, 4)},{round(lon, 4)}"
    
    def get(self, lat, lon):
        """Récupérer une adresse du cache"""
        key = self.get_key(lat, lon)
        return self.cache.get(key)
    
    def set(self, lat, lon, address_data):
        """Enregistrer une adresse dans le cache"""
        key = self.get_key(lat, lon)
        self.cache[key] = address_data
        self._save_cache()


class VersionTracker:
    """Gestionnaire de suivi des versions BIS/AIP"""
    
    def __init__(self, version_file):
        self.version_file = version_file
    
    def get_last_version(self):
        """Récupérer la dernière version traitée"""
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"WARN: Impossible de lire la dernière version: {e}", file=sys.stderr)
                return None
        return None
    
    def save_version(self, version):
        """Sauvegarder la version actuelle"""
        try:
            os.makedirs(os.path.dirname(self.version_file), exist_ok=True)
            with open(self.version_file, 'w') as f:
                f.write(version)
        except Exception as e:
            print(f"WARN: Impossible de sauvegarder la version: {e}", file=sys.stderr)


class HydroQuebecCollector:
    """Collecteur de données pour les pannes d'Hydro-Québec"""
    
    # Mapping des codes de cause vers descriptions en français
    CAUSES = {
        '11': 'Défaillance d\'équipement',
        '12': 'Défaillance d\'équipement',
        '13': 'Défaillance d\'équipement',
        '14': 'Défaillance d\'équipement',
        '15': 'Défaillance d\'équipement',
        '58': 'Défaillance d\'équipement',
        '70': 'Défaillance d\'équipement',
        '72': 'Défaillance d\'équipement',
        '73': 'Défaillance d\'équipement',
        '74': 'Défaillance d\'équipement',
        '79': 'Défaillance d\'équipement',
        '21': 'Conditions météorologiques',
        '22': 'Conditions météorologiques',
        '24': 'Conditions météorologiques',
        '25': 'Conditions météorologiques',
        '26': 'Conditions météorologiques',
        '31': 'Accident ou incident',
        '32': 'Accident ou incident',
        '33': 'Accident ou incident',
        '34': 'Accident ou incident',
        '41': 'Accident ou incident',
        '42': 'Accident ou incident',
        '43': 'Accident ou incident',
        '44': 'Accident ou incident',
        '54': 'Accident ou incident',
        '55': 'Accident ou incident',
        '56': 'Accident ou incident',
        '57': 'Accident ou incident',
        '51': 'Dommages causés par la végétation',
        '52': 'Dommages causés par un animal',
        '53': 'Dommages causés par un animal',
        'defaut': 'Cause inconnue'
    }
    
    # Mapping des codes de statut
    STATUTS = {
        'A': 'Travail assigné',
        'L': 'Équipe au travail',
        'R': 'Équipe en route',
        'N': 'En attente de validation'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Splunk-HydroQuebec-Collector/3.x'
        })
        
        # Initialiser le cache de géocodage
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'local')
        cache_file = os.path.join(cache_dir, 'geocode_cache.pkl')
        self.geocode_cache = GeocodeCache(cache_file)
        
        # Initialiser le suivi de version
        version_file = os.path.join(cache_dir, 'bis_version.txt')
        self.version_tracker = VersionTracker(version_file)
    
    def convert_bis_to_timestamp(self, bis_version):
        """Convertir le bis_version (format YYYYMMDDHHmmss) en timestamp ISO 8601"""
        try:
            # Format: 20251125155014 -> 2025-11-25T15:50:14
            year = bis_version[0:4]
            month = bis_version[4:6]
            day = bis_version[6:8]
            hour = bis_version[8:10]
            minute = bis_version[10:12]
            second = bis_version[12:14]
            
            return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        except Exception as e:
            print(f"WARN: Impossible de convertir bis_version '{bis_version}': {e}", file=sys.stderr)
            return bis_version
    
    def get_bis_version(self):
        """Récupérer la version actuelle du fichier BIS"""
        try:
            url = 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/bisversion.json'
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # L'API peut retourner soit un JSON, soit juste un string
            try:
                data = response.json()
                # Si c'est un dict avec 'version'
                if isinstance(data, dict):
                    return data.get('version')
                # Si c'est directement la version (string)
                elif isinstance(data, str):
                    return data
                else:
                    return str(data)
            except:
                # Si le JSON parse échoue, utiliser le texte brut
                return response.text.strip().strip('"')
                
        except Exception as e:
            print(f"ERROR: Impossible de récupérer la version BIS: {e}", file=sys.stderr)
            return None
    
    def get_pannes(self, bis_version):
        """Récupérer la liste des pannes"""
        try:
            url = f'https://pannes.hydroquebec.com/pannes/donnees/v3_0/bismarkers{bis_version}.json'
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: Impossible de récupérer les pannes: {e}", file=sys.stderr)
            return None
    
    def reverse_geocode(self, lat, lon):
        """Géocoder inversement des coordonnées pour obtenir l'adresse"""
        # Vérifier le cache d'abord
        cached = self.geocode_cache.get(lat, lon)
        if cached:
            return cached
        
        try:
            # Respecter la limite de 1 requête par seconde
            time.sleep(1.1)
            
            url = 'https://nominatim.openstreetmap.org/reverse'
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'fr'
            }
            headers = {
                'User-Agent': 'Splunk-HydroQuebec-Collector/3.x'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extraire les informations d'adresse
            address = data.get('address', {})
            display_name = data.get('display_name', '')
            
            # Extraire la région depuis l'adresse complète (4ème segment avant la fin)
            # Format: "adresse, ville, MRC, région, province, code postal, pays"
            region = 'Québec'  # Valeur par défaut
            if display_name:
                parts = [p.strip() for p in display_name.split(',')]
                if len(parts) >= 4:
                    # Le 4ème avant la fin est la région administrative
                    region = parts[-4]
            
            result = {
                'municipalite': address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or 'Inconnue',
                'region': region,
                'code_postal': address.get('postcode', ''),
                'adresse': display_name,
                'pays': address.get('country', 'Canada')
            }
            
            # Mettre en cache
            self.geocode_cache.set(lat, lon, result)
            
            return result
            
        except Exception as e:
            print(f"WARN: Erreur lors du géocodage de ({lat}, {lon}): {e}", file=sys.stderr)
            return {
                'municipalite': 'Inconnue',
                'region': 'Québec',
                'code_postal': '',
                'adresse': f'Coordonnées: {lat}, {lon}',
                'pays': 'Canada'
            }
    
    def parse_panne(self, panne_data, bis_version):
        """Parser les données d'une panne"""
        try:
            # Format des données: 
            # [nombre_clients, date_debut, date_fin_estimee, "P", coordonnees, statut, ?, code_cause, ?, id_municipalite, message_id]
            
            nombre_clients = panne_data[0]
            date_debut = panne_data[1]
            date_fin_estimee = panne_data[2]
            type_evenement = panne_data[3]
            
            # Parser les coordonnées
            coords_str = panne_data[4]
            coords = json.loads(coords_str) if isinstance(coords_str, str) else coords_str
            longitude = coords[0]
            latitude = coords[1]
            
            statut_code = panne_data[5]
            code_cause = str(panne_data[7])
            id_municipalite = panne_data[9]
            
            # Créer un ID unique pour la panne
            id_panne = f"{latitude}_{longitude}_{date_debut}"
            
            # Obtenir l'adresse (avec cache)
            adresse_info = self.reverse_geocode(latitude, longitude)
            
            # Construire l'événement
            event = {
                'id_panne': id_panne,
                'nombre_clients': nombre_clients,
                'date_debut': date_debut,
                'date_fin_estimee': date_fin_estimee,
                'latitude': latitude,
                'longitude': longitude,
                'statut_code': statut_code,
                'statut': self.STATUTS.get(statut_code, statut_code),
                'code_cause': code_cause,
                'cause_desc': self.CAUSES.get(code_cause, 'Cause inconnue'),
                'id_municipalite': id_municipalite,
                'municipalite': adresse_info['municipalite'],
                'region': adresse_info['region'],
                'code_postal': adresse_info['code_postal'],
                'adresse': adresse_info['adresse'],
                'pays': adresse_info['pays'],
                'bis_id': bis_version,
                'bis_timestamp': self.convert_bis_to_timestamp(bis_version),
                'type_evenement': 'panne'
            }
            
            return event
            
        except Exception as e:
            print(f"ERROR: Erreur lors du parsing d'une panne: {e}", file=sys.stderr)
            print(f"Données brutes: {panne_data}", file=sys.stderr)
            return None
    
    def collect(self):
        """Collecter les pannes et envoyer à Splunk"""
        
        # Récupérer la version BIS
        bis_version = self.get_bis_version()
        if not bis_version:
            return
        
        # Vérifier si la version a changé
        last_version = self.version_tracker.get_last_version()
        if last_version:
            if bis_version == last_version:
                # Version inchangée, pas de collecte
                return
        
        # Récupérer les pannes
        pannes_data = self.get_pannes(bis_version)
        if not pannes_data:
            return
        
        pannes_list = pannes_data.get('pannes', [])
        
        # Parser chaque panne et envoyer tous les événements
        for panne_data in pannes_list:
            event = self.parse_panne(panne_data, bis_version)
            if event:
                # Envoyer directement l'événement à Splunk (stdout uniquement)
                print(json.dumps(event, ensure_ascii=False))
        
        # Sauvegarder la version actuelle
        self.version_tracker.save_version(bis_version)


def main():
    """Point d'entrée principal"""
    try:
        collector = HydroQuebecCollector()
        collector.collect()
    except Exception as e:
        print(f"ERROR: Erreur fatale: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
