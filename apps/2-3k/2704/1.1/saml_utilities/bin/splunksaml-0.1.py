import re,sys,time,splunk.Intersplunk
import urllib           # urldecoding
import zlib             # uncompressing
import base64
import xml.dom.minidom	# XML parsing
import logging, logging.handlers

LOGFILE = '/opt/splunk/var/log/splunk/saml_utilities.log'
LOGLEVEL = 'DEBUG'

# xml namespaces for xpath
ns = {'saml2p': '{urn:oasis:names:tc:SAML:2.0:protocol}',
       'saml2': '{urn:oasis:names:tc:SAML:2.0:assertion}',
          'ds': '{http://www.w3.org/2000/09/xmldsig#}',
         'xs' : '{http://www.w3.org/2001/XMLSchema}',
         'ec' : '{http://www.w3.org/2001/10/xml-exc-c14n#}',
        'xsi' : '{http://www.w3.org/2001/XMLSchema-instance}',
     }

# xpath strings
xp_subject_nameid     = '{saml2}Assertion/{saml2}Subject/{saml2}NameID'.format(**ns)
xp_attributestatement = '{saml2}Assertion/{saml2}AttributeStatement'.format(**ns)
xp_status_code        = '{saml2p}Status/{saml2p}StatusCode'.format(**ns)
xp_status_message     = '{saml2p}Status/{saml2p}StatusMessage'.format(**ns)
xp_signature_method   = '{ds}Signature/{ds}SignedInfo/{ds}SignatureMethod'.format(**ns)

def setup_logger():
	logger = logging.getLogger('SAML_Utilities')
	logger.setLevel(logging.DEBUG)
	file_handler = logging.handlers.RotatingFileHandler(LOGFILE)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return(logger)

def set_loglevel(logger,LOGLEVEL):
#	logger.debug('set_level()')
	if LOGLEVEL == 'DEBUG':
		logger.setLevel(logging.DEBUG)
	if LOGLEVEL == 'INFO':
		logger.setLevel(logging.INFO)
	if LOGLEVEL == 'WARN':
		logger.setLevel(logging.WARN)
	if LOGLEVEL == 'ERROR':
		logger.setLevel(logging.ERROR)
	return()

def xml_untidy(xmlDocument):
#	logger.debug("xml_untidy()")
	xmlString = re.sub('\s+',' ',xmlDocument)
	xmlString = re.sub('\n+','',xmlString)
	return(xmlString)

def decode_response(response,pretty_xml=False):
#	logger.debug("decode_response()")
	#	SAMLResponse is a base64 encoded XML document
	#		Parameters
	#			response   : base64 encoded SAML Assertion XML string
	#			pretty_xml : Return pretty/tidy SAMLAssertion XML (Multi-line, indented) (Default is False)
	#		Return
	#			The decoded SAML Assertion if successful, "Error decoding SAML Response" on failure.
	#
	decompressed_SAMLResponse = ""
	SAMLResponseXML           = ""
	try:
		urldecoded_SAMLResponse   = urllib.unquote(response)
		b64decoded_SAMLResponse   = base64.b64decode(urldecoded_SAMLResponse)
		SAMLResponseXML           = xml_untidy(b64decoded_SAMLResponse)
		#logger.debug(SAMLResponseXML)
	except:
		if SAMLResponseXML is None:
			logger.error("Error decoding SAML Response")
			return()
	else:
		return SAMLResponseXML

