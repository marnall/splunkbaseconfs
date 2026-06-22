# Datavira Add-on for USOM Threat Intelligence / USOM Tehdit İstihbaratı için Datavira Eklentisi

[English](#english) · [Türkçe](#türkçe)

---

## English

`TA-usom-cti` integrates the USOM (Turkey's TR-CERT, part of the Turkish
Cybersecurity Presidency) public threat-intelligence API into Splunk
Enterprise and Splunk Enterprise Security.

USOM stopped publishing its legacy `.txt` IOC distribution on
**June 1, 2026**; only the JSON REST API at
<https://siberguvenlik.gov.tr/api/> remains.

### What it does

- Polls the USOM REST API on a schedule and produces five Splunk lookups:
  `usom_ip_intel`, `usom_ip6_intel`, `usom_ip6net_intel`,
  `usom_domain_intel`, `usom_url_intel`.
- Resolves USOM's short codes (`desc`, `source`, `connectiontype`) to
  their English titles via the companion `/api/address-description/`,
  `/api/address-source/`, and `/api/address-connection-type/` endpoints.
- Optionally pushes each lookup into Splunk Enterprise Security's threat
  intelligence framework (`ip_intel`, `domain_intel`, `http_intel` KV-store
  collections) via the bundled `threatlist://` stanzas — disabled by
  default; toggled per-type from the setup page.
- Emits one stats event per fetch cycle to a configurable Splunk index
  (default `_internal`, sourcetype `usom_ti:stats`).

### Requirements

- Splunk Enterprise 9.0+ or 10.x. Single-instance, search head, or heavy
  forwarder.
- Outbound HTTPS to `siberguvenlik.gov.tr` (or the configured
  `api_base_url`).
- For ES push: Splunk Enterprise Security 7.0+ installed on the same
  instance.

No external pip dependencies.

#### Search Head Cluster (SHC)

The modular input checks SHC membership at runtime and **only fetches on
the cluster captain**; non-captain members no-op silently. Lookups are
written to the captain's `$SPLUNK_HOME/etc/apps/TA-usom-cti/lookups/`
directory and propagate to the rest of the cluster through SHC's
built-in app bundle replication.

### Install

#### From Splunkbase

1. **Apps → Browse more apps**, search "USOM", click **Install**.
2. Restart Splunk when prompted.

#### From a tarball

```bash
tar -xzf TA-usom-cti-<version>.tar.gz -C $SPLUNK_HOME/etc/apps/
$SPLUNK_HOME/bin/splunk restart
```

### Configure

After install, open **Apps → USOM Threat Intelligence → Setup** and tick
the relevant options. The form persists to the `[usom_ti://default]`
input stanza.

| Parameter | Default | Description |
|---|---|---|
| `criticality_threshold` | `7` | Maximum `criticality_level` to include. USOM uses an inverted scale: **1 = most critical, 10 = least**. Threshold of `3` keeps only the top three levels. |
| `types` | `ip,ip6,ip6net,domain,url` | Comma-separated subset of IOC types to fetch. |
| `interval` | `14400` | Seconds between polls (default 4 hours). |
| `api_base_url` | `https://siberguvenlik.gov.tr/api/address/index` | Override for testing only. |
| `request_delay_seconds` | `5` | Polite delay between paginated requests. |
| `http_proxy` | _(empty)_ | Optional HTTP/HTTPS proxy URL. |
| `stats_index` | `_internal` | Index for per-cycle stats events (sourcetype `usom_ti:stats`). |

### Enterprise Security integration

The setup page exposes five independent toggles ("Push to ES threat
intel") — one per lookup. Ticking a box enables the matching
`[threatlist://usom_<type>_intel]` stanza shipped with the add-on. ES's
threat-intel framework then ingests the corresponding CSV into its
KV-store collection:

| Lookup | ES `type` | KV collection |
|---|---|---|
| `usom_ip_intel` | `ip` | `ip_intel` |
| `usom_ip6_intel` | `ip` | `ip_intel` |
| `usom_ip6net_intel` | `ip` | `ip_intel` |
| `usom_domain_intel` | `domain` | `domain_intel` |
| `usom_url_intel` | `http` | `http_intel` |

The `criticality_level` column maps to the ES `weight` field. Remember
the inverted scale: a lower numeric value means a more critical IOC.

### Monitoring dashboard

The add-on ships a single SimpleXML dashboard at **Apps → USOM Threat
Intelligence → USOM Monitoring**. It shows total indicator counts, a
type / criticality breakdown, the last 24h of fetch cycles (counts,
durations, success vs. error), and a tail of the operational log
(`$SPLUNK_HOME/var/log/splunk/ta_usom_cti.log`, auto-indexed into
`_internal`).

### Example searches

```spl
| inputlookup usom_ip_intel
| where criticality_level <= 3
```

```spl
index=firewall action=allowed
| lookup usom_ip_intel ip AS dest_ip OUTPUT criticality_level, description, category
| where isnotnull(criticality_level)
```

```spl
index=proxy
| lookup usom_url_intel url AS http_url OUTPUT criticality_level, description, category, source
| where isnotnull(criticality_level)
| stats count by url, description, category, source
```

### Limitations

- The USOM API serves a Turkey-centric feed; expect a strong bias toward
  Turkish hosts and infrastructure. Pair with other feeds for global
  coverage.
- The `criticality_level` scale is USOM's assessment — do not treat it
  as universally comparable to other vendors' scores. The direction is
  inverted vs many other vendors (`1 = most critical`).
- All API responses are public; no auth header is sent today.

### Support

`support+usom-cti@datavira.com`

### License

Apache License 2.0 — see [LICENSE](LICENSE).

---

## Türkçe

`TA-usom-cti`, USOM'un (Türkiye Cumhurbaşkanlığı Siber Güvenlik
Başkanlığı'na bağlı TR-CERT) kamuya açık tehdit istihbaratı API'sini
Splunk Enterprise ve Splunk Enterprise Security'ye entegre eder.

USOM, eski `.txt` IOC dağıtımını **1 Haziran 2026** itibarıyla durdurdu;
yalnızca <https://siberguvenlik.gov.tr/api/> adresindeki JSON REST API'si
hizmet vermeye devam ediyor.

### Ne yapar

- USOM REST API'sini belirli aralıklarla sorgular ve beş Splunk lookup
  üretir: `usom_ip_intel`, `usom_ip6_intel`, `usom_ip6net_intel`,
  `usom_domain_intel`, `usom_url_intel`.
- USOM'un kısa kodlarını (`desc`, `source`, `connectiontype`) karşılık
  gelen `/api/address-description/`, `/api/address-source/` ve
  `/api/address-connection-type/` endpoint'leri üzerinden açıklamalarına
  çevirir.
- İsteğe bağlı olarak her lookup'ı Splunk Enterprise Security'nin tehdit
  istihbaratı framework'üne (`ip_intel`, `domain_intel`, `http_intel`
  KV-store collection'ları) gömülü `threatlist://` stanza'ları üzerinden
  iletir — varsayılan kapalı; setup ekranından her IOC tipi için ayrı
  ayrı açılabilir.
- Her fetch döngüsünde, yapılandırılabilir bir Splunk indexine (varsayılan
  `_internal`, sourcetype `usom_ti:stats`) tek bir istatistik event'i
  yazar.

### Gereksinimler

- Splunk Enterprise 9.0+ veya 10.x. Tek node, search head veya heavy
  forwarder olarak çalışabilir.
- `siberguvenlik.gov.tr` (veya yapılandırılan `api_base_url`) için giden
  HTTPS erişimi.
- ES push özelliği için: aynı instance üzerinde Splunk Enterprise
  Security 7.0+ kurulu olmalı.

Harici pip bağımlılığı yoktur.

#### Search Head Cluster (SHC)

Modular input çalışma zamanında SHC üyeliğini kontrol eder ve **fetch
işlemini yalnızca cluster captain'ında** gerçekleştirir; captain olmayan
üyeler sessizce atlar. Lookup'lar captain'ın
`$SPLUNK_HOME/etc/apps/TA-usom-cti/lookups/` dizinine yazılır ve SHC'nin
yerleşik app bundle replication mekanizması üzerinden cluster'ın geri
kalanına yayılır.

### Kurulum

#### Splunkbase üzerinden

1. **Apps → Browse more apps** menüsünden "USOM" arayın, **Install**'a
   tıklayın.
2. İstendiğinde Splunk'ı yeniden başlatın.

#### Tarball üzerinden

```bash
tar -xzf TA-usom-cti-<sürüm>.tar.gz -C $SPLUNK_HOME/etc/apps/
$SPLUNK_HOME/bin/splunk restart
```

### Yapılandırma

Kurulumdan sonra **Apps → USOM Threat Intelligence → Setup** sayfasını
açın ve ilgili seçenekleri işaretleyin. Form `[usom_ti://default]` input
stanza'sına kalıcı olarak yazar.

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `criticality_threshold` | `7` | Dahil edilecek maksimum `criticality_level`. USOM ters bir ölçek kullanır: **1 = en kritik, 10 = en az kritik**. Eşik değer `3` olarak ayarlanırsa yalnızca ilk üç kritiklik seviyesi alınır. |
| `types` | `ip,ip6,ip6net,domain,url` | Çekilecek IOC tiplerinin virgülle ayrılmış listesi. |
| `interval` | `14400` | Sorgular arası saniye (varsayılan 4 saat). |
| `api_base_url` | `https://siberguvenlik.gov.tr/api/address/index` | Sadece test amaçlı override için. |
| `request_delay_seconds` | `5` | Sayfalar arası kibarlık gecikmesi. |
| `http_proxy` | _(boş)_ | Opsiyonel HTTP/HTTPS proxy URL'i. |
| `stats_index` | `_internal` | Cycle başına yazılan stats event'leri için index (sourcetype `usom_ti:stats`). |

### Enterprise Security entegrasyonu

Setup sayfasında beş bağımsız toggle bulunur ("Push to ES threat intel")
— her lookup için bir tane. Kutuyu işaretlemek, eklentiyle birlikte gelen
ilgili `[threatlist://usom_<tip>_intel]` stanza'sını aktif eder. ES'in
tehdit istihbaratı framework'ü ardından CSV'yi karşılık gelen KV-store
collection'ına aktarır:

| Lookup | ES `type` | KV collection |
|---|---|---|
| `usom_ip_intel` | `ip` | `ip_intel` |
| `usom_ip6_intel` | `ip` | `ip_intel` |
| `usom_ip6net_intel` | `ip` | `ip_intel` |
| `usom_domain_intel` | `domain` | `domain_intel` |
| `usom_url_intel` | `http` | `http_intel` |

`criticality_level` sütunu ES'in `weight` alanına haritalanır. Ters
ölçeği unutmayın: daha düşük sayısal değer daha kritik IOC anlamına gelir.

### Monitoring dashboard'u

Eklenti, **Apps → USOM Threat Intelligence → USOM Monitoring**
yolunda tek bir SimpleXML dashboard ile gelir. Toplam IOC sayısı, tip /
kritiklik kırılımı, son 24 saatin fetch döngüleri (sayılar, süreler,
başarı vs. hata) ve operasyonel log'un son satırlarını
(`$SPLUNK_HOME/var/log/splunk/ta_usom_cti.log`, otomatik olarak
`_internal`'e indexlenir) gösterir.

### Örnek aramalar

```spl
| inputlookup usom_ip_intel
| where criticality_level <= 3
```

```spl
index=firewall action=allowed
| lookup usom_ip_intel ip AS dest_ip OUTPUT criticality_level, description, category
| where isnotnull(criticality_level)
```

```spl
index=proxy
| lookup usom_url_intel url AS http_url OUTPUT criticality_level, description, category, source
| where isnotnull(criticality_level)
| stats count by url, description, category, source
```

### Sınırlamalar

- USOM API'si Türkiye odaklı bir besleme sunar; Türk host ve altyapıya
  güçlü bir önyargı beklemelisiniz. Küresel kapsam için başka beslemelerle
  birlikte kullanın.
- `criticality_level` ölçeği USOM'un kendi değerlendirmesidir — başka
  sağlayıcıların skorlarıyla doğrudan karşılaştırılamaz. Yön de
  diğerlerinden ters (`1 = en kritik`).
- Tüm API yanıtları kamuya açıktır; bugün için herhangi bir auth header
  gönderilmez.

### Destek

`support+usom-cti@datavira.com`

### Lisans

Apache License 2.0 — bkz. [LICENSE](LICENSE).
