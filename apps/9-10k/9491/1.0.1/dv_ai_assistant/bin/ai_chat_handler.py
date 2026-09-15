import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import time
import os
import re
import subprocess
import sys
import splunk.admin as admin
import splunk.rest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import splunk_io as sio          
from guardrail import Guardrail   
from datamodel_policy import parse_datamodel_definitions   



DEFAULT_TRIAGE_PROMPT = "You are a senior SOC analyst. Analyze the supplied alert using only visible evidence."

APP_ID = "dv_ai_assistant"
AUDIT_LOG_FILE = "dv_ai_assistant_ai_audit.log"
AUDIT_SOURCETYPE = "dv_ai_assistant:ai_audit"


_PROTECTED_CIDRS = [
    "127.0.0.0/8",      
    "10.0.0.0/8",       
    "172.16.0.0/12",    
    "192.168.0.0/16",   
    "169.254.0.0/16",   
    "0.0.0.0/8",        
    "224.0.0.0/4",      
    "240.0.0.0/4",      
    "255.255.255.255/32"
]


_BACKEND_MESSAGES = {
    "en": {
        "prompt_missing": "Error: Prompt is missing.",
        "provider_read": "Error: Could not read AI engines.",
        "provider_none": "Error: No AI engines configured.",
        "auth_denied": "⛔ [ PERMISSION DENIED: IP LIST CHANGE ]\n\nThis action requires the 'block_ip' capability. Contact a SOC administrator.",
        "invalid_unblock": "⛔ [ IP UNBLOCK REJECTED ]\n\n'{ip}' is not a valid IPv4 address.",
        "lookup_failed": "❌ [ CHECK FAILED ] Could not read the IP blocklist: {error}",
        "not_found": "ℹ️ [ NO ACTION REQUIRED ]\n\n'{ip}' was not found in ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ CONFIRMATION REQUIRED: REMOVE IP FROM BLOCKLIST ]\n\n'{ip}' will be removed from ai_ip_block.csv and the firewall feed will be refreshed.\n\nTo confirm, enter exactly:\nunconfirm {ip}\n\nEnter anything else to cancel.",
        "block_rejected": "⛔ [ IP BLOCK REJECTED ]\n\n'{ip}' could not be blocked: {reason}.",
        "block_not_allowed": "⚠️ [ IP BLOCK NOT ALLOWED ]\n\n'{ip}' cannot be blocked automatically: {reason}.\n\nNo action was taken.",
        "confirm_block": "🛑 [ CONFIRMATION REQUIRED: ADD IP TO BLOCKLIST ]\n\n'{ip}' will be added to the permanent blocklist (ai_ip_block.csv) and the firewall feed will be refreshed.\n\nTo confirm, enter exactly:\nconfirm {ip}\n\nEnter anything else to cancel.",
        "block_success": "🚨 [ ACTION COMPLETED: IP ADDED TO BLOCKLIST ]\n\n'{ip}' was added to ai_ip_block.csv and the firewall feed was refreshed.\n\n🌐 Integration URL:\n{url}",
        "block_failed": "❌ [ ACTION FAILED ] The IP block operation failed: {error}",
        "unblock_success": "🎉 [ ACTION COMPLETED: IP REMOVED FROM BLOCKLIST ]\n\n'{ip}' was removed from ai_ip_block.csv. The firewall feed was regenerated and the IP is no longer present in ai_ip_block.txt.\n\n🌐 Integration URL:\n{url}",
        "unblock_failed": "❌ [ ACTION FAILED ] The IP unblock operation failed: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: SEARCH BLOCKED ]\n\nThe generated SPL contains a write or side-effecting command and was not executed. This assistant can execute read-only searches only.\n\nDetected risk: {issues}\n\nBlocked search (for reference):\n```spl\n{spl}\n```",
        "connection_failed": "Connection failed: {error}"
    },
    "tr": {
        "prompt_missing": "Hata: İstek metni eksik.",
        "provider_read": "Hata: AI sağlayıcıları okunamadı.",
        "provider_none": "Hata: Yapılandırılmış AI sağlayıcısı bulunamadı.",
        "auth_denied": "⛔ [ YETKİ YOK: IP LİSTESİ DEĞİŞİKLİĞİ ]\n\nBu işlem için 'block_ip' yetkisi gereklidir. Bir SOC yöneticisiyle iletişime geçin.",
        "invalid_unblock": "⛔ [ IP ENGEL KALDIRMA REDDEDİLDİ ]\n\n'{ip}' geçerli bir IPv4 adresi değil.",
        "lookup_failed": "❌ [ KONTROL BAŞARISIZ ] IP engelleme listesi okunamadı: {error}",
        "not_found": "ℹ️ [ İŞLEM GEREKMİYOR ]\n\n'{ip}' ai_ip_block.csv içinde bulunamadı.",
        "confirm_unblock": "🛑 [ ONAY GEREKLİ: IP ENGELİNİ KALDIR ]\n\n'{ip}' ai_ip_block.csv listesinden çıkarılacak ve firewall beslemesi yenilenecek.\n\nOnaylamak için tam olarak şunu girin:\nunconfirm {ip}\n\nİptal etmek için başka bir şey girin.",
        "block_rejected": "⛔ [ IP ENGELLEME REDDEDİLDİ ]\n\n'{ip}' engellenemedi: {reason}.",
        "block_not_allowed": "⚠️ [ IP ENGELLEMEYE İZİN VERİLMEDİ ]\n\n'{ip}' otomatik olarak engellenemez: {reason}.\n\nHerhangi bir işlem yapılmadı.",
        "confirm_block": "🛑 [ ONAY GEREKLİ: IP'Yİ ENGELLE ]\n\n'{ip}' kalıcı engelleme listesine (ai_ip_block.csv) eklenecek ve firewall beslemesi yenilenecek.\n\nOnaylamak için tam olarak şunu girin:\nconfirm {ip}\n\nİptal etmek için başka bir şey girin.",
        "block_success": "🚨 [ İŞLEM TAMAMLANDI: IP ENGELLEME LİSTESİNE EKLENDİ ]\n\n'{ip}' ai_ip_block.csv listesine eklendi ve firewall beslemesi yenilendi.\n\n🌐 Entegrasyon URL'si:\n{url}",
        "block_failed": "❌ [ İŞLEM BAŞARISIZ ] IP engelleme işlemi başarısız oldu: {error}",
        "unblock_success": "🎉 [ İŞLEM TAMAMLANDI: IP ENGELLEME LİSTESİNDEN ÇIKARILDI ]\n\n'{ip}' ai_ip_block.csv listesinden çıkarıldı. Firewall beslemesi yeniden üretildi ve IP'nin ai_ip_block.txt içinde bulunmadığı doğrulandı.\n\n🌐 Entegrasyon URL'si:\n{url}",
        "unblock_failed": "❌ [ İŞLEM BAŞARISIZ ] IP engel kaldırma işlemi başarısız oldu: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: SORGU ENGELLENDİ ]\n\nÜretilen SPL yazma veya yan etkili bir komut içerdiği için çalıştırılmadı. Bu asistan yalnızca salt okunur aramalar çalıştırabilir.\n\nTespit edilen risk: {issues}\n\nEngellenen sorgu:\n```spl\n{spl}\n```",
        "connection_failed": "Bağlantı başarısız: {error}"
    },
    "de": {
        "prompt_missing": "Fehler: Die Anfrage fehlt.",
        "provider_read": "Fehler: AI-Anbieter konnten nicht gelesen werden.",
        "provider_none": "Fehler: Kein AI-Anbieter konfiguriert.",
        "auth_denied": "⛔ [ KEINE BERECHTIGUNG: IP-LISTE ÄNDERN ]\n\nFür diese Aktion ist die Berechtigung 'block_ip' erforderlich. Wenden Sie sich an einen SOC-Administrator.",
        "invalid_unblock": "⛔ [ IP-ENTSPERRUNG ABGELEHNT ]\n\n'{ip}' ist keine gültige IPv4-Adresse.",
        "lookup_failed": "❌ [ PRÜFUNG FEHLGESCHLAGEN ] Die IP-Sperrliste konnte nicht gelesen werden: {error}",
        "not_found": "ℹ️ [ KEINE AKTION ERFORDERLICH ]\n\n'{ip}' wurde in ai_ip_block.csv nicht gefunden.",
        "confirm_unblock": "🛑 [ BESTÄTIGUNG ERFORDERLICH: IP ENTSPERREN ]\n\n'{ip}' wird aus ai_ip_block.csv entfernt und der Firewall-Feed wird aktualisiert.\n\nZur Bestätigung genau eingeben:\nunconfirm {ip}\n\nEine andere Eingabe bricht den Vorgang ab.",
        "block_rejected": "⛔ [ IP-SPERRE ABGELEHNT ]\n\n'{ip}' konnte nicht gesperrt werden: {reason}.",
        "block_not_allowed": "⚠️ [ IP-SPERRE NICHT ZULÄSSIG ]\n\n'{ip}' kann nicht automatisch gesperrt werden: {reason}.\n\nEs wurde keine Aktion ausgeführt.",
        "confirm_block": "🛑 [ BESTÄTIGUNG ERFORDERLICH: IP SPERREN ]\n\n'{ip}' wird zur permanenten Sperrliste hinzugefügt und der Firewall-Feed wird aktualisiert.\n\nZur Bestätigung genau eingeben:\nconfirm {ip}\n\nEine andere Eingabe bricht den Vorgang ab.",
        "block_success": "🚨 [ AKTION ABGESCHLOSSEN: IP GESPERRT ]\n\n'{ip}' wurde zu ai_ip_block.csv hinzugefügt und der Firewall-Feed wurde aktualisiert.\n\n🌐 Integrations-URL:\n{url}",
        "block_failed": "❌ [ AKTION FEHLGESCHLAGEN ] Die IP-Sperre ist fehlgeschlagen: {error}",
        "unblock_success": "🎉 [ AKTION ABGESCHLOSSEN: IP ENTSPERRT ]\n\n'{ip}' wurde aus ai_ip_block.csv entfernt. Der Firewall-Feed wurde neu erstellt.\n\n🌐 Integrations-URL:\n{url}",
        "unblock_failed": "❌ [ AKTION FEHLGESCHLAGEN ] Die IP-Entsperrung ist fehlgeschlagen: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: SUCHE BLOCKIERT ]\n\nDas erzeugte SPL enthält einen Schreib- oder Seiteneffekt-Befehl und wurde nicht ausgeführt. Es sind nur schreibgeschützte Suchen erlaubt.\n\nErkanntes Risiko: {issues}\n\nBlockierte Suche:\n```spl\n{spl}\n```",
        "connection_failed": "Verbindung fehlgeschlagen: {error}"
    },
    "fr": {
        "prompt_missing": "Erreur : la requête est manquante.",
        "provider_read": "Erreur : impossible de lire les fournisseurs IA.",
        "provider_none": "Erreur : aucun fournisseur IA n'est configuré.",
        "auth_denied": "⛔ [ AUTORISATION REFUSÉE : MODIFICATION DE LA LISTE IP ]\n\nCette action nécessite la capacité 'block_ip'. Contactez un administrateur SOC.",
        "invalid_unblock": "⛔ [ DÉBLOCAGE IP REFUSÉ ]\n\n'{ip}' n'est pas une adresse IPv4 valide.",
        "lookup_failed": "❌ [ VÉRIFICATION ÉCHOUÉE ] Impossible de lire la liste de blocage IP : {error}",
        "not_found": "ℹ️ [ AUCUNE ACTION REQUISE ]\n\n'{ip}' est introuvable dans ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ CONFIRMATION REQUISE : DÉBLOQUER L'IP ]\n\n'{ip}' sera supprimée de ai_ip_block.csv et le flux firewall sera actualisé.\n\nPour confirmer, saisissez exactement :\nunconfirm {ip}\n\nToute autre saisie annule l'opération.",
        "block_rejected": "⛔ [ BLOCAGE IP REFUSÉ ]\n\n'{ip}' n'a pas pu être bloquée : {reason}.",
        "block_not_allowed": "⚠️ [ BLOCAGE IP NON AUTORISÉ ]\n\n'{ip}' ne peut pas être bloquée automatiquement : {reason}.\n\nAucune action n'a été effectuée.",
        "confirm_block": "🛑 [ CONFIRMATION REQUISE : BLOQUER L'IP ]\n\n'{ip}' sera ajoutée à la liste de blocage permanente et le flux firewall sera actualisé.\n\nPour confirmer, saisissez exactement :\nconfirm {ip}\n\nToute autre saisie annule l'opération.",
        "block_success": "🚨 [ ACTION TERMINÉE : IP BLOQUÉE ]\n\n'{ip}' a été ajoutée à ai_ip_block.csv et le flux firewall a été actualisé.\n\n🌐 URL d'intégration :\n{url}",
        "block_failed": "❌ [ ÉCHEC DE L'ACTION ] Le blocage IP a échoué : {error}",
        "unblock_success": "🎉 [ ACTION TERMINÉE : IP DÉBLOQUÉE ]\n\n'{ip}' a été supprimée de ai_ip_block.csv. Le flux firewall a été régénéré.\n\n🌐 URL d'intégration :\n{url}",
        "unblock_failed": "❌ [ ÉCHEC DE L'ACTION ] Le déblocage IP a échoué : {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL : RECHERCHE BLOQUÉE ]\n\nLe SPL généré contient une commande d'écriture ou à effet de bord et n'a pas été exécuté. Seules les recherches en lecture seule sont autorisées.\n\nRisque détecté : {issues}\n\nRecherche bloquée :\n```spl\n{spl}\n```",
        "connection_failed": "Échec de la connexion : {error}"
    },
    "es": {
        "prompt_missing": "Error: falta la solicitud.",
        "provider_read": "Error: no se pudieron leer los proveedores de IA.",
        "provider_none": "Error: no hay proveedores de IA configurados.",
        "auth_denied": "⛔ [ SIN PERMISO: CAMBIO DE LISTA IP ]\n\nEsta acción requiere la capacidad 'block_ip'. Contacte con un administrador SOC.",
        "invalid_unblock": "⛔ [ DESBLOQUEO IP RECHAZADO ]\n\n'{ip}' no es una dirección IPv4 válida.",
        "lookup_failed": "❌ [ COMPROBACIÓN FALLIDA ] No se pudo leer la lista de bloqueo IP: {error}",
        "not_found": "ℹ️ [ NO SE REQUIERE ACCIÓN ]\n\n'{ip}' no se encontró en ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ CONFIRMACIÓN REQUERIDA: DESBLOQUEAR IP ]\n\n'{ip}' se eliminará de ai_ip_block.csv y se actualizará el feed del firewall.\n\nPara confirmar, escriba exactamente:\nunconfirm {ip}\n\nCualquier otra entrada cancela la operación.",
        "block_rejected": "⛔ [ BLOQUEO IP RECHAZADO ]\n\nNo se pudo bloquear '{ip}': {reason}.",
        "block_not_allowed": "⚠️ [ BLOQUEO IP NO PERMITIDO ]\n\n'{ip}' no puede bloquearse automáticamente: {reason}.\n\nNo se realizó ninguna acción.",
        "confirm_block": "🛑 [ CONFIRMACIÓN REQUERIDA: BLOQUEAR IP ]\n\n'{ip}' se añadirá a la lista de bloqueo permanente y se actualizará el feed del firewall.\n\nPara confirmar, escriba exactamente:\nconfirm {ip}\n\nCualquier otra entrada cancela la operación.",
        "block_success": "🚨 [ ACCIÓN COMPLETADA: IP BLOQUEADA ]\n\n'{ip}' se añadió a ai_ip_block.csv y se actualizó el feed del firewall.\n\n🌐 URL de integración:\n{url}",
        "block_failed": "❌ [ ACCIÓN FALLIDA ] El bloqueo de IP falló: {error}",
        "unblock_success": "🎉 [ ACCIÓN COMPLETADA: IP DESBLOQUEADA ]\n\n'{ip}' se eliminó de ai_ip_block.csv. El feed del firewall se regeneró.\n\n🌐 URL de integración:\n{url}",
        "unblock_failed": "❌ [ ACCIÓN FALLIDA ] El desbloqueo de IP falló: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: BÚSQUEDA BLOQUEADA ]\n\nEl SPL generado contiene una operación de escritura o con efectos secundarios y no se ejecutó. Solo se permiten búsquedas de solo lectura.\n\nRiesgo detectado: {issues}\n\nBúsqueda bloqueada:\n```spl\n{spl}\n```",
        "connection_failed": "Conexión fallida: {error}"
    },
    "it": {
        "prompt_missing": "Errore: richiesta mancante.", "provider_read": "Errore: impossibile leggere i provider AI.", "provider_none": "Errore: nessun provider AI configurato.",
        "auth_denied": "⛔ [ AUTORIZZAZIONE NEGATA: MODIFICA LISTA IP ]\n\nQuesta azione richiede la capability 'block_ip'. Contatta un amministratore SOC.",
        "invalid_unblock": "⛔ [ SBLOCCO IP RIFIUTATO ]\n\n'{ip}' non è un indirizzo IPv4 valido.", "lookup_failed": "❌ [ CONTROLLO FALLITO ] Impossibile leggere la blocklist IP: {error}", "not_found": "ℹ️ [ NESSUNA AZIONE RICHIESTA ]\n\n'{ip}' non è presente in ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ CONFERMA RICHIESTA: SBLOCCA IP ]\n\n'{ip}' verrà rimosso da ai_ip_block.csv e il feed firewall verrà aggiornato.\n\nPer confermare, inserisci esattamente:\nunconfirm {ip}\n\nQualsiasi altro valore annulla l'operazione.",
        "block_rejected": "⛔ [ BLOCCO IP RIFIUTATO ]\n\nImpossibile bloccare '{ip}': {reason}.", "block_not_allowed": "⚠️ [ BLOCCO IP NON CONSENTITO ]\n\n'{ip}' non può essere bloccato automaticamente: {reason}.\n\nNessuna azione eseguita.",
        "confirm_block": "🛑 [ CONFERMA RICHIESTA: BLOCCA IP ]\n\n'{ip}' verrà aggiunto alla blocklist permanente e il feed firewall verrà aggiornato.\n\nPer confermare, inserisci esattamente:\nconfirm {ip}\n\nQualsiasi altro valore annulla l'operazione.",
        "block_success": "🚨 [ AZIONE COMPLETATA: IP BLOCCATO ]\n\n'{ip}' è stato aggiunto a ai_ip_block.csv e il feed firewall è stato aggiornato.\n\n🌐 URL di integrazione:\n{url}", "block_failed": "❌ [ AZIONE FALLITA ] Blocco IP non riuscito: {error}",
        "unblock_success": "🎉 [ AZIONE COMPLETATA: IP SBLOCCATO ]\n\n'{ip}' è stato rimosso da ai_ip_block.csv. Il feed firewall è stato rigenerato.\n\n🌐 URL di integrazione:\n{url}", "unblock_failed": "❌ [ AZIONE FALLITA ] Sblocco IP non riuscito: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: RICERCA BLOCCATA ]\n\nL'SPL generato contiene un comando di scrittura o con effetti collaterali e non è stato eseguito. Sono consentite solo ricerche in sola lettura.\n\nRischio rilevato: {issues}\n\nRicerca bloccata:\n```spl\n{spl}\n```", "connection_failed": "Connessione fallita: {error}"
    },
    "pt": {
        "prompt_missing": "Erro: solicitação ausente.", "provider_read": "Erro: não foi possível ler os provedores de IA.", "provider_none": "Erro: nenhum provedor de IA configurado.",
        "auth_denied": "⛔ [ SEM PERMISSÃO: ALTERAÇÃO DA LISTA DE IP ]\n\nEsta ação requer a capacidade 'block_ip'. Contate um administrador SOC.",
        "invalid_unblock": "⛔ [ DESBLOQUEIO DE IP REJEITADO ]\n\n'{ip}' não é um endereço IPv4 válido.", "lookup_failed": "❌ [ VERIFICAÇÃO FALHOU ] Não foi possível ler a lista de bloqueio de IP: {error}", "not_found": "ℹ️ [ NENHUMA AÇÃO NECESSÁRIA ]\n\n'{ip}' não foi encontrado em ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ CONFIRMAÇÃO NECESSÁRIA: DESBLOQUEAR IP ]\n\n'{ip}' será removido de ai_ip_block.csv e o feed do firewall será atualizado.\n\nPara confirmar, digite exatamente:\nunconfirm {ip}\n\nQualquer outra entrada cancela a operação.",
        "block_rejected": "⛔ [ BLOQUEIO DE IP REJEITADO ]\n\n'{ip}' não pôde ser bloqueado: {reason}.", "block_not_allowed": "⚠️ [ BLOQUEIO DE IP NÃO PERMITIDO ]\n\n'{ip}' não pode ser bloqueado automaticamente: {reason}.\n\nNenhuma ação foi executada.",
        "confirm_block": "🛑 [ CONFIRMAÇÃO NECESSÁRIA: BLOQUEAR IP ]\n\n'{ip}' será adicionado à lista de bloqueio permanente e o feed do firewall será atualizado.\n\nPara confirmar, digite exatamente:\nconfirm {ip}\n\nQualquer outra entrada cancela a operação.",
        "block_success": "🚨 [ AÇÃO CONCLUÍDA: IP BLOQUEADO ]\n\n'{ip}' foi adicionado a ai_ip_block.csv e o feed do firewall foi atualizado.\n\n🌐 URL de integração:\n{url}", "block_failed": "❌ [ AÇÃO FALHOU ] O bloqueio de IP falhou: {error}",
        "unblock_success": "🎉 [ AÇÃO CONCLUÍDA: IP DESBLOQUEADO ]\n\n'{ip}' foi removido de ai_ip_block.csv. O feed do firewall foi regenerado.\n\n🌐 URL de integração:\n{url}", "unblock_failed": "❌ [ AÇÃO FALHOU ] O desbloqueio de IP falhou: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: PESQUISA BLOQUEADA ]\n\nO SPL gerado contém uma operação de escrita ou com efeito colateral e não foi executado. Somente pesquisas de leitura são permitidas.\n\nRisco detectado: {issues}\n\nPesquisa bloqueada:\n```spl\n{spl}\n```", "connection_failed": "Falha na conexão: {error}"
    },
    "nl": {
        "prompt_missing": "Fout: aanvraag ontbreekt.", "provider_read": "Fout: AI-providers konden niet worden gelezen.", "provider_none": "Fout: geen AI-provider geconfigureerd.",
        "auth_denied": "⛔ [ GEEN TOESTEMMING: IP-LIJST WIJZIGEN ]\n\nVoor deze actie is de capability 'block_ip' vereist. Neem contact op met een SOC-beheerder.",
        "invalid_unblock": "⛔ [ IP-DEBLOKKERING GEWEIGERD ]\n\n'{ip}' is geen geldig IPv4-adres.", "lookup_failed": "❌ [ CONTROLE MISLUKT ] De IP-blokkeerlijst kon niet worden gelezen: {error}", "not_found": "ℹ️ [ GEEN ACTIE NODIG ]\n\n'{ip}' is niet gevonden in ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ BEVESTIGING VEREIST: IP DEBLOKKEREN ]\n\n'{ip}' wordt verwijderd uit ai_ip_block.csv en de firewallfeed wordt vernieuwd.\n\nVoer ter bevestiging exact in:\nunconfirm {ip}\n\nElke andere invoer annuleert de actie.",
        "block_rejected": "⛔ [ IP-BLOKKERING GEWEIGERD ]\n\n'{ip}' kon niet worden geblokkeerd: {reason}.", "block_not_allowed": "⚠️ [ IP-BLOKKERING NIET TOEGESTAAN ]\n\n'{ip}' kan niet automatisch worden geblokkeerd: {reason}.\n\nEr is geen actie uitgevoerd.",
        "confirm_block": "🛑 [ BEVESTIGING VEREIST: IP BLOKKEREN ]\n\n'{ip}' wordt toegevoegd aan de permanente blokkeerlijst en de firewallfeed wordt vernieuwd.\n\nVoer ter bevestiging exact in:\nconfirm {ip}\n\nElke andere invoer annuleert de actie.",
        "block_success": "🚨 [ ACTIE VOLTOOID: IP GEBLOKKEERD ]\n\n'{ip}' is toegevoegd aan ai_ip_block.csv en de firewallfeed is vernieuwd.\n\n🌐 Integratie-URL:\n{url}", "block_failed": "❌ [ ACTIE MISLUKT ] IP-blokkering mislukt: {error}",
        "unblock_success": "🎉 [ ACTIE VOLTOOID: IP GEDEBLOKKEERD ]\n\n'{ip}' is verwijderd uit ai_ip_block.csv. De firewallfeed is opnieuw opgebouwd.\n\n🌐 Integratie-URL:\n{url}", "unblock_failed": "❌ [ ACTIE MISLUKT ] IP-deblokkering mislukt: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: ZOEKOPDRACHT GEBLOKKEERD ]\n\nDe gegenereerde SPL bevat een schrijfopdracht of neveneffect en is niet uitgevoerd. Alleen read-only zoekopdrachten zijn toegestaan.\n\nGedetecteerd risico: {issues}\n\nGeblokkeerde zoekopdracht:\n```spl\n{spl}\n```", "connection_failed": "Verbinding mislukt: {error}"
    },
    "pl": {
        "prompt_missing": "Błąd: brak zapytania.", "provider_read": "Błąd: nie można odczytać dostawców AI.", "provider_none": "Błąd: nie skonfigurowano dostawcy AI.",
        "auth_denied": "⛔ [ BRAK UPRAWNIEŃ: ZMIANA LISTY IP ]\n\nTa akcja wymaga uprawnienia 'block_ip'. Skontaktuj się z administratorem SOC.",
        "invalid_unblock": "⛔ [ ODBLOKOWANIE IP ODRZUCONE ]\n\n'{ip}' nie jest prawidłowym adresem IPv4.", "lookup_failed": "❌ [ KONTROLA NIEUDANA ] Nie można odczytać listy blokowanych IP: {error}", "not_found": "ℹ️ [ BRAK WYMAGANEJ AKCJI ]\n\nNie znaleziono '{ip}' w ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ WYMAGANE POTWIERDZENIE: ODBLOKUJ IP ]\n\n'{ip}' zostanie usunięty z ai_ip_block.csv, a feed firewalla zostanie odświeżony.\n\nAby potwierdzić, wpisz dokładnie:\nunconfirm {ip}\n\nInna wartość anuluje operację.",
        "block_rejected": "⛔ [ BLOKADA IP ODRZUCONA ]\n\nNie można zablokować '{ip}': {reason}.", "block_not_allowed": "⚠️ [ BLOKADA IP NIEDOZWOLONA ]\n\n'{ip}' nie może zostać zablokowany automatycznie: {reason}.\n\nNie wykonano żadnej akcji.",
        "confirm_block": "🛑 [ WYMAGANE POTWIERDZENIE: ZABLOKUJ IP ]\n\n'{ip}' zostanie dodany do stałej listy blokad, a feed firewalla zostanie odświeżony.\n\nAby potwierdzić, wpisz dokładnie:\nconfirm {ip}\n\nInna wartość anuluje operację.",
        "block_success": "🚨 [ AKCJA ZAKOŃCZONA: IP ZABLOKOWANE ]\n\n'{ip}' dodano do ai_ip_block.csv i odświeżono feed firewalla.\n\n🌐 URL integracji:\n{url}", "block_failed": "❌ [ AKCJA NIEUDANA ] Blokowanie IP nie powiodło się: {error}",
        "unblock_success": "🎉 [ AKCJA ZAKOŃCZONA: IP ODBLOKOWANE ]\n\n'{ip}' usunięto z ai_ip_block.csv. Feed firewalla został przebudowany.\n\n🌐 URL integracji:\n{url}", "unblock_failed": "❌ [ AKCJA NIEUDANA ] Odblokowanie IP nie powiodło się: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: WYSZUKIWANIE ZABLOKOWANE ]\n\nWygenerowany SPL zawiera operację zapisu lub efekt uboczny i nie został uruchomiony. Dozwolone są tylko wyszukiwania tylko do odczytu.\n\nWykryte ryzyko: {issues}\n\nZablokowane wyszukiwanie:\n```spl\n{spl}\n```", "connection_failed": "Połączenie nie powiodło się: {error}"
    },
    "ru": {
        "prompt_missing": "Ошибка: запрос отсутствует.", "provider_read": "Ошибка: не удалось прочитать провайдеры ИИ.", "provider_none": "Ошибка: провайдер ИИ не настроен.",
        "auth_denied": "⛔ [ НЕТ ПРАВ: ИЗМЕНЕНИЕ СПИСКА IP ]\n\nДля этого действия требуется capability 'block_ip'. Обратитесь к администратору SOC.",
        "invalid_unblock": "⛔ [ РАЗБЛОКИРОВКА IP ОТКЛОНЕНА ]\n\n'{ip}' не является корректным IPv4-адресом.", "lookup_failed": "❌ [ ПРОВЕРКА НЕ УДАЛАСЬ ] Не удалось прочитать список блокировки IP: {error}", "not_found": "ℹ️ [ ДЕЙСТВИЕ НЕ ТРЕБУЕТСЯ ]\n\n'{ip}' не найден в ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ: РАЗБЛОКИРОВАТЬ IP ]\n\n'{ip}' будет удалён из ai_ip_block.csv, а firewall feed будет обновлён.\n\nДля подтверждения введите точно:\nunconfirm {ip}\n\nЛюбой другой ввод отменит операцию.",
        "block_rejected": "⛔ [ БЛОКИРОВКА IP ОТКЛОНЕНА ]\n\nНе удалось заблокировать '{ip}': {reason}.", "block_not_allowed": "⚠️ [ БЛОКИРОВКА IP НЕ РАЗРЕШЕНА ]\n\n'{ip}' нельзя заблокировать автоматически: {reason}.\n\nДействие не выполнялось.",
        "confirm_block": "🛑 [ ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ: ЗАБЛОКИРОВАТЬ IP ]\n\n'{ip}' будет добавлен в постоянный список блокировки, а firewall feed будет обновлён.\n\nДля подтверждения введите точно:\nconfirm {ip}\n\nЛюбой другой ввод отменит операцию.",
        "block_success": "🚨 [ ДЕЙСТВИЕ ЗАВЕРШЕНО: IP ЗАБЛОКИРОВАН ]\n\n'{ip}' добавлен в ai_ip_block.csv, firewall feed обновлён.\n\n🌐 URL интеграции:\n{url}", "block_failed": "❌ [ ОШИБКА ДЕЙСТВИЯ ] Не удалось заблокировать IP: {error}",
        "unblock_success": "🎉 [ ДЕЙСТВИЕ ЗАВЕРШЕНО: IP РАЗБЛОКИРОВАН ]\n\n'{ip}' удалён из ai_ip_block.csv. Firewall feed перестроен.\n\n🌐 URL интеграции:\n{url}", "unblock_failed": "❌ [ ОШИБКА ДЕЙСТВИЯ ] Не удалось разблокировать IP: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: ПОИСК ЗАБЛОКИРОВАН ]\n\nСгенерированный SPL содержит операцию записи или побочный эффект и не был выполнен. Разрешены только поиски в режиме чтения.\n\nОбнаруженный риск: {issues}\n\nЗаблокированный поиск:\n```spl\n{spl}\n```", "connection_failed": "Ошибка подключения: {error}"
    },
    "ar": {
        "prompt_missing": "خطأ: الطلب مفقود.", "provider_read": "خطأ: تعذر قراءة موفري الذكاء الاصطناعي.", "provider_none": "خطأ: لم يتم تكوين أي موفر ذكاء اصطناعي.",
        "auth_denied": "⛔ [ لا توجد صلاحية: تعديل قائمة IP ]\n\nيتطلب هذا الإجراء صلاحية 'block_ip'. تواصل مع مسؤول SOC.",
        "invalid_unblock": "⛔ [ تم رفض إلغاء حظر IP ]\n\n'{ip}' ليس عنوان IPv4 صالحًا.", "lookup_failed": "❌ [ فشل التحقق ] تعذرت قراءة قائمة حظر IP: {error}", "not_found": "ℹ️ [ لا يلزم إجراء ]\n\nلم يتم العثور على '{ip}' في ai_ip_block.csv.",
        "confirm_unblock": "🛑 [ تأكيد مطلوب: إلغاء حظر IP ]\n\nستتم إزالة '{ip}' من ai_ip_block.csv وسيتم تحديث تغذية الجدار الناري.\n\nللتأكيد أدخل بالضبط:\nunconfirm {ip}\n\nأي إدخال آخر يلغي العملية.",
        "block_rejected": "⛔ [ تم رفض حظر IP ]\n\nتعذر حظر '{ip}': {reason}.", "block_not_allowed": "⚠️ [ حظر IP غير مسموح ]\n\nلا يمكن حظر '{ip}' تلقائيًا: {reason}.\n\nلم يتم تنفيذ أي إجراء.",
        "confirm_block": "🛑 [ تأكيد مطلوب: حظر IP ]\n\nستتم إضافة '{ip}' إلى قائمة الحظر الدائمة وسيتم تحديث تغذية الجدار الناري.\n\nللتأكيد أدخل بالضبط:\nconfirm {ip}\n\nأي إدخال آخر يلغي العملية.",
        "block_success": "🚨 [ اكتمل الإجراء: تم حظر IP ]\n\nتمت إضافة '{ip}' إلى ai_ip_block.csv وتحديث تغذية الجدار الناري.\n\n🌐 رابط التكامل:\n{url}", "block_failed": "❌ [ فشل الإجراء ] فشل حظر IP: {error}",
        "unblock_success": "🎉 [ اكتمل الإجراء: تم إلغاء حظر IP ]\n\nتمت إزالة '{ip}' من ai_ip_block.csv وإعادة إنشاء تغذية الجدار الناري.\n\n🌐 رابط التكامل:\n{url}", "unblock_failed": "❌ [ فشل الإجراء ] فشل إلغاء حظر IP: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: تم حظر البحث ]\n\nيحتوي SPL الناتج على أمر كتابة أو تأثير جانبي ولم يتم تنفيذه. يُسمح فقط بعمليات البحث للقراءة فقط.\n\nالمخاطر المكتشفة: {issues}\n\nالبحث المحظور:\n```spl\n{spl}\n```", "connection_failed": "فشل الاتصال: {error}"
    },
    "ja": {
        "prompt_missing": "エラー: リクエストがありません。", "provider_read": "エラー: AIプロバイダーを読み取れませんでした。", "provider_none": "エラー: AIプロバイダーが設定されていません。",
        "auth_denied": "⛔ [ 権限がありません: IPリスト変更 ]\n\nこの操作には 'block_ip' capability が必要です。SOC管理者に連絡してください。",
        "invalid_unblock": "⛔ [ IPブロック解除を拒否 ]\n\n'{ip}' は有効なIPv4アドレスではありません。", "lookup_failed": "❌ [ 確認失敗 ] IPブロックリストを読み取れませんでした: {error}", "not_found": "ℹ️ [ 操作不要 ]\n\n'{ip}' は ai_ip_block.csv にありません。",
        "confirm_unblock": "🛑 [ 確認が必要: IPブロック解除 ]\n\n'{ip}' を ai_ip_block.csv から削除し、ファイアウォールフィードを更新します。\n\n確認するには次を正確に入力してください:\nunconfirm {ip}\n\nそれ以外の入力はキャンセルになります。",
        "block_rejected": "⛔ [ IPブロックを拒否 ]\n\n'{ip}' をブロックできませんでした: {reason}。", "block_not_allowed": "⚠️ [ IPブロックは許可されていません ]\n\n'{ip}' は自動ブロックできません: {reason}。\n\n操作は実行されませんでした。",
        "confirm_block": "🛑 [ 確認が必要: IPをブロック ]\n\n'{ip}' を恒久ブロックリストに追加し、ファイアウォールフィードを更新します。\n\n確認するには次を正確に入力してください:\nconfirm {ip}\n\nそれ以外の入力はキャンセルになります。",
        "block_success": "🚨 [ 操作完了: IPをブロックしました ]\n\n'{ip}' を ai_ip_block.csv に追加し、ファイアウォールフィードを更新しました。\n\n🌐 統合URL:\n{url}", "block_failed": "❌ [ 操作失敗 ] IPブロックに失敗しました: {error}",
        "unblock_success": "🎉 [ 操作完了: IPブロックを解除しました ]\n\n'{ip}' を ai_ip_block.csv から削除し、ファイアウォールフィードを再生成しました。\n\n🌐 統合URL:\n{url}", "unblock_failed": "❌ [ 操作失敗 ] IPブロック解除に失敗しました: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: 検索をブロック ]\n\n生成されたSPLには書き込みまたは副作用を伴うコマンドが含まれるため実行されませんでした。読み取り専用検索のみ許可されます。\n\n検出されたリスク: {issues}\n\nブロックされた検索:\n```spl\n{spl}\n```", "connection_failed": "接続に失敗しました: {error}"
    },
    "ko": {
        "prompt_missing": "오류: 요청이 없습니다.", "provider_read": "오류: AI 공급자를 읽을 수 없습니다.", "provider_none": "오류: 구성된 AI 공급자가 없습니다.",
        "auth_denied": "⛔ [ 권한 없음: IP 목록 변경 ]\n\n이 작업에는 'block_ip' capability가 필요합니다. SOC 관리자에게 문의하세요.",
        "invalid_unblock": "⛔ [ IP 차단 해제 거부 ]\n\n'{ip}'는 유효한 IPv4 주소가 아닙니다.", "lookup_failed": "❌ [ 확인 실패 ] IP 차단 목록을 읽을 수 없습니다: {error}", "not_found": "ℹ️ [ 작업 불필요 ]\n\n'{ip}'가 ai_ip_block.csv에 없습니다.",
        "confirm_unblock": "🛑 [ 확인 필요: IP 차단 해제 ]\n\n'{ip}'를 ai_ip_block.csv에서 제거하고 방화벽 피드를 갱신합니다.\n\n확인하려면 정확히 입력하세요:\nunconfirm {ip}\n\n다른 입력은 작업을 취소합니다.",
        "block_rejected": "⛔ [ IP 차단 거부 ]\n\n'{ip}'를 차단할 수 없습니다: {reason}.", "block_not_allowed": "⚠️ [ IP 차단 허용 안 됨 ]\n\n'{ip}'는 자동 차단할 수 없습니다: {reason}.\n\n작업이 수행되지 않았습니다.",
        "confirm_block": "🛑 [ 확인 필요: IP 차단 ]\n\n'{ip}'를 영구 차단 목록에 추가하고 방화벽 피드를 갱신합니다.\n\n확인하려면 정확히 입력하세요:\nconfirm {ip}\n\n다른 입력은 작업을 취소합니다.",
        "block_success": "🚨 [ 작업 완료: IP 차단됨 ]\n\n'{ip}'를 ai_ip_block.csv에 추가하고 방화벽 피드를 갱신했습니다.\n\n🌐 통합 URL:\n{url}", "block_failed": "❌ [ 작업 실패 ] IP 차단에 실패했습니다: {error}",
        "unblock_success": "🎉 [ 작업 완료: IP 차단 해제됨 ]\n\n'{ip}'를 ai_ip_block.csv에서 제거하고 방화벽 피드를 다시 생성했습니다.\n\n🌐 통합 URL:\n{url}", "unblock_failed": "❌ [ 작업 실패 ] IP 차단 해제에 실패했습니다: {error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL: 검색 차단됨 ]\n\n생성된 SPL에 쓰기 또는 부작용 명령이 포함되어 실행되지 않았습니다. 읽기 전용 검색만 허용됩니다.\n\n탐지된 위험: {issues}\n\n차단된 검색:\n```spl\n{spl}\n```", "connection_failed": "연결 실패: {error}"
    },
    "zh": {
        "prompt_missing": "错误：缺少请求。", "provider_read": "错误：无法读取 AI 提供商。", "provider_none": "错误：未配置 AI 提供商。",
        "auth_denied": "⛔ [ 无权限：修改 IP 列表 ]\n\n此操作需要 'block_ip' capability。请联系 SOC 管理员。",
        "invalid_unblock": "⛔ [ IP 解封被拒绝 ]\n\n'{ip}' 不是有效的 IPv4 地址。", "lookup_failed": "❌ [ 检查失败 ] 无法读取 IP 阻止列表：{error}", "not_found": "ℹ️ [ 无需操作 ]\n\n在 ai_ip_block.csv 中未找到 '{ip}'。",
        "confirm_unblock": "🛑 [ 需要确认：解除 IP 阻止 ]\n\n将从 ai_ip_block.csv 中移除 '{ip}' 并刷新防火墙 feed。\n\n确认请输入：\nunconfirm {ip}\n\n输入其他内容将取消操作。",
        "block_rejected": "⛔ [ IP 阻止被拒绝 ]\n\n无法阻止 '{ip}'：{reason}。", "block_not_allowed": "⚠️ [ 不允许阻止 IP ]\n\n无法自动阻止 '{ip}'：{reason}。\n\n未执行任何操作。",
        "confirm_block": "🛑 [ 需要确认：阻止 IP ]\n\n将把 '{ip}' 加入永久阻止列表并刷新防火墙 feed。\n\n确认请输入：\nconfirm {ip}\n\n输入其他内容将取消操作。",
        "block_success": "🚨 [ 操作完成：IP 已阻止 ]\n\n已将 '{ip}' 添加到 ai_ip_block.csv 并刷新防火墙 feed。\n\n🌐 集成 URL：\n{url}", "block_failed": "❌ [ 操作失败 ] IP 阻止失败：{error}",
        "unblock_success": "🎉 [ 操作完成：IP 已解封 ]\n\n已从 ai_ip_block.csv 中移除 '{ip}' 并重新生成防火墙 feed。\n\n🌐 集成 URL：\n{url}", "unblock_failed": "❌ [ 操作失败 ] IP 解封失败：{error}",
        "guardrail_blocked": "🛡️ [ GUARDRAIL：搜索已阻止 ]\n\n生成的 SPL 包含写入或副作用命令，因此未执行。仅允许只读搜索。\n\n检测到的风险：{issues}\n\n被阻止的搜索：\n```spl\n{spl}\n```", "connection_failed": "连接失败：{error}"
    }
}

