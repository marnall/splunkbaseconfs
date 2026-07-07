import os
import sys
from wa_constants import *
import logging
import log_helper

libpath = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(libpath, '3rdparty')]
import botocore.session

class WellArchitected(object):
    def __init__(self, kwargs):
        self.session = botocore.session.get_session()
        self.session.user_agent_name = '%s/' % APN_PARTNER_ID + self.session.user_agent_name
        self.client = self.session.create_client(**kwargs)

    def create_workload(self, kwargs):
        try:
            workload = self.client.create_workload(**kwargs)
            return workload
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def create_milestone(self, kwargs):
        try:
            milestone = self.client.create_milestone(**kwargs)
            return milestone
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def list_workloads(self, kwargs):
        try:
            workloads = self._get_workloads(kwargs)
            return workloads
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def list_milestones(self, kwargs):
        try:
            milestones = self._get_milestones(kwargs)
            return milestones
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def list_lens_review_improvements(self, kwargs):
        next_token = None
        try:
            lens_review_improvements = self.client.list_lens_review_improvements(**kwargs)

            if 'NextToken' in lens_review_improvements:
                next_token = lens_review_improvements['NextToken']

            while next_token:
                kwargs['NextToken'] = next_token
                response = self.client.list_lens_review_improvements(**kwargs)
                lens_review_improvements['ImprovementSummaries'].extend(response['ImprovementSummaries'])
                if 'NextToken' not in response:
                    break
                next_token = response['NextToken']
            return lens_review_improvements
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def list_lenses(self, kwargs):
        try:
            response = self._get_lenses(kwargs)
            return response
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def update_workload(self, kwargs):
        try:
            response = self.client.update_workload(**kwargs)
            return response
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def update_answer(self, kwargs):
        try:
            response = self.client.update_answer(**kwargs)
            return response
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def delete_workload(self, kwargs):
        try:
            response = self.client.delete_workload(**kwargs)
            return response
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            print(e)

    def _get_workloads(self, kwargs):
        try:
            response = self.client.list_workloads(**kwargs)
            return response['WorkloadSummaries']
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def _get_milestones(self, kwargs):
        try:
            response = self.client.list_milestones(**kwargs)
            return response['MilestoneSummaries']
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e

    def _get_lenses(self, kwargs):
        try:
            response = self.client.list_lenses(**kwargs)
            return response['LensSummaries']
        except (
            self.client.exceptions.AccessDeniedException,
            self.client.exceptions.ConflictException,
            self.client.exceptions.InternalServerException,
            self.client.exceptions.ResourceNotFoundException,
            self.client.exceptions.ServiceQuotaExceededException,
            self.client.exceptions.ThrottlingException,
            self.client.exceptions.ValidationException
         ) as e:
            raise e
