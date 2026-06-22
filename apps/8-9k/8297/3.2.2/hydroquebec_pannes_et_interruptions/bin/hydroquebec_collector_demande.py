#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Le module 'requests' n'est pas installé. Installez-le avec: pip install requests", file=sys.stderr)
    sys.exit(1)


class HydroQuebecDemandeCollector:
    """Collecteur de données pour la demande d'électricité en temps réel d'Hydro-Québec"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Splunk-HydroQuebec-Collector/3.x'
        })
        
        # Initialiser le fichier d'état pour éviter les duplicatas
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'local')
        self.state_file = os.path.join(cache_dir, 'demande_state.pkl')
    
    def get_demande_data(self):
        """Récupérer les données de demande d'électricité"""
        try:
            url = 'https://www.hydroquebec.com/data/documents-donnees/donnees-ouvertes/json/demande.json'
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: Impossible de récupérer les données de demande: {e}", file=sys.stderr)
            return None
    
    def load_last_state(self):
        """Charger le dernier état pour éviter les duplicatas"""
        if os.path.exists(self.state_file):
            try:
                import pickle
                with open(self.state_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"WARN: Impossible de charger l'état précédent: {e}", file=sys.stderr)
                return None
        return None
    
    def save_state(self, state_data):
        """Sauvegarder l'état actuel"""
        try:
            import pickle
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'wb') as f:
                pickle.dump(state_data, f)
        except Exception as e:
            print(f"WARN: Impossible de sauvegarder l'état: {e}", file=sys.stderr)
    
    def parse_demande_data(self, data):
        """Parser et transformer les données de demande"""
        try:
            # Structure réelle du JSON Hydro-Québec:
            # {
            #   "details": [
            #     {
            #       "date": "2025-12-07T01:15:00",
            #       "valeurs": {
            #         "demandeTotal": 27597.0
            #       }
            #     },
            #     ...
            #   ],
            #   "recentHour": "2025-12-08T15:30:00",
            #   "indexDonneePlusRecent": 158
            # }
            
            details = data.get('details', [])
            
            if not details:
                print("WARN: Aucune donnée dans l'array 'details'", file=sys.stderr)
                return []
            
            events = []
            
            # Parcourir toutes les entrées
            for entry in details:
                date_mesure = entry.get('date')
                valeurs = entry.get('valeurs', {})
                demande_total = valeurs.get('demandeTotal')
                
                # Ignorer les entrées sans demandeTotal (données futures)
                if not date_mesure or demande_total is None:
                    continue
                
                # Convertir la date ISO au format Splunk (sans le T)
                # "2025-12-07T01:15:00" -> "2025-12-07 01:15:00"
                date_mesure_formatted = date_mesure.replace('T', ' ')
                
                event = {
                    'demande_mw': demande_total,
                    'date_mesure': date_mesure_formatted,
                    'type_evenement': 'demande_electricite',
                    'date_collecte': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                events.append(event)
            
            return events
            
        except Exception as e:
            print(f"ERROR: Erreur lors du parsing des données de demande: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return []
    
    def collect(self):
        """Collecter les données de demande et envoyer à Splunk"""
        
        # Récupérer les données
        data = self.get_demande_data()
        if not data:
            return
        
        # Parser les données
        events = self.parse_demande_data(data)
        if not events:
            print("WARN: Aucun événement valide à envoyer", file=sys.stderr)
            return
        
        # Charger l'état précédent
        last_state = self.load_last_state()
        last_dates = set(last_state.get('collected_dates', [])) if last_state else set()
        
        # Filtrer les événements déjà collectés
        new_events = []
        for event in events:
            date_key = event['date_mesure']
            if date_key not in last_dates:
                new_events.append(event)
        
        if not new_events:
            print(f"INFO: Aucune nouvelle donnée ({len(events)} déjà collectées)", file=sys.stderr)
            return
        
        # Envoyer les nouveaux événements à Splunk (STDOUT seulement)
        for event in new_events:
            print(json.dumps(event, ensure_ascii=False))
        
        # Log dans STDERR (ne va pas dans Splunk)
        print(f"INFO: {len(new_events)} événement(s) envoyé(s) sur {len(events)} total", file=sys.stderr)
        
        # Mettre à jour l'état avec toutes les dates collectées
        # Garder seulement les 200 dernières dates pour ne pas surcharger
        all_dates = last_dates.union(set(e['date_mesure'] for e in new_events))
        all_dates = sorted(all_dates, reverse=True)[:200]
        
        self.save_state({'collected_dates': list(all_dates)})


def main():
    """Point d'entrée principal"""
    try:
        collector = HydroQuebecDemandeCollector()
        collector.collect()
    except Exception as e:
        print(f"ERROR: Erreur fatale: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