_BACKEND_MESSAGES["en"].setdefault("guard_invalid_ip", "invalid IPv4 address (each octet must be between 0 and 255)")
_BACKEND_MESSAGES["en"].setdefault("guard_self_block", "the Splunk server address is protected from self-blocking")
_BACKEND_MESSAGES["en"].setdefault("guard_protected", "protected or private range ({cidr})")
_BACKEND_MESSAGES["en"].setdefault("guard_allowlisted", "allowlisted range ({cidr})")
_BACKEND_MESSAGES["tr"].update({"guard_invalid_ip": "geçersiz IPv4 adresi (her oktet 0 ile 255 arasında olmalıdır)", "guard_self_block": "Splunk sunucusunun kendi adresi engellemeye karşı korunuyor", "guard_protected": "korumalı veya özel ağ aralığı ({cidr})", "guard_allowlisted": "izin listesinde bulunan ağ aralığı ({cidr})"})
_BACKEND_MESSAGES["de"].update({"guard_invalid_ip": "ungültige IPv4-Adresse", "guard_self_block": "die Splunk-Serveradresse ist vor Selbstsperrung geschützt", "guard_protected": "geschützter oder privater Bereich ({cidr})", "guard_allowlisted": "freigegebener Bereich ({cidr})"})
_BACKEND_MESSAGES["fr"].update({"guard_invalid_ip": "adresse IPv4 invalide", "guard_self_block": "l'adresse du serveur Splunk est protégée contre l'auto-blocage", "guard_protected": "plage protégée ou privée ({cidr})", "guard_allowlisted": "plage autorisée ({cidr})"})
_BACKEND_MESSAGES["es"].update({"guard_invalid_ip": "dirección IPv4 no válida", "guard_self_block": "la dirección del servidor Splunk está protegida contra autobloqueo", "guard_protected": "rango protegido o privado ({cidr})", "guard_allowlisted": "rango permitido ({cidr})"})
_BACKEND_MESSAGES["it"].update({"guard_invalid_ip": "indirizzo IPv4 non valido", "guard_self_block": "l'indirizzo del server Splunk è protetto dall'auto-blocco", "guard_protected": "intervallo protetto o privato ({cidr})", "guard_allowlisted": "intervallo consentito ({cidr})"})
_BACKEND_MESSAGES["pt"].update({"guard_invalid_ip": "endereço IPv4 inválido", "guard_self_block": "o endereço do servidor Splunk é protegido contra autobloqueio", "guard_protected": "faixa protegida ou privada ({cidr})", "guard_allowlisted": "faixa permitida ({cidr})"})
_BACKEND_MESSAGES["nl"].update({"guard_invalid_ip": "ongeldig IPv4-adres", "guard_self_block": "het Splunk-serveradres is beschermd tegen zelfblokkering", "guard_protected": "beschermd of privébereik ({cidr})", "guard_allowlisted": "toegestaan bereik ({cidr})"})
_BACKEND_MESSAGES["pl"].update({"guard_invalid_ip": "nieprawidłowy adres IPv4", "guard_self_block": "adres serwera Splunk jest chroniony przed samoblokadą", "guard_protected": "chroniony lub prywatny zakres ({cidr})", "guard_allowlisted": "dozwolony zakres ({cidr})"})
_BACKEND_MESSAGES["ru"].update({"guard_invalid_ip": "некорректный IPv4-адрес", "guard_self_block": "адрес сервера Splunk защищён от самоблокировки", "guard_protected": "защищённый или частный диапазон ({cidr})", "guard_allowlisted": "разрешённый диапазон ({cidr})"})
_BACKEND_MESSAGES["ar"].update({"guard_invalid_ip": "عنوان IPv4 غير صالح", "guard_self_block": "عنوان خادم Splunk محمي من الحظر الذاتي", "guard_protected": "نطاق محمي أو خاص ({cidr})", "guard_allowlisted": "نطاق مسموح ({cidr})"})
_BACKEND_MESSAGES["ja"].update({"guard_invalid_ip": "無効なIPv4アドレス", "guard_self_block": "Splunkサーバー自身のアドレスは自己ブロックから保護されています", "guard_protected": "保護またはプライベート範囲 ({cidr})", "guard_allowlisted": "許可リスト範囲 ({cidr})"})
_BACKEND_MESSAGES["ko"].update({"guard_invalid_ip": "유효하지 않은 IPv4 주소", "guard_self_block": "Splunk 서버 주소는 자체 차단으로부터 보호됩니다", "guard_protected": "보호 또는 사설 범위 ({cidr})", "guard_allowlisted": "허용 목록 범위 ({cidr})"})
_BACKEND_MESSAGES["zh"].update({"guard_invalid_ip": "无效的 IPv4 地址", "guard_self_block": "Splunk 服务器地址受保护，不能自我阻止", "guard_protected": "受保护或私有网段 ({cidr})", "guard_allowlisted": "允许列表网段 ({cidr})"})


