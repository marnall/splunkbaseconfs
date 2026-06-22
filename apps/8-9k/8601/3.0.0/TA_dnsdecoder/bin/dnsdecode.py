#!/usr/bin/env python3
"""
Splunk Custom Search Command: dnsdecode
Decodes Base64-encoded DNS wire-format messages.

Usage in SPL:
    ... | dnsdecode field=dns_answer
"""

import sys
import os

# Add the app's lib directory for splunklib AND dnspython
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))

import base64
import json

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import dns.message
import dns.rdatatype
import dns.rcode
import dns.opcode
import dns.flags
import dns.rdataclass


@Configuration()
class DnsDecodeCommand(StreamingCommand):
    """Decodes Base64-encoded DNS wire-format messages."""

    field = Option(
        doc='Field containing the Base64-encoded DNS message',
        require=True
    )

    def stream(self, records):
        field_name = self.field

        for record in records:
            raw_value = record.get(field_name, '')

            if not raw_value or not raw_value.strip():
                record['dns_decode_status'] = 'error'
                record['dns_error'] = 'empty_field'
                yield record
                continue

            try:
                wire_data = base64.b64decode(raw_value)
                msg = dns.message.from_wire(wire_data)
            except Exception as e:
                record['dns_decode_status'] = 'error'
                record['dns_error'] = str(e)
                yield record
                continue

            # Header
            record['dns_id'] = str(msg.id)
            record['dns_opcode'] = dns.opcode.to_text(msg.opcode())
            record['dns_rcode'] = dns.rcode.to_text(msg.rcode())
            record['dns_flags'] = dns.flags.to_text(msg.flags)
            record['dns_is_response'] = str(bool(msg.flags & dns.flags.QR))
            record['dns_authoritative'] = str(bool(msg.flags & dns.flags.AA))
            record['dns_truncated'] = str(bool(msg.flags & dns.flags.TC))

            # Question
            questions = []
            for q in msg.question:
                questions.append({
                    'name': str(q.name),
                    'type': dns.rdatatype.to_text(q.rdtype),
                    'class': dns.rdataclass.to_text(q.rdclass),
                })
            record['dns_question_count'] = str(len(questions))
            if questions:
                record['dns_query_name'] = questions[0]['name']
                record['dns_query_type'] = questions[0]['type']

            # Answers
            answers = []
            for rrset in msg.answer:
                for rdata in rrset:
                    answers.append({
                        'name': str(rrset.name),
                        'type': dns.rdatatype.to_text(rrset.rdtype),
                        'ttl': int(rrset.ttl),
                        'data': str(rdata),
                    })
            record['dns_answer_count'] = str(len(answers))
            record['dns_answers'] = json.dumps(answers)

            for i, ans in enumerate(answers[:10]):
                record['dns_answer_%d_name' % i] = ans['name']
                record['dns_answer_%d_type' % i] = ans['type']
                record['dns_answer_%d_ttl' % i] = str(ans['ttl'])
                record['dns_answer_%d_data' % i] = ans['data']

            # Authority
            authority = []
            for rrset in msg.authority:
                for rdata in rrset:
                    authority.append({
                        'name': str(rrset.name),
                        'type': dns.rdatatype.to_text(rrset.rdtype),
                        'ttl': int(rrset.ttl),
                        'data': str(rdata),
                    })
            record['dns_authority_count'] = str(len(authority))
            if authority:
                record['dns_authority'] = json.dumps(authority)

            # Additional
            additional = []
            for rrset in msg.additional:
                for rdata in rrset:
                    additional.append({
                        'name': str(rrset.name),
                        'type': dns.rdatatype.to_text(rrset.rdtype),
                        'data': str(rdata),
                    })
            record['dns_additional_count'] = str(len(additional))
            if additional:
                record['dns_additional'] = json.dumps(additional)

            record['dns_decode_status'] = 'success'
            yield record


dispatch(DnsDecodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
