"""
Use Case Dashboard Definitions for DASH Lite - Styled App Builder

Python mirror of appserver/static/js/use_cases.js.
Provides dashboard definitions structured for Simple XML generation.

1 use case x 2 dashboards.
All searches use makeresults (fully self-contained, no CSV dependencies).
"""

USE_CASES = {

    # ==================================================================
    # CYBERSECURITY (SIEM)
    # ==================================================================
    'cybersecurity': {
        'label': 'Cybersecurity (SIEM)',
        'dashboards': [
            {
                'id': 'security_posture',
                'title': 'Security Posture Overview',
                'description': 'High-level summary of the organization\'s risk profile',
                'rows': [
                    {
                        'panels': [
                            {'title': 'Critical Alerts (24h)', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=42, trend="-12%"'},
                            {'title': 'Mean Time to Detect', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=18, unit="min"'},
                            {'title': 'Compliance Score', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=94, unit="%"'},
                        ]
                    },
                    {
                        'panels': [
                            {'title': 'Alerts by Severity', 'type': 'chart', 'chart_type': 'column',
                             'search': '| makeresults count=4 | streamstats count as idx | eval severity=case(idx=1,"Critical",idx=2,"High",idx=3,"Medium",idx=4,"Low"), count=case(idx=1,42,idx=2,156,idx=3,389,idx=4,721) | table severity count'},
                            {'title': 'Threat Trend (24h)', 'type': 'chart', 'chart_type': 'area',
                             'search': '| makeresults count=24 | streamstats count as hour | eval _time=relative_time(now(), "-24h+".(hour-1)."h"), alerts=round(random()%50+10), blocked=round(random()%30+5) | table _time alerts blocked'},
                        ]
                    },
                    {
                        'panels': [
                            {'title': 'Recent Security Events', 'type': 'table',
                             'search': '| makeresults count=5 | streamstats count as idx | eval _time=relative_time(now(), "-".(idx*15)."m"), source=case(idx=1,"Firewall",idx=2,"IDS",idx=3,"WAF",idx=4,"Endpoint",idx=5,"SIEM"), severity=case(idx=1,"Critical",idx=2,"High",idx=3,"Medium",idx=4,"Low",idx=5,"High"), action=case(idx=1,"Blocked",idx=2,"Alerted",idx=3,"Blocked",idx=4,"Quarantined",idx=5,"Alerted"), description=case(idx=1,"Port scan from 10.0.1.55",idx=2,"SQL injection attempt",idx=3,"XSS payload detected",idx=4,"Malware hash match",idx=5,"Brute force login") | table _time source severity action description'},
                        ]
                    },
                ]
            },
            {
                'id': 'network_security',
                'title': 'Network Security',
                'description': 'Firewall, IDS/IPS, and network traffic analysis',
                'rows': [
                    {
                        'panels': [
                            {'title': 'Blocked Connections', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=12847'},
                            {'title': 'Active Firewall Rules', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=342'},
                            {'title': 'IDS Alerts', 'type': 'single',
                             'search': '| makeresults count=1 | eval count=89'},
                        ]
                    },
                    {
                        'panels': [
                            {'title': 'Traffic by Protocol', 'type': 'chart', 'chart_type': 'pie',
                             'search': '| makeresults count=5 | streamstats count as idx | eval protocol=case(idx=1,"HTTPS",idx=2,"HTTP",idx=3,"DNS",idx=4,"SSH",idx=5,"SMTP"), bytes=case(idx=1,45200,idx=2,23100,idx=3,18700,idx=4,8400,idx=5,4600) | table protocol bytes'},
                            {'title': 'Bandwidth Over Time', 'type': 'chart', 'chart_type': 'line',
                             'search': '| makeresults count=24 | streamstats count as hour | eval _time=relative_time(now(), "-24h+".(hour-1)."h"), inbound_mb=round(random()%500+200), outbound_mb=round(random()%300+100) | table _time inbound_mb outbound_mb'},
                        ]
                    },
                    {
                        'panels': [
                            {'title': 'Top Blocked Sources', 'type': 'table',
                             'search': '| makeresults count=5 | streamstats count as idx | eval src_ip=case(idx=1,"203.0.113.45",idx=2,"198.51.100.23",idx=3,"192.0.2.17",idx=4,"203.0.113.89",idx=5,"198.51.100.56"), country=case(idx=1,"CN",idx=2,"RU",idx=3,"BR",idx=4,"KR",idx=5,"IN"), blocked_count=case(idx=1,4521,idx=2,3892,idx=3,2156,idx=4,1843,idx=5,1205), last_seen=case(idx=1,"2 min ago",idx=2,"5 min ago",idx=3,"12 min ago",idx=4,"18 min ago",idx=5,"25 min ago") | table src_ip country blocked_count last_seen'},
                        ]
                    },
                ]
            },
        ]
    },
}