_BACKEND_MESSAGES["en"].update({
    "lookup_remove_failed": "The IP could not be removed from the lookup.",
    "export_script_missing": "export_blocked_ips.sh was not found.",
    "export_failed": "TXT export failed: {detail}",
    "txt_verify_failed": "The IP was removed from the lookup but is still present in ai_ip_block.txt.",
    "parsing_error": "Parsing error: No valid response format was found.",
    "openai_error": "[OpenAI error: {detail}]",
    "gemini_empty": "[Gemini returned an empty response. finishReason={reason}]",
    "gemini_no_response": "[Gemini returned no response. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM error: {detail}]",
    "http_error": "HTTP Error {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail note:* the search references a sensitive field name ({issues}). Review the result accordingly.",
    "agentic_search_info": "Agentic Search Info"
})
_BACKEND_MESSAGES["tr"].update({
    "lookup_remove_failed": "IP lookup listesinden kaldırılamadı.",
    "export_script_missing": "export_blocked_ips.sh bulunamadı.",
    "export_failed": "TXT dışa aktarma başarısız: {detail}",
    "txt_verify_failed": "IP lookup listesinden kaldırıldı ancak ai_ip_block.txt içinde hâlâ bulunuyor.",
    "parsing_error": "Ayrıştırma hatası: Geçerli bir yanıt biçimi bulunamadı.",
    "openai_error": "[OpenAI hatası: {detail}]",
    "gemini_empty": "[Gemini boş yanıt döndürdü. finishReason={reason}]",
    "gemini_no_response": "[Gemini yanıt döndürmedi. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM hatası: {detail}]",
    "http_error": "HTTP Hatası {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail notu:* arama hassas bir alan adına referans veriyor ({issues}). Çıktıyı buna göre değerlendirin.",
    "agentic_search_info": "Agentic Arama Bilgisi"
})
_BACKEND_MESSAGES["de"].update({
    "lookup_remove_failed": "Die IP konnte nicht aus dem Lookup entfernt werden.",
    "export_script_missing": "export_blocked_ips.sh wurde nicht gefunden.",
    "export_failed": "TXT-Export fehlgeschlagen: {detail}",
    "txt_verify_failed": "Die IP wurde aus dem Lookup entfernt, ist aber weiterhin in ai_ip_block.txt vorhanden.",
    "parsing_error": "Analysefehler: Kein gültiges Antwortformat gefunden.",
    "openai_error": "[OpenAI-Fehler: {detail}]",
    "gemini_empty": "[Gemini hat eine leere Antwort zurückgegeben. finishReason={reason}]",
    "gemini_no_response": "[Gemini hat keine Antwort zurückgegeben. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM-Fehler: {detail}]",
    "http_error": "HTTP-Fehler {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail-Hinweis:* Die Suche verweist auf einen sensiblen Feldnamen ({issues}). Prüfen Sie das Ergebnis entsprechend.",
    "agentic_search_info": "Agentic-Suchinformationen"
})
_BACKEND_MESSAGES["fr"].update({
    "lookup_remove_failed": "L'adresse IP n'a pas pu être supprimée du lookup.",
    "export_script_missing": "export_blocked_ips.sh est introuvable.",
    "export_failed": "Échec de l'export TXT : {detail}",
    "txt_verify_failed": "L'adresse IP a été supprimée du lookup mais est toujours présente dans ai_ip_block.txt.",
    "parsing_error": "Erreur d'analyse : aucun format de réponse valide n'a été trouvé.",
    "openai_error": "[Erreur OpenAI : {detail}]",
    "gemini_empty": "[Gemini a renvoyé une réponse vide. finishReason={reason}]",
    "gemini_no_response": "[Gemini n'a renvoyé aucune réponse. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code} : {detail}]",
    "llm_error": "[Erreur LLM : {detail}]",
    "http_error": "Erreur HTTP {code} : {detail}",
    "guardrail_caution": "⚠️ *Note Guardrail :* la recherche référence un nom de champ sensible ({issues}). Vérifiez le résultat en conséquence.",
    "agentic_search_info": "Informations de recherche agentique"
})
_BACKEND_MESSAGES["es"].update({
    "lookup_remove_failed": "No se pudo eliminar la IP del lookup.",
    "export_script_missing": "No se encontró export_blocked_ips.sh.",
    "export_failed": "La exportación TXT falló: {detail}",
    "txt_verify_failed": "La IP se eliminó del lookup, pero todavía aparece en ai_ip_block.txt.",
    "parsing_error": "Error de análisis: no se encontró un formato de respuesta válido.",
    "openai_error": "[Error de OpenAI: {detail}]",
    "gemini_empty": "[Gemini devolvió una respuesta vacía. finishReason={reason}]",
    "gemini_no_response": "[Gemini no devolvió respuesta. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[Error de LLM: {detail}]",
    "http_error": "Error HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *Nota de Guardrail:* la búsqueda hace referencia a un nombre de campo sensible ({issues}). Revise el resultado en consecuencia.",
    "agentic_search_info": "Información de búsqueda agéntica"
})
_BACKEND_MESSAGES["it"].update({
    "lookup_remove_failed": "Impossibile rimuovere l'IP dal lookup.",
    "export_script_missing": "export_blocked_ips.sh non è stato trovato.",
    "export_failed": "Esportazione TXT non riuscita: {detail}",
    "txt_verify_failed": "L'IP è stato rimosso dal lookup ma è ancora presente in ai_ip_block.txt.",
    "parsing_error": "Errore di parsing: nessun formato di risposta valido trovato.",
    "openai_error": "[Errore OpenAI: {detail}]",
    "gemini_empty": "[Gemini ha restituito una risposta vuota. finishReason={reason}]",
    "gemini_no_response": "[Gemini non ha restituito alcuna risposta. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[Errore LLM: {detail}]",
    "http_error": "Errore HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *Nota Guardrail:* la ricerca fa riferimento a un nome campo sensibile ({issues}). Valuta il risultato di conseguenza.",
    "agentic_search_info": "Informazioni ricerca agentica"
})
_BACKEND_MESSAGES["pt"].update({
    "lookup_remove_failed": "Não foi possível remover o IP do lookup.",
    "export_script_missing": "export_blocked_ips.sh não foi encontrado.",
    "export_failed": "Falha na exportação TXT: {detail}",
    "txt_verify_failed": "O IP foi removido do lookup, mas ainda está presente em ai_ip_block.txt.",
    "parsing_error": "Erro de análise: nenhum formato de resposta válido foi encontrado.",
    "openai_error": "[Erro do OpenAI: {detail}]",
    "gemini_empty": "[Gemini retornou uma resposta vazia. finishReason={reason}]",
    "gemini_no_response": "[Gemini não retornou resposta. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[Erro de LLM: {detail}]",
    "http_error": "Erro HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *Nota do Guardrail:* a pesquisa faz referência a um nome de campo sensível ({issues}). Revise o resultado de acordo.",
    "agentic_search_info": "Informações da pesquisa agêntica"
})
_BACKEND_MESSAGES["nl"].update({
    "lookup_remove_failed": "Het IP-adres kon niet uit de lookup worden verwijderd.",
    "export_script_missing": "export_blocked_ips.sh is niet gevonden.",
    "export_failed": "TXT-export mislukt: {detail}",
    "txt_verify_failed": "Het IP-adres is uit de lookup verwijderd maar staat nog in ai_ip_block.txt.",
    "parsing_error": "Parsefout: er is geen geldig antwoordformaat gevonden.",
    "openai_error": "[OpenAI-fout: {detail}]",
    "gemini_empty": "[Gemini gaf een leeg antwoord terug. finishReason={reason}]",
    "gemini_no_response": "[Gemini gaf geen antwoord terug. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM-fout: {detail}]",
    "http_error": "HTTP-fout {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail-opmerking:* de zoekopdracht verwijst naar een gevoelige veldnaam ({issues}). Beoordeel het resultaat dienovereenkomstig.",
    "agentic_search_info": "Agentic-zoekinformatie"
})
_BACKEND_MESSAGES["pl"].update({
    "lookup_remove_failed": "Nie udało się usunąć adresu IP z lookup.",
    "export_script_missing": "Nie znaleziono export_blocked_ips.sh.",
    "export_failed": "Eksport TXT nie powiódł się: {detail}",
    "txt_verify_failed": "Adres IP usunięto z lookup, ale nadal znajduje się w ai_ip_block.txt.",
    "parsing_error": "Błąd parsowania: nie znaleziono prawidłowego formatu odpowiedzi.",
    "openai_error": "[Błąd OpenAI: {detail}]",
    "gemini_empty": "[Gemini zwrócił pustą odpowiedź. finishReason={reason}]",
    "gemini_no_response": "[Gemini nie zwrócił odpowiedzi. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[Błąd LLM: {detail}]",
    "http_error": "Błąd HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *Uwaga Guardrail:* wyszukiwanie odwołuje się do wrażliwej nazwy pola ({issues}). Oceń wynik z uwzględnieniem tego kontekstu.",
    "agentic_search_info": "Informacje wyszukiwania agentowego"
})
_BACKEND_MESSAGES["ru"].update({
    "lookup_remove_failed": "Не удалось удалить IP-адрес из lookup.",
    "export_script_missing": "Файл export_blocked_ips.sh не найден.",
    "export_failed": "Ошибка экспорта TXT: {detail}",
    "txt_verify_failed": "IP-адрес удалён из lookup, но всё ещё присутствует в ai_ip_block.txt.",
    "parsing_error": "Ошибка разбора: допустимый формат ответа не найден.",
    "openai_error": "[Ошибка OpenAI: {detail}]",
    "gemini_empty": "[Gemini вернул пустой ответ. finishReason={reason}]",
    "gemini_no_response": "[Gemini не вернул ответ. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[Ошибка LLM: {detail}]",
    "http_error": "Ошибка HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *Примечание Guardrail:* поиск ссылается на чувствительное имя поля ({issues}). Учитывайте это при оценке результата.",
    "agentic_search_info": "Информация об агентном поиске"
})
_BACKEND_MESSAGES["ar"].update({
    "lookup_remove_failed": "تعذر إزالة عنوان IP من lookup.",
    "export_script_missing": "لم يتم العثور على export_blocked_ips.sh.",
    "export_failed": "فشل تصدير TXT: {detail}",
    "txt_verify_failed": "تمت إزالة عنوان IP من lookup لكنه لا يزال موجودًا في ai_ip_block.txt.",
    "parsing_error": "خطأ في التحليل: لم يتم العثور على تنسيق استجابة صالح.",
    "openai_error": "[خطأ OpenAI: {detail}]",
    "gemini_empty": "[أعاد Gemini استجابة فارغة. finishReason={reason}]",
    "gemini_no_response": "[لم يُعد Gemini استجابة. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[خطأ LLM: {detail}]",
    "http_error": "خطأ HTTP {code}: {detail}",
    "guardrail_caution": "⚠️ *ملاحظة Guardrail:* يشير البحث إلى اسم حقل حساس ({issues}). راجع النتيجة وفقًا لذلك.",
    "agentic_search_info": "معلومات البحث الوكيلي"
})
_BACKEND_MESSAGES["ja"].update({
    "lookup_remove_failed": "lookup から IP を削除できませんでした。",
    "export_script_missing": "export_blocked_ips.sh が見つかりません。",
    "export_failed": "TXT エクスポートに失敗しました: {detail}",
    "txt_verify_failed": "IP は lookup から削除されましたが、ai_ip_block.txt にまだ存在します。",
    "parsing_error": "解析エラー: 有効な応答形式が見つかりませんでした。",
    "openai_error": "[OpenAI エラー: {detail}]",
    "gemini_empty": "[Gemini が空の応答を返しました。finishReason={reason}]",
    "gemini_no_response": "[Gemini から応答がありません。blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM エラー: {detail}]",
    "http_error": "HTTP エラー {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail 注記:* 検索が機密フィールド名 ({issues}) を参照しています。結果をその点を考慮して確認してください。",
    "agentic_search_info": "エージェント検索情報"
})
_BACKEND_MESSAGES["ko"].update({
    "lookup_remove_failed": "lookup에서 IP를 제거할 수 없습니다.",
    "export_script_missing": "export_blocked_ips.sh를 찾을 수 없습니다.",
    "export_failed": "TXT 내보내기 실패: {detail}",
    "txt_verify_failed": "IP가 lookup에서 제거되었지만 ai_ip_block.txt에 여전히 존재합니다.",
    "parsing_error": "구문 분석 오류: 유효한 응답 형식을 찾을 수 없습니다.",
    "openai_error": "[OpenAI 오류: {detail}]",
    "gemini_empty": "[Gemini가 빈 응답을 반환했습니다. finishReason={reason}]",
    "gemini_no_response": "[Gemini가 응답을 반환하지 않았습니다. blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}: {detail}]",
    "llm_error": "[LLM 오류: {detail}]",
    "http_error": "HTTP 오류 {code}: {detail}",
    "guardrail_caution": "⚠️ *Guardrail 참고:* 검색이 민감한 필드 이름 ({issues})을 참조합니다. 이를 고려하여 결과를 검토하세요.",
    "agentic_search_info": "에이전트 검색 정보"
})
_BACKEND_MESSAGES["zh"].update({
    "lookup_remove_failed": "无法从 lookup 中删除该 IP。",
    "export_script_missing": "未找到 export_blocked_ips.sh。",
    "export_failed": "TXT 导出失败：{detail}",
    "txt_verify_failed": "该 IP 已从 lookup 中删除，但仍存在于 ai_ip_block.txt 中。",
    "parsing_error": "解析错误：未找到有效的响应格式。",
    "openai_error": "[OpenAI 错误：{detail}]",
    "gemini_empty": "[Gemini 返回了空响应。finishReason={reason}]",
    "gemini_no_response": "[Gemini 未返回响应。blockReason={reason}]",
    "llm_http_error": "[LLM HTTP {code}：{detail}]",
    "llm_error": "[LLM 错误：{detail}]",
    "http_error": "HTTP 错误 {code}：{detail}",
    "guardrail_caution": "⚠️ *Guardrail 提示：* 搜索引用了敏感字段名称 ({issues})。请据此审查结果。",
    "agentic_search_info": "代理式搜索信息"
})