def decode_authnrequest(authn_request,pretty_xml=False):
	#	AuthnRequest is a deflated, base64 encoded and url-escaped XML document
	#		Parameters
	#			authn_request : deflated, base64 encoded and url-escaped SAML AuthnRequest XML string
	#			pretty_xml    : Return pretty/tidy SAMLRequest XML (Multi-line, indented) (Default is False)
	#		Return
	#			The decoded AuthnRequest if successful, "Error decoding SAMLRequest" on failure.
	#
	decompressed_SAMLRequest = ""
	try:
		urldecoded_SAMLRequest   = urllib.unquote(authn_request)
		#urldecoded_SAMLRequest  = urldecoded_SAMLRequest.strip('SAMLRequest=')
		b64decoded_SAMLRequest   = base64.b64decode(urldecoded_SAMLRequest)
		decompressed_SAMLRequest = zlib.decompress(b64decoded_SAMLRequest, -15)
	except:
		if decompressed_SAMLRequest is None:
			logger.error("Error decoding SAMLRequest")
			return()

	else:
		if pretty_xml:
			_xml_doc = xml.dom.minidom.parseString(decompressed_SAMLRequest)
			xml_pretty = _xml_doc.toprettyxml(indent='\t')
			return(xml_pretty)
		else:
			return decompressed_SAMLRequest
			
def dosaml(results,settings):
#	logger.debug("dosaml()")
	try:
		fields, argvals = splunk.Intersplunk.getKeywordsAndOptions()
		saml_type       = argvals.get("type", "authnrequest")
		pretty_xml      = argvals.get("format", "raw")
		extract_fields  = argvals.get("extract", True)
    
		if saml_type == "authnrequest":
			samlfunct = decode_authnrequest
		if saml_type == "response":
			samlfunct = decode_response

#		logger.debug("TYPE: " + saml_type)

		for _result in results:
			for _field in fields:
				if _field in _result:
					if pretty_xml == "tidy":
						_result[_field] = samlfunct(_result[_field],True) # update specified field with decoded data	
						if (extract_fields):
							_result.update(do_extract_fields(_result[_field], saml_type)) # create new fields with SAML attributes
					else:
						_result[_field] = samlfunct(_result[_field]) # update specified field with decoded data
						if (extract_fields):
							_result.update(do_extract_fields(_result[_field], saml_type)) # create new fields with SAML attributes

		#append extracted_saml_fields to results
		splunk.Intersplunk.outputResults(results)
    
	except:
		import traceback
		stack   = traceback.format_exc()
		results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))
		logger.error("Error : " + str(stack))

def do_extract_fields(SAMLMessage,saml_type):
#	logger.debug("do_extract_fields()")
	extracted_fields = ""
	if saml_type == "authnrequest":
		return( saml_authnrequest_extractFields(SAMLMessage) )
	if saml_type == "response":
		return( saml_response_extractFields(SAMLMessage) )
	return(False)

def saml_response_extractFields(response):
#	logger.debug("saml_response_extractFields()")
	try:
		saml_response = {}
		import xml.etree.ElementTree as xml
		root = xml.fromstring(response)	
		for attrib in root.attrib:
			saml_response['SAMLResponse_' + attrib]               = root.attrib.get(attrib).encode()

		saml_response['SAMLResponse_Status']                          = root.find(xp_status_code).get('Value').encode()

		status_message = root.find(xp_status_message)
		if status_message != None:
			saml_response['SAMLResponse_Message']                 = status_message.text.encode()
	
		name_id = root.find(xp_subject_nameid)
    		if name_id != None:
       			saml_response['SAMLResponse_Attribute_NameID']        = name_id.text.encode()

		signature_method = root.find(xp_signature_method)
		if signature_method != None:	
			saml_response['SAMLResponse_SignatureMethod']         = signature_method.text
			
		attribute_statement = root.find(xp_attributestatement)
		if attribute_statement != None:
			logger.debug("Attribute Statement")
			for el in attribute_statement:
				name  = el.get('Name') or el.tag
				logger.debug(name)
				saml_response['SAMLResponse_Attribute_' + name] = "NONE"

		return(saml_response)
	except:
		return({})

