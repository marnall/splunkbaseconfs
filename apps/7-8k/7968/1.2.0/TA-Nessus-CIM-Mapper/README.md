# TA-Nessus-CIM-Mapper

Este Technology Add-on (TA) desarrollado por Francis Segura permite normalizar y mapear eventos generados por Tenable Nessus Professional (en formato JSON) al modelo de datos `Vulnerabilities` definido por el Common Information Model (CIM) de Splunk.

## Funcionalidades

- Mapeo automático de campos CVE, severidad, producto, firma y categoría.
- Alineación total con el Data Model `Vulnerabilities`.
- Basado en eventos con `sourcetype=nessus:json`.

## Requisitos

- Splunk Enterprise o Splunk Cloud
- Eventos Nessus exportados como JSON
- CIM instalado en el entorno de búsqueda (`Splunk_SA_CIM`)

## Instalación

1. Copie la carpeta `TA-Nessus-CIM-Mapper` en `$SPLUNK_HOME/etc/apps/`.
2. Reinicie Splunk o realice un recarga de configuración.
3. Asegúrese de que los eventos tengan el sourcetype `nessus:json`.

## Validación

Use esta búsqueda para validar la normalización:

```spl
| tstats count from datamodel=Vulnerabilities by All_Tags
