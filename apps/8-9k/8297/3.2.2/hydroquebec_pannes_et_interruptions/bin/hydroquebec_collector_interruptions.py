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


class HydroQuebecInterruptionsCollector:
    """Collecteur de données pour les interruptions planifiées d'Hydro-Québec"""
    
    # Mapping des codes de cause vers descriptions en français
    CAUSES = {
        '11': 'Défaillance d\'équipement',
        '12': 'Défaillance d\'équipement',
        '13': 'Défaillance d\'équipement',
        '14': 'Défaillance d\'équipement',
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
        '10': 'Code d\'équipement',
        'defaut': 'Cause inconnue'
    }
    
    # Mapping des codes de statut
    STATUTS = {
        'A': 'Travail assigné',
        'L': 'Équipe au travail',
        'R': 'Équipe en route'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Splunk-HydroQuebec-Collector/3.x'
        })
        
        # Initialiser le cache de géocodage (partagé avec le collecteur de pannes)
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'local')
        cache_file = os.path.join(cache_dir, 'geocode_cache.pkl')
        self.geocode_cache = GeocodeCache(cache_file)
        
        # Initialiser le suivi de version
        version_file = os.path.join(cache_dir, 'aip_version.txt')
        self.version_tracker = VersionTracker(version_file)
    
    def convert_aip_to_timestamp(self, aip_version):
        """Convertir le aip_version (format YYYYMMDDHHmmss) en timestamp ISO 8601"""
        try:
            # Format: 20251125155014 -> 2025-11-25T15:50:14
            year = aip_version[0:4]
            month = aip_version[4:6]
            day = aip_version[6:8]
            hour = aip_version[8:10]
            minute = aip_version[10:12]
            second = aip_version[12:14]
            
            return f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        except Exception as e:
            print(f"WARN: Impossible de convertir aip_version '{aip_version}': {e}", file=sys.stderr)
            return aip_version
    
    def get_aip_version(self):
        """Récupérer la version actuelle du fichier AIP"""
        try:
            url = 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipversion.json'
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
            print(f"ERROR: Impossible de récupérer la version AIP: {e}", file=sys.stderr)
            return None
    
    def get_interruptions(self, aip_version):
        """Récupérer la liste des interruptions planifiées"""
        try:
            url = f'https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipmarkers{aip_version}.json'
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: Impossible de récupérer les interruptions: {e}", file=sys.stderr)
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
    
    def parse_interruption(self, interruption_data, aip_version):
        """Parser les données d'une interruption planifiée"""
        try:
            # Format des données (selon la documentation):
            # [nombre_clients, id_avis, date_debut_prevue, date_fin_prevue, date_debut_reelle, 
            #  date_fin_reelle, date_debut_reportee, date_fin_reportee, date_debut_reprogrammee,
            #  date_fin_reprogrammee, code_cause, ?, code_remarque, id_municipalite, statut, coordonnees]
            
            nombre_clients = interruption_data[0]
            id_avis = interruption_data[1]
            date_debut_prevue = interruption_data[2] if interruption_data[2] else ''
            date_fin_prevue = interruption_data[3] if interruption_data[3] else ''
            date_debut_reelle = interruption_data[4] if interruption_data[4] else ''
            date_fin_reelle = interruption_data[5] if interruption_data[5] else ''
            date_debut_reportee = interruption_data[6] if interruption_data[6] else ''
            date_fin_reportee = interruption_data[7] if interruption_data[7] else ''
            date_debut_reprogrammee = interruption_data[8] if interruption_data[8] else ''
            date_fin_reprogrammee = interruption_data[9] if interruption_data[9] else ''
            
            code_cause = str(interruption_data[10])
            code_remarque = interruption_data[12]
            id_municipalite = interruption_data[13]
            statut_code = interruption_data[14]
            
            # Parser les coordonnées
            coords_str = interruption_data[15]
            coords = json.loads(coords_str) if isinstance(coords_str, str) else coords_str
            longitude = coords[0]
            latitude = coords[1]
            
            # Créer un ID unique pour l'interruption
            id_interruption = f"INT_{id_avis}_{latitude}_{longitude}"
            
            # Obtenir l'adresse (avec cache)
            adresse_info = self.reverse_geocode(latitude, longitude)
            
            # Construire l'événement
            event = {
                'id_interruption': id_interruption,
                'id_avis': id_avis,
                'nombre_clients': nombre_clients,
                'date_debut_prevue': date_debut_prevue,
                'date_fin_prevue': date_fin_prevue,
                'date_debut_reelle': date_debut_reelle,
                'date_fin_reelle': date_fin_reelle,
                'date_debut_reportee': date_debut_reportee,
                'date_fin_reportee': date_fin_reportee,
                'date_debut_reprogrammee': date_debut_reprogrammee,
                'date_fin_reprogrammee': date_fin_reprogrammee,
                'latitude': latitude,
                'longitude': longitude,
                'statut_code': statut_code,
                'statut': self.STATUTS.get(statut_code, statut_code),
                'code_cause': code_cause,
                'cause_desc': self.CAUSES.get(code_cause, 'Maintenance planifiée'),
                'code_remarque': code_remarque,
                'id_municipalite': id_municipalite,
                'municipalite': adresse_info['municipalite'],
                'region': adresse_info['region'],
                'code_postal': adresse_info['code_postal'],
                'adresse': adresse_info['adresse'],
                'pays': adresse_info['pays'],
                'aip_id': aip_version,
                'aip_timestamp': self.convert_aip_to_timestamp(aip_version),
                'type_evenement': 'interruption_planifiee'
            }
            
            return event
            
        except Exception as e:
            print(f"ERROR: Erreur lors du parsing d'une interruption: {e}", file=sys.stderr)
            print(f"Données brutes: {interruption_data}", file=sys.stderr)
            return None
    
    def collect(self):
        """Collecter les interruptions planifiées et envoyer à Splunk"""
        
        # Récupérer la version AIP
        aip_version = self.get_aip_version()
        if not aip_version:
            return
        
        # Vérifier si la version a changé
        last_version = self.version_tracker.get_last_version()
        if last_version:
            if aip_version == last_version:
                # Version inchangée, pas de collecte
                return
        
        # Récupérer les interruptions
        interruptions_data = self.get_interruptions(aip_version)
        if not interruptions_data:
            return
        
        # La structure peut varier, essayer différentes clés
        interruptions_list = []
        if isinstance(interruptions_data, dict):
            interruptions_list = interruptions_data.get('aips', []) or interruptions_data.get('interruptions', [])
        elif isinstance(interruptions_data, list):
            interruptions_list = interruptions_data
        
        # Parser chaque interruption et envoyer tous les événements
        for interruption_data in interruptions_list:
            event = self.parse_interruption(interruption_data, aip_version)
            if event:
                # Envoyer directement l'événement à Splunk (stdout uniquement)
                print(json.dumps(event, ensure_ascii=False))
        
        # Sauvegarder la version actuelle
        self.version_tracker.save_version(aip_version)


def main():
    """Point d'entrée principal"""
    try:
        collector = HydroQuebecInterruptionsCollector()
        collector.collect()
    except Exception as e:
        print(f"ERROR: Erreur fatale: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
