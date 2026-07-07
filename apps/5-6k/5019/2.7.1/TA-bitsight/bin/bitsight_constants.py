from bitsight_data_collectors import alerts, findings, graph, company, risk_vector_data, d_h_s, findings_summary, remediations # noqa

"""
This is a map of endpoints with their corresponding URL and data collection functions.

FORMAT:
{
    <endpoint_name>:
        {
            'url': <corresponding_url>,
            'function': <corresponding_function>
        }
}
"""

ENDPOINT_DISPATHCER = {
    'alerts': {'url': 'v2/alerts/', 'function': alerts},
    'findings': {'url': 'v1/companies/{0}/findings', 'function': findings},
    'graph_data': {'url': 'v1/companies/{0}/graph_data', 'function': graph},
    'companies': {'url': 'v1/companies/{0}', 'function': company},
    'diligence_statistics': {'url': 'v1/companies/{0}/diligence/statistics', 'function': risk_vector_data},
    'industries_statistics': {'url': 'v1/companies/{0}/industries/statistics', 'function': risk_vector_data},
    'observations_statistics': {'url': 'v1/companies/{0}/observations/statistics', 'function': risk_vector_data},
    'diligence_historical-statistics': {'url': 'v1/companies/{0}/diligence/historical-statistics', 'function': d_h_s},
    'findings_summary': {'url': 'v1/companies/{0}/findings/summary', 'function': findings_summary},
    'remediations': {'url': 'ratings/v1/remediations', 'function': remediations}
}
