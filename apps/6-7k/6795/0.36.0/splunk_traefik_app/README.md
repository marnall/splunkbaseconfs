### Splunk Traefik App

## Requirements

This app requires the Traefik addon to be installed: [splunkbase.splunk.com/app/6733](https://splunkbase.splunk.com/app/6733)

To configure Traefik access and application logs, please refer to
[doc.traefik.io/traefik/observability/access-logs/](https://doc.traefik.io/traefik/observability/access-logs/) and [doc.traefik.io/traefik/observability/logs/](https://doc.traefik.io/traefik/observability/logs/)

To configure access logs in JSON or Common Log Format (CLF) you can use:  
```yaml
accessLog:
  filePath: "/path/to/access.log"
  format: json|common
```

To configure the application logs for Traefik, you can use:
```yaml
log:
  filePath: "/path/to/log-file.log"
  format: json|common
  level: DEBUG|INFO|WARN|ERROR|FATAL|PANIC
```

In case of any problem with the app please open an issue at [gitlab.com/mathieuHa/splunk_traefik_app](https://gitlab.com/mathieuHa/splunk_traefik_app)

Mathieu HANOTAUX, Gaetan Jacquaz