def _ipv4_to_int(ip):
    o = ip.split('.')
    return (int(o[0]) << 24) | (int(o[1]) << 16) | (int(o[2]) << 8) | int(o[3])


def _valid_ipv4(ip):
    o = ip.split('.')
    if len(o) != 4:
        return False
    for p in o:
        if not p.isdigit() or int(p) > 255:
            return False
    return True


def _in_cidr(ip_int, cidr):
    try:
        net, bits = cidr.split('/')
        bits = int(bits)
        if not _valid_ipv4(net):
            return False
        mask = ((0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF) if bits else 0
        return (ip_int & mask) == (_ipv4_to_int(net) & mask)
    except Exception:
        return False


class AIChatHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            self.supportedArgs.addOptArg('prompt')
            self.supportedArgs.addOptArg('provider_id')
            self.supportedArgs.addOptArg('mode')
            self.supportedArgs.addOptArg('history')

    def log_audit(self, user, model, mode, raw_prompt, ai_reply):
        try:
            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            log_dir = os.path.join(splunk_home, 'var', 'log', 'splunk')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_file = os.path.join(log_dir, AUDIT_LOG_FILE)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            safe_prompt = str(raw_prompt).replace('\n', ' ').replace('"', "'")
            safe_reply = str(ai_reply).replace('\n', ' ').replace('"', "'")
            log_entry = f'{timestamp} action="ai_query" user="{user}" mode="{mode}" model="{model}" prompt="{safe_prompt}" reply="{safe_reply}"\n'
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass

    def handleList(self, confInfo):
        """Return only non-secret UI bootstrap data needed by normal chat users.

        Provider administration and the full Knowledge Base remain behind the
        admin endpoints/capability. This endpoint exposes only provider names,
        default selection, and qq_ Quick Query labels/prompts.
        """
        providers = []
        quick_queries = []

        try:
            conf = self.readConf("ai_providers") or {}
            for stanza, settings in conf.items():
                if not stanza or stanza == "default":
                    continue
                providers.append({
                    "name": stanza,
                    "is_default": str((settings or {}).get("is_default", "0")).lower() in ("1", "true", "yes")
                })
        except Exception:
            providers = []

        try:
            conf = self.readConf("ai_knowledge_base") or {}
            for stanza, settings in conf.items():
                if not str(stanza).startswith("qq_"):
                    continue
                settings = settings or {}
                prompt = str(settings.get("context_data", "") or "").strip()
                if not prompt:
                    continue
                label = str(settings.get("description", "") or "").strip() or str(stanza)[3:]
                quick_queries.append({"label": label, "prompt": prompt})
        except Exception:
            quick_queries = []

        confInfo["bootstrap"].append("providers", json.dumps(providers, ensure_ascii=False))
        confInfo["bootstrap"].append("quick_queries", json.dumps(quick_queries, ensure_ascii=False))

    
    @staticmethod
    def _has_block_negation(text):
        """Detect explicit block-action negation."""
        neg = [
            r'\bengelleme(?:yin|yelim|z|sin)?\b', r'\bbloklama\b', r'\bblocklama\b',
            r'\bbanlama\b', r'\byapma\b', r'\betme\b', r'\bsak[ıi]n\b', r'\basla\b',
            r'\bgerek yok\b', r'\bistemiyorum\b', r"\bdon'?t\b", r'\bdo not\b',
            r'\bnever\b', r'\bno need\b', r"\bshould ?n'?t\b", r'\bshould not\b',
            r'\bwithout blocking\b',
        ]
        for rx in neg:
            if re.search(rx, text):
                return True
        return False

    @staticmethod
    def _get_sh_ip(session_key):
        try:
            _, sc = splunk.rest.simpleRequest(
                '/services/server/info?output_mode=json', sessionKey=session_key, method='GET')
            c = json.loads(sc)['entry'][0]['content']
            return c.get('ip', '') or c.get('host', '') or ''
        except Exception:
            return ''

    @staticmethod
    def _block_guard(ip, sh_ip, allowlist):
        if not _valid_ipv4(ip):
            return ("guard_invalid_ip", {})
        if sh_ip and ip == sh_ip:
            return ("guard_self_block", {})
        ipn = _ipv4_to_int(ip)
        for c in _PROTECTED_CIDRS:
            if _in_cidr(ipn, c):
                return ("guard_protected", {"cidr": c})
        for c in (allowlist or []):
            if _in_cidr(ipn, c):
                return ("guard_allowlisted", {"cidr": c})
        return None

    def _do_block(self, confInfo, session_key, current_user, provider_id, prompt, target_ip, sh_ip, language):
        try:
            block_spl = f'| makeresults | eval ip="{target_ip}" | fields - _time | outputlookup append=true ai_ip_block.csv'
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/dv_ai_assistant/search/jobs',
                sessionKey=session_key,
                postargs={'search': block_spl, 'exec_mode': 'oneshot'},
                method='POST'
            )

            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            script_path = os.path.join(splunk_home, 'etc', 'apps', 'dv_ai_assistant', 'bin', 'export_blocked_ips.sh')
            if os.path.exists(script_path):
                subprocess.run(['/bin/bash', script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            url_ip = sh_ip or 'localhost'
            feed_url = f'https://{url_ip}:8000/en-US/static/app/dv_ai_assistant/ai_ip_block.txt'
            success_reply = self._msg(language, 'block_success', ip=target_ip, url=feed_url)
            self.log_audit(current_user, provider_id or 'system', 'ip_block', prompt, success_reply)
            confInfo['chat_result'].append('reply', success_reply)
        except Exception as e:
            error_reply = self._msg(language, 'block_failed', error=str(e))
            self.log_audit(current_user, provider_id or 'system', 'ip_block', prompt, error_reply)
            confInfo['error'].append('reply', error_reply)


    @staticmethod
    def _lookup_contains_ip(session_key, target_ip):
        """ai_ip_block.csv içinde IP var mı? Sonucu doğrulama amacıyla kullanılır."""
        rows, _ = sio.run_search(
            session_key,
            f'| inputlookup ai_ip_block.csv | search ip="{target_ip}" | head 1 | fields ip',
            earliest='0',
            latest='now',
            max_results=1,
            timeout=30
        )
        return bool(rows)

    @staticmethod
    def _txt_contains_ip(target_ip):
        """Firewall besleme TXT dosyasında IP var mı?"""
        splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
        output_file = os.path.join(
            splunk_home, 'etc', 'apps', 'dv_ai_assistant',
            'appserver', 'static', 'ai_ip_block.txt'
        )
        if not os.path.exists(output_file):
            return False
        with open(output_file, 'r', encoding='utf-8', errors='replace') as handle:
            return target_ip in {line.strip() for line in handle if line.strip()}

    def _do_unblock(self, confInfo, session_key, current_user, provider_id, prompt, target_ip, sh_ip, language):
        try:
            if not _valid_ipv4(target_ip):
                raise ValueError(self._msg(language, 'invalid_unblock', ip=target_ip))

            if not self._lookup_contains_ip(session_key, target_ip):
                reply = self._msg(language, 'not_found', ip=target_ip)
                self.log_audit(current_user, provider_id or 'system', 'ip_unblock_not_found', prompt, reply)
                confInfo['chat_result'].append('reply', reply)
                return

            unblock_spl = (
                f'| inputlookup ai_ip_block.csv '
                f'| where ip!="{target_ip}" '
                f'| outputlookup ai_ip_block.csv'
            )
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/dv_ai_assistant/search/jobs',
                sessionKey=session_key,
                postargs={'search': unblock_spl, 'exec_mode': 'oneshot'},
                method='POST'
            )

            if self._lookup_contains_ip(session_key, target_ip):
                raise RuntimeError(self._msg(language, 'lookup_remove_failed'))

            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            script_path = os.path.join(
                splunk_home, 'etc', 'apps', 'dv_ai_assistant',
                'bin', 'export_blocked_ips.sh'
            )
            if not os.path.exists(script_path):
                raise RuntimeError(self._msg(language, 'export_script_missing'))

            proc = subprocess.run(
                ['/bin/bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or '').strip()
                raise RuntimeError(self._msg(language, 'export_failed', detail=(detail or 'script exit code ' + str(proc.returncode))))

            if self._txt_contains_ip(target_ip):
                raise RuntimeError(self._msg(language, 'txt_verify_failed'))

            url_ip = sh_ip or 'localhost'
            feed_url = f'https://{url_ip}:8000/en-US/static/app/dv_ai_assistant/ai_ip_block.txt'
            success_reply = self._msg(language, 'unblock_success', ip=target_ip, url=feed_url)
            self.log_audit(current_user, provider_id or 'system', 'ip_unblock', prompt, success_reply)
            confInfo['chat_result'].append('reply', success_reply)

        except Exception as e:
            error_reply = self._msg(language, 'unblock_failed', error=str(e))
            self.log_audit(current_user, provider_id or 'system', 'ip_unblock_error', prompt, error_reply)
            confInfo['error'].append('reply', error_reply)


    def _effective_caps_roles(self, session_key, username):
        """Geçerli kullanıcının etkin capability ve rollerini döndürür."""
        caps, roles = set(), set()
        try:
            _, c = splunk.rest.simpleRequest(
                '/services/authentication/current-context?output_mode=json',
                sessionKey=session_key, method='GET')
            content = json.loads(c)['entry'][0]['content']
            r = content.get('roles', []) or []
            roles = set(r if isinstance(r, list) else [r])
            cp = content.get('capabilities', []) or []
            caps = set(cp if isinstance(cp, list) else [cp])
        except Exception:
            pass
        
        if not caps and username:
            try:
                _, uc = splunk.rest.simpleRequest(
                    '/services/authentication/users/' + urllib.parse.quote(str(username)) + '?output_mode=json',
                    sessionKey=session_key, method='GET')
                ucontent = json.loads(uc)['entry'][0]['content']
                cp = ucontent.get('capabilities', []) or []
                caps = set(cp if isinstance(cp, list) else [cp])
                if not roles:
                    r = ucontent.get('roles', []) or []
                    roles = set(r if isinstance(r, list) else [r])
            except Exception:
                pass
        return caps, roles

    def _can_block(self, session_key, username, sec):
        """C4: IP engelleme mutating aksiyonu için yetki (capability) kontrolü."""
        required_cap = (str(sec.get('block_ip_capability', '') or 'block_ip')).strip() or 'block_ip'
        allow_roles = set(x.strip() for x in str(sec.get('block_ip_roles', '') or '').split(',') if x.strip())
        allow_roles |= {'admin', 'sc_admin'}   
        caps, roles = self._effective_caps_roles(session_key, username)
        if required_cap in caps:
            return True
        if roles & allow_roles:
            return True
        return False

    
    
    
    
    def _load_prompt_templates(self):
        templates = {}
        try:
            conf = self.readConf("ai_prompts") or {}
            for stanza, settings in conf.items():
                value = str(settings.get("template", "") or "").strip()
                if value:
                    templates[stanza] = value
        except Exception:
            pass
        return templates

    @staticmethod
    def _render_prompt(template, **values):
        rendered = str(template or "")
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", str(value or ""))
        return rendered

    def _response_language(self):
        try:
            settings_conf = self.readConf("ai_settings") or {}
            settings = settings_conf.get("global_settings", {}) or {}
            language = str(settings.get("language", "auto") or "auto").strip().lower()
        except Exception:
            language = "auto"
        allowed = {"auto", "en", "tr", "de", "fr", "es", "it", "pt", "nl", "pl", "ru", "ar", "ja", "ko", "zh"}
        return language if language in allowed else "auto"

    @staticmethod
    def _msg(language, key, **values):
        language = str(language or "auto").strip().lower()
        if language == "auto" or language not in _BACKEND_MESSAGES:
            language = "en"
        template = _BACKEND_MESSAGES.get(language, {}).get(key) or _BACKEND_MESSAGES["en"].get(key, key)
        try:
            return template.format(**values)
        except Exception:
            return template

    @classmethod
    def _guard_reason(cls, language, guard_result):
        if not guard_result:
            return ""
        key, values = guard_result
        return cls._msg(language, key, **(values or {}))

    @staticmethod
    def _language_instruction(language):
        language = str(language or "auto").strip().lower()
        names = {
            "en": "English", "tr": "Turkish", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "pt": "Portuguese", "nl": "Dutch",
            "pl": "Polish", "ru": "Russian", "ar": "Arabic", "ja": "Japanese",
            "ko": "Korean", "zh": "Chinese"
        }
        if language == "auto" or language not in names:
            return "Respond only in the same language as the user's current request. Do not mix languages unless technical terms require it."
        return "Respond only in %s. Do not switch or mix languages unless technical terms require it." % names[language]

    def _ssl_context(self, url, sec):
        """C5: Uzak host'lara TLS doğrulaması yapılır. Doğrulama YALNIZCA loopback
        için veya ai_assistant.conf [security] ile açıkça izin verilen host'lar
        için atlanır. Böylece bulut sağlayıcılara (OpenAI/Gemini/custom) giden
        API anahtarları MITM'e karşı korunur."""
        sec = sec or {}
        try:
            host = (urllib.parse.urlparse(url).hostname or '').lower()
        except Exception:
            host = ''
        loopback = host in ('localhost', '127.0.0.1', '::1', '0.0.0.0') or host.startswith('127.')
        verify_tls = str(sec.get('verify_tls', 'true')).strip().lower() not in ('0', 'false', 'no', 'off')
        skip_hosts = set(h.strip().lower() for h in str(sec.get('tls_skip_verify_hosts', '') or '').split(',') if h.strip())
        if (not verify_tls) or loopback or (host in skip_hosts):
            return ssl._create_unverified_context()
        return ssl.create_default_context()

    def _urlopen_json(self, req, ctx, timeout):
        """LLM çağrısı + geçici hata (429/500/502/503/504) durumunda kısa
        backoff'la 2 retry. Bu hatalar hızlı döner, timeout bütçesini bozmaz."""
        delays = [1.5, 3.0]
        attempt = 0
        while True:
            try:
                r = urllib.request.urlopen(req, context=ctx, timeout=timeout)
                return json.loads(r.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < len(delays):
                    time.sleep(delays[attempt])
                    attempt += 1
                    continue
                raise

    def _query_llm(self, user_prompt, engine_type, url, model, api_key, sec=None, system_instruction="", language="en"):
        ctx = self._ssl_context(url, sec)
        headers = {'Content-Type': 'application/json'}
        request_url = url.rstrip('/')
        payload = {}
        user_prompt = str(user_prompt or '')
        system_instruction = str(system_instruction or '').strip()

        if engine_type == 'ollama':
            if request_url.endswith('/api'):
                request_url += '/generate'
            elif not request_url.endswith('generate') and not request_url.endswith('chat'):
                request_url += '/api/generate'

            if request_url.endswith('/chat'):
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": user_prompt})
                payload = {"model": model, "messages": messages, "stream": False}
            else:
                payload = {"model": model, "prompt": user_prompt, "stream": False}
                if system_instruction:
                    payload["system"] = system_instruction

        elif engine_type == 'openai':
            headers['Authorization'] = f"Bearer {api_key}"
            messages = []
            if system_instruction:
                model_name = str(model or '').strip().lower()
                developer_prefixes = ('gpt-5', 'gpt-4.1', 'o1', 'o3', 'o4')
                instruction_role = 'developer' if model_name.startswith(developer_prefixes) else 'system'
                messages.append({"role": instruction_role, "content": system_instruction})
            messages.append({"role": "user", "content": user_prompt})
            payload = {"model": model, "messages": messages}

        elif engine_type == 'gemini':
            headers['X-goog-api-key'] = api_key
            if ':generatecontent' not in request_url.lower():
                base = request_url.split('/v1beta')[0].rstrip('/')
                request_url = f"{base}/v1beta/models/{model}:generateContent"
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }]
            }
            if system_instruction:
                payload["system_instruction"] = {
                    "parts": [{"text": system_instruction}]
                }

        else:
            if api_key:
                headers['Authorization'] = f"Bearer {api_key}"
            combined_prompt = user_prompt
            if system_instruction:
                combined_prompt = f"{system_instruction}\n\nUSER REQUEST:\n{user_prompt}"
            payload = {"prompt": combined_prompt}

        req = urllib.request.Request(
            request_url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        resp_json = self._urlopen_json(req, ctx, getattr(self, '_llm_timeout', 60))

        reply_text = self._msg(language, 'parsing_error')
        if engine_type == 'ollama':
            if isinstance(resp_json.get('message'), dict):
                reply_text = resp_json.get('message', {}).get('content', '') or ''
            else:
                reply_text = resp_json.get('response', '') or ''
        elif engine_type == 'openai':
            choices = resp_json.get('choices', [])
            reply_text = (choices[0].get('message', {}).get('content', '') if choices else '') or ''
            if not reply_text and 'error' in resp_json:
                reply_text = self._msg(language, 'openai_error', detail=resp_json.get('error', {}).get('message', ''))
        elif engine_type == 'gemini':
            cands = resp_json.get('candidates', [])
            if cands:
                parts = cands[0].get('content', {}).get('parts', [])
                texts = [p.get('text', '') for p in parts if p.get('text') and not p.get('thought')]
                reply_text = "\n".join(t for t in texts if t).strip()
                if not reply_text:
                    reply_text = self._msg(language, 'gemini_empty', reason=cands[0].get('finishReason', ''))
            else:
                pf = resp_json.get('promptFeedback', {})
                reply_text = self._msg(language, 'gemini_no_response', reason=pf.get('blockReason', '?'))
        elif engine_type == 'custom':
            reply_text = resp_json.get('reply', str(resp_json))

        return reply_text.strip()

    @staticmethod
    def _extract_spl(raw):
        """LLM çıktısından çalıştırılabilir SPL'i çıkarır. NO_SEARCH_NEEDED ise ya da
        SPL bulunamazsa None döner (o zaman sohbet moduna düşülür).
        index=... / sourcetype=... / tstats ... gibi başlangıçları da SPL sayar."""
        if not raw:
            return None
        t = raw.replace('```spl', '').replace('```', '').replace('`', '').strip()
        if 'NO_SEARCH_NEEDED' in t.upper():
            return None
        start = re.compile(
            r'^\s*(search\b|\||index\s*=|sourcetype\s*=|source\s*=|host\s*=|tstats\b|from\b|inputlookup\b|makeresults\b)',
            re.IGNORECASE
        )
        lines = t.split('\n')
        for i in range(len(lines)):
            if start.match(lines[i]):
                spl = '\n'.join(lines[i:]).strip()
                return spl if spl else None
        return None

    @staticmethod
    def _dispatch_window(prompt):
        """Derive the dispatch earliest/latest window from the user request.
        'son 5 dakika' -> (-5m, now). Varsayılan 24 saat."""
        p = (prompt or "").lower()
        m = re.search(r'(?:son|last|past)\s+(\d+)\s*([a-zçğıöşü]+)', p)
        if m:
            n, w = m.group(1), m.group(2)
            if w.startswith(('dak', 'dk', 'min')):
                u = 'm'
            elif w.startswith(('saat', 'hour', 'hr', 'sa')):
                u = 'h'
            elif w.startswith(('gün', 'gun', 'day', 'gu')):
                u = 'd'
            elif w.startswith(('haf', 'week', 'wk')):
                u = 'w'
            elif w.startswith(('ay', 'month', 'mon')):
                u = 'mon'
            else:
                u = 'h'
            return "-%s%s" % (n, u), "now"
        if 'bugün' in p or 'today' in p:
            return "@d", "now"
        return "-24h@h", "now"

    def handleCreate(self, confInfo):
        args = self.callerArgs.data
        prompt = args.get('prompt', [''])[0]
        provider_id = args.get('provider_id', [''])[0]
        mode = args.get('mode', ['chat'])[0]
        response_language = self._response_language()

        if not prompt:
            confInfo['error'].append('reply', self._msg(response_language, 'prompt_missing'))
            return

        session_key = self.getSessionKey()
        current_user = 'unknown'
        try:
            _, auth_content = splunk.rest.simpleRequest(
                '/services/authentication/current-context?output_mode=json',
                sessionKey=session_key, method='GET'
            )
            auth_data = json.loads(auth_content)
            current_user = auth_data['entry'][0]['content']['username']
        except Exception:
            current_user = getattr(self, 'userName', 'unknown')

        
        
        
        
        
        
        
        lower_prompt = prompt.lower()
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'

        confirm_match = re.match(
            r'^\s*(?:onayla|onay|confirm)\s+((?:\d{1,3}\.){3}\d{1,3})\s*$',
            prompt.strip(), re.IGNORECASE
        )
        unconfirm_match = re.match(
            r'^\s*(?:unconfirm|kaldırmayı\s+onayla|engel\s+kaldırmayı\s+onayla)\s+'
            r'((?:\d{1,3}\.){3}\d{1,3})\s*$',
            prompt.strip(), re.IGNORECASE
        )

        is_unblock_intent = re.search(
            r'(?:engel(?:ini|i)?\s+kaldır|engelleme\s+listesinden\s+kaldır|'
            r'kara\s+listeden\s+kaldır|blok(?:u|unu)?\s+kaldır|'
            r'blocklist(?:ten|den)?\s+(?:kaldır|sil)|\bunblock\b|\bunban\b)',
            lower_prompt
        ) is not None
        is_block_intent = re.search(r'\b(?:engelle|block|blokla|banla)', lower_prompt) is not None
        is_negated = self._has_block_negation(lower_prompt)
        is_question = ('?' in lower_prompt or 'sence' in lower_prompt or 'acaba' in lower_prompt
                       or 'should' in lower_prompt
                       or re.search(r'\b(?:mi|mı|mu|mü)\b', lower_prompt) is not None)

        if mode != 'triage' and (
            unconfirm_match or
            (is_unblock_intent and not is_question) or
            confirm_match or
            (is_block_intent and not is_unblock_intent and not is_negated and not is_question)
        ):
            try:
                sec = sio.get_settings(session_key).get('security', {}) or {}
            except Exception:
                sec = {}

            allowlist = [c.strip() for c in str(sec.get('ip_block_allowlist', '') or '').split(',') if c.strip()]
            sh_ip = self._get_sh_ip(session_key)

            
            if not self._can_block(session_key, current_user, sec):
                reply = self._msg(response_language, 'auth_denied')
                self.log_audit(current_user, provider_id or 'system', 'ip_block_denied_authz', prompt, reply)
                confInfo['chat_result'].append('reply', reply)
                return

            
            if unconfirm_match:
                target_ip = unconfirm_match.group(1)
                if not _valid_ipv4(target_ip):
                    reply = self._msg(response_language, 'invalid_unblock', ip=target_ip)
                    self.log_audit(current_user, provider_id or 'system', 'ip_unblock_denied', prompt, reply)
                    confInfo['chat_result'].append('reply', reply)
                    return
                self._do_unblock(
                    confInfo, session_key, current_user,
                    provider_id, prompt, target_ip, sh_ip, response_language
                )
                return

            if is_unblock_intent:
                ip_match = re.search(ip_pattern, prompt)
                if ip_match:
                    target_ip = ip_match.group(0)
                    if not _valid_ipv4(target_ip):
                        reply = self._msg(response_language, 'invalid_unblock', ip=target_ip)
                        self.log_audit(current_user, provider_id or 'system', 'ip_unblock_denied', prompt, reply)
                        confInfo['chat_result'].append('reply', reply)
                        return

                    try:
                        exists = self._lookup_contains_ip(session_key, target_ip)
                    except Exception as lookup_err:
                        reply = self._msg(response_language, 'lookup_failed', error=str(lookup_err))
                        self.log_audit(current_user, provider_id or 'system', 'ip_unblock_lookup_error', prompt, reply)
                        confInfo['error'].append('reply', reply)
                        return

                    if not exists:
                        reply = self._msg(response_language, 'not_found', ip=target_ip)
                        self.log_audit(current_user, provider_id or 'system', 'ip_unblock_not_found', prompt, reply)
                        confInfo['chat_result'].append('reply', reply)
                        return

                    confirm_reply = self._msg(response_language, 'confirm_unblock', ip=target_ip)
                    self.log_audit(current_user, provider_id or 'system', 'ip_unblock_prompt', prompt, confirm_reply)
                    confInfo['chat_result'].append('reply', confirm_reply)
                    return

            
            if confirm_match:
                target_ip = confirm_match.group(1)
                guard_err = self._block_guard(target_ip, sh_ip, allowlist)
                if guard_err:
                    reason = self._guard_reason(response_language, guard_err)
                    reply = self._msg(response_language, 'block_rejected', ip=target_ip, reason=reason)
                    self.log_audit(current_user, provider_id or 'system', 'ip_block_denied', prompt, reply)
                    confInfo['chat_result'].append('reply', reply)
                    return
                self._do_block(confInfo, session_key, current_user, provider_id, prompt, target_ip, sh_ip, response_language)
                return

            ip_match = re.search(ip_pattern, prompt)
            if ip_match:
                target_ip = ip_match.group(0)
                guard_err = self._block_guard(target_ip, sh_ip, allowlist)
                if guard_err:
                    reason = self._guard_reason(response_language, guard_err)
                    reply = self._msg(response_language, 'block_not_allowed', ip=target_ip, reason=reason)
                    self.log_audit(current_user, provider_id or 'system', 'ip_block_denied', prompt, reply)
                    confInfo['chat_result'].append('reply', reply)
                    return

                confirm_reply = self._msg(response_language, 'confirm_block', ip=target_ip)
                self.log_audit(current_user, provider_id or 'system', 'ip_block_prompt', prompt, confirm_reply)
                confInfo['chat_result'].append('reply', confirm_reply)
                return

        
        
        
        kb_context = ""
        datamodel_context = ""
        system_prompt = ""
        try:
            kb_dict = self.readConf("ai_knowledge_base")
            if kb_dict:
                kb_lines = []
                datamodel_definitions = parse_datamodel_definitions(kb_dict)

                for stanza, settings in kb_dict.items():
                    if stanza == 'system_prompt':
                        
                        system_prompt = settings.get('context_data', '') or ''
                        continue
                    if stanza.startswith('qq_'):
                        
                        continue
                    if str(settings.get('type', '')).strip().lower() == 'datamodel':
                        
                        continue

                    desc = settings.get('description', '')
                    data = settings.get('context_data', '')
                    default_search = settings.get('default_search', '')
                    approved_spl = data or default_search
                    if approved_spl:
                        kb_lines.append(
                            f"- Anahtar: {stanza} | Tanım: {desc} | Onaylı SPL/Arama: {approved_spl}"
                        )

                if kb_lines:
                    kb_context = "\n".join(kb_lines)

                dm_lines = []
                for registry_key, definition in datamodel_definitions.items():
                    field_map = ", ".join(
                        f"{logical}={physical}"
                        for logical, physical in sorted(definition.fields.items())
                    )
                    value_map_parts = []
                    for logical_field, values in sorted(definition.values.items()):
                        for logical_value, physical_value in sorted(values.items()):
                            value_map_parts.append(
                                f"{logical_field}.{logical_value}={physical_value}"
                            )
                    value_map = ", ".join(value_map_parts) or "yok"
                    dm_lines.append(
                        f"- Registry: {registry_key} | Açıklama: {definition.description} | "
                        f"DataModel/Dataset: {definition.dataset} | "
                        f"Accelerated: {'true' if definition.accelerated else 'false'} | "
                        f"Alanlar: {field_map} | Değer eşlemeleri: {value_map}"
                    )
                if dm_lines:
                    datamodel_context = "\n".join(dm_lines)
        except Exception:
            pass

        try:
            _, conf_content = splunk.rest.simpleRequest(
                '/servicesNS/nobody/dv_ai_assistant/configs/conf-ai_providers?output_mode=json',
                sessionKey=session_key, method='GET'
            )
            providers_data = json.loads(conf_content).get('entry', [])
        except Exception:
            confInfo['error'].append('reply', self._msg(response_language, 'provider_read'))
            return

        if not providers_data:
            confInfo['error'].append('reply', self._msg(response_language, 'provider_none'))
            return

        selected_provider = None
        if provider_id:
            for p in providers_data:
                if p['name'] == provider_id:
                    selected_provider = p['content']
                    break

        if not selected_provider:
            for p in providers_data:
                if p['content'].get('is_default') in ['1', 'true', 'True', True]:
                    selected_provider = p['content']
                    provider_id = p['name']
                    break

        if not selected_provider:
            selected_provider = providers_data[0]['content']
            provider_id = providers_data[0]['name']

        engine_type = selected_provider.get('engine_type', 'ollama').lower()
        url = selected_provider.get('url', '').strip()
        model = selected_provider.get('model', '').strip()

        api_key = ""
        if engine_type != 'ollama':
            realm = f'dv_ai_provider_{provider_id}'
            try:
                _, pwd_content = splunk.rest.simpleRequest(
                    f'/servicesNS/nobody/dv_ai_assistant/storage/passwords?output_mode=json&search=realm="{realm}"',
                    sessionKey=session_key, method='GET'
                )
                for p in json.loads(pwd_content).get('entry', []):
                    if p.get('content', {}).get('username') == 'api_key':
                        api_key = p.get('content', {}).get('clear_password', '')
                        break
            except Exception:
                pass

        
        try:
            app_settings = sio.get_settings(session_key)
        except Exception:
            app_settings = {}

        
        
        try:
            self._llm_timeout = int((app_settings.get('query', {}) or {}).get('llm_timeout_seconds', 60) or 60)
        except (TypeError, ValueError):
            self._llm_timeout = 60

        prompt_templates = self._load_prompt_templates()
        language_instruction = self._language_instruction(response_language)

        
        
        
        
        
        if mode == 'triage':
            triage_template = prompt_templates.get("triage", "")
            triage_system = str(triage_template or system_prompt or DEFAULT_TRIAGE_PROMPT).strip()
            triage_system = self._render_prompt(
                triage_system,
                LANGUAGE_INSTRUCTION=language_instruction,
                ALERT_DATA=""
            )
            triage_system = triage_system.replace("[ALERT DATA]", "").strip()
            triage_user = "[ALERT DATA]\n" + prompt

            try:
                final_reply = self._query_llm(
                    triage_user,
                    engine_type,
                    url,
                    model,
                    api_key,
                    app_settings.get('security', {}),
                    system_instruction=triage_system,
                    language=response_language
                )
            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode('utf-8', 'replace')[:400]
                except Exception:
                    body = ''
                final_reply = self._msg(response_language, 'llm_http_error', code=e.code, detail=body)
            except Exception as e:
                final_reply = self._msg(response_language, 'llm_error', detail=str(e))
            self.log_audit(current_user, provider_id, mode, prompt, final_reply)
            confInfo['chat_result'].append('reply', final_reply)
            return

        history_text = ""
        raw_hist = args.get('history', [''])[0]
        if raw_hist:
            try:
                hist = json.loads(raw_hist)
                h_lines = []
                for m in hist[-6:]:
                    role = 'User' if m.get('role') == 'user' else 'Assistant'
                    content = str(m.get('content', '')).strip()
                    if content:
                        h_lines.append(f"{role}: {content}")
                if h_lines:
                    history_text = "\n".join(h_lines)
            except Exception:
                history_text = ""

        
        
        
        try:
            
            history_block = f"PREVIOUS CONVERSATION:\n{history_text}\n\n" if history_text else ""
            planner_template = prompt_templates.get("planner", "")
            if not planner_template:
                planner_template = "You are an expert Splunk SPL generation engine. Return exactly one valid single-line SPL search, or exactly NO_SEARCH_NEEDED when no Splunk search is required."
            planner_system = self._render_prompt(
                planner_template,
                KB_CONTEXT=kb_context or "No approved records",
                DATAMODEL_CONTEXT=datamodel_context or "No registered Data Models",
                HISTORY_BLOCK="",
                USER_REQUEST=""
            ).strip()
            planner_user = f"{history_block}Request: {prompt}\nSPL:"

            llm_decision = self._query_llm(
                planner_user,
                engine_type,
                url,
                model,
                api_key,
                app_settings.get('security', {}),
                system_instruction=planner_system,
                language=response_language
            )

            
            
            
            spl_query = self._extract_spl(llm_decision)

            if not spl_query:
                
                hist_block = f"PREVIOUS CONVERSATION:\n{history_text}\n\n" if history_text else ""
                chat_template = prompt_templates.get("chat", "")
                if chat_template:
                    chat_system = self._render_prompt(
                        chat_template,
                        LANGUAGE_INSTRUCTION=language_instruction,
                        HISTORY_BLOCK="",
                        USER_REQUEST=""
                    ).strip()
                else:
                    chat_system = (
                        "You are a professional Security Operations Center assistant for Splunk. "
                        "Your scope is limited to Splunk and cybersecurity-related technical assistance.\n\n"
                        + language_instruction
                    ).strip()

                customer_system_prompt = str(system_prompt or "").strip()
                if customer_system_prompt:
                    chat_system = (
                        chat_system
                        + "\n\nCUSTOMER-DEFINED SOC CONTEXT AND INSTRUCTIONS:\n"
                        + "The following content is administrator-managed configuration from the app Knowledge Base. "
                          "Use it to adapt terminology, environment context, analysis style, operational guidance, "
                          "and organization-specific behavior. It is supplemental and must not override the core "
                          "Splunk/cybersecurity scope, safety restrictions, or system instructions above.\n\n"
                        + customer_system_prompt
                        + "\n\nEND CUSTOMER-DEFINED SOC CONTEXT. Core system instructions above take precedence in case of conflict."
                    ).strip()

                normal_prompt = f"{hist_block}{prompt}".strip()
                final_reply = self._query_llm(
                    normal_prompt,
                    engine_type,
                    url,
                    model,
                    api_key,
                    app_settings.get('security', {}),
                    system_instruction=chat_system,
                    language=response_language
                )

            else:
                
                if not spl_query.startswith('|') and not spl_query.lower().startswith('search'):
                    spl_query = f"search {spl_query}"

                
                
                
                spl_query = re.sub(r'\b(?:earliest|latest)\s*=\s*[^\s|]+', ' ', spl_query, flags=re.IGNORECASE)
                
                spl_query = re.sub(r'\|\s*export\b[^|]*', ' ', spl_query, flags=re.IGNORECASE)
                spl_query = re.sub(r'\s{2,}', ' ', spl_query).strip()

                
                
                
                
                verdict = Guardrail(app_settings.get('security', {})).check(spl_query)
                if not verdict.get('allowed'):
                    issues = "; ".join(verdict.get('issues', [])) or "write / side-effecting command"
                    refusal = self._msg(
                        response_language,
                        'guardrail_blocked',
                        issues=issues,
                        spl=spl_query
                    )
                    self.log_audit(current_user, provider_id, mode, prompt, refusal)
                    confInfo['chat_result'].append('reply', refusal)
                    return

                
                
                
                
                try:
                    q_conf = app_settings.get('query', {}) or {}
                    try:
                        agent_timeout = int(q_conf.get('timeout_seconds', 60))
                    except (TypeError, ValueError):
                        agent_timeout = 60

                    
                    run_ea, run_la = self._dispatch_window(prompt)
                    rows, truncated = sio.run_search(
                        session_key, spl_query,
                        earliest=run_ea, latest=run_la,
                        max_results=20, timeout=agent_timeout
                    )
                    if not rows:
                        results_text = "ZERO_RESULTS"
                    else:
                        results_text = json.dumps(rows, indent=2, ensure_ascii=False)
                except Exception as search_err:
                    results_text = f"SEARCH_ERROR: {str(search_err)}"

                
                synthesis_template = prompt_templates.get("synthesis", "")
                if not synthesis_template:
                    synthesis_template = "You are a professional cybersecurity analysis engine. Interpret Splunk search results directly and never invent evidence. {{LANGUAGE_INSTRUCTION}}"
                synthesis_system = self._render_prompt(
                    synthesis_template,
                    LANGUAGE_INSTRUCTION=language_instruction,
                    USER_REQUEST="",
                    SPL_QUERY="",
                    SEARCH_RESULTS=""
                ).strip()
                synthesis_prompt = (
                    f"Original request: {prompt}\n"
                    f"Executed SPL: {spl_query}\n\n"
                    f"Raw Splunk results:\n{results_text}"
                )

                final_reply = self._query_llm(
                    synthesis_prompt,
                    engine_type,
                    url,
                    model,
                    api_key,
                    app_settings.get('security', {}),
                    system_instruction=synthesis_system,
                    language=response_language
                )

                
                if verdict.get('risk_level') == 'caution':
                    sec_issues = "; ".join(verdict.get('issues', []))
                    final_reply += "\n\n" + self._msg(response_language, 'guardrail_caution', issues=sec_issues)

                
                final_reply += f"\n\n*({self._msg(response_language, 'agentic_search_info')} · {run_ea} → {run_la}:)*\n```spl\n{spl_query}\n```"

            self.log_audit(current_user, provider_id, mode, prompt, final_reply)
            confInfo['chat_result'].append('reply', final_reply)

        except urllib.error.HTTPError as e:
            error_msg = self._msg(response_language, 'http_error', code=e.code, detail=e.read().decode('utf-8', 'replace'))
            self.log_audit(current_user, provider_id, mode, prompt, error_msg)
            confInfo['error'].append('reply', error_msg)
        except Exception as e:
            error_msg = self._msg(response_language, 'connection_failed', error=str(e))
            self.log_audit(current_user, provider_id, mode, prompt, error_msg)
            confInfo['error'].append('reply', error_msg)


admin.init(AIChatHandler, admin.CONTEXT_APP_AND_USER)