def saml_authnrequest_extractFields(authnrequest):
	logger.debug("saml_authnrequest_extractFields()")
	try:
		DOMTree = xml.dom.minidom.parseString(authnrequest)
		saml_document = DOMTree.documentElement
		saml_request = {}

		if (saml_document.getAttribute("xmlns:samlp")):
			saml_request['SAMLRequest_xmlns_samlp']              = saml_document.getAttribute("xmlns:samlp").encode()

		if (saml_document.getAttribute("xmlns:saml")):
			saml_request['SAMLRequest_xmlns_saml']               = saml_document.getAttribute("xmlns:saml").encode()

		if (saml_document.getAttribute("xmlns:ds")):
			saml_request['SAMLRequest_xmlnsds']                  = saml_document.getAttribute("xmlns:ds").encode()

		if (saml_document.getAttribute("xmlns:xenc")):
			saml_request['SAMLRequest_xmlns_xenc']               = saml_document.getAttribute("xmlns:xenc").encode()

		if (saml_document.getAttribute("xmlns:xs")):
			saml_request['SAMLRequest_xmlns_xs']                 = saml_document.getAttribute("xmlns:xs").encode()

		if (saml_document.getAttribute("xmlns:xsi")):
			saml_request['SAMLRequest_xmlns_xsi']                = saml_document.getAttribute("xmlns:xsi").encode()

		if (saml_document.getAttribute("AssertionConsumerServiceURL")):
			saml_request['SAMLRequest_ACSURL']                   = saml_document.getAttribute("AssertionConsumerServiceURL").encode()

		if (saml_document.getAttribute("Destination")):
			saml_request['SAMLRequest_Destination']              = saml_document.getAttribute("Destination").encode()

		if (saml_document.getAttribute("Consent")):
			saml_request['SAMLRequest_Consent']                  = saml_document.getAttribute("Consent").encode()

		if (saml_document.getAttribute("ID")):
			saml_request['SAMLRequest_ID']                       = saml_document.getAttribute("ID").encode()

		if (saml_document.getAttribute("IssueInstant")):
				saml_request['SAMLRequest_Issue_Instant']    = saml_document.getAttribute("IssueInstant").encode()

		if (saml_document.getAttribute("ProtocolBinding")):
			saml_request['SAMLRequest_Protocol_Binding']         = saml_document.getAttribute("ProtocolBinding").encode()

		if (saml_document.getAttribute("Version")):
			saml_request['SAMLRequest_Version']                  = saml_document.getAttribute("Version").encode()

		if (saml_document.getAttribute("ProviderName")):
			saml_request['SAMLRequest_ProviderName']             = saml_document.getAttribute("ProviderName").encode()

		if (saml_document.getElementsByTagName("saml:Issuer")):
			saml_request['SAMLRequest_Issuer_Namespace']         = saml_document.getElementsByTagName("saml:Issuer")[0].getAttribute("xmlns:saml").encode()
			saml_request['SAMLRequest_Issuer']                   = saml_document.getElementsByTagName("saml:Issuer")[0].childNodes[0].data.encode()

		if (saml_document.getElementsByTagName("Issuer")):
			saml_request['SAMLRequest_Issuer_Namespace']         = saml_document.getElementsByTagName("Issuer")[0].getAttribute("xmlns").encode()
			saml_request['SAMLRequest_Issuer']                   = saml_document.getElementsByTagName("Issuer")[0].childNodes[0].data.encode()

		if (saml_document.getAttribute("IsPassive")):
			saml_request['SAMLRequest_IsPassive']                = saml_document.getAttribute("IsPassive").encode()

		if (saml_document.getElementsByTagName("samlp:NameIDPolicy")):
			saml_request['SAMLRequest_NameIDPolicy_AllowCreate'] = saml_document.getElementsByTagName("samlp:NameIDPolicy")[0].getAttribute("AllowCreate").encode()
			saml_request['SAMLRequest_NameIDPolicy_Format']      = saml_document.getElementsByTagName("samlp:NameIDPolicy")[0].getAttribute("Format").encode()

		return(saml_request)
	except:
		return({})

logger = setup_logger()    
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
results = dosaml(results, settings)
