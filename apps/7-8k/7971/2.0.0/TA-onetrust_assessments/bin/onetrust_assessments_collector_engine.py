
# encoding = utf-8

import requests, json, asyncio, re
from typing import Any, Tuple
from enum import Enum
from datetime import datetime, timedelta

class OneTrustArchivalState(str, Enum):
    ALL = "ALL"
    ARCHIVED = "ARCHIVED"
    NON_ARCHIVED = "NON_ARCHIVED" 

class OneTrustAssessmentsCollector():
    
    ASSESSMENTS_API_ENDPOINT = 'api/assessment/v2/assessments'
    ONETRUST_USERS = 'api/scim/v3/Users'
    FAQ_REGEX = re.compile(r"Frequently\sAsked\sQuestions")
    
    def __init__(self, base_url: str, api_key: str, created_since: str, 
                 archival_state: OneTrustArchivalState = OneTrustArchivalState.NON_ARCHIVED, 
                 template_name: str = '.', page_size: int = 2000, exc_skipped_q: bool = True):
        self.base_url = base_url
        self.api_key = api_key
        self.archival_state = archival_state
        self.page_size = page_size
        self.exc_skipped_q = exc_skipped_q
        try:
            self.filter_from_template = re.compile(template_name)
        except re.error:
            self.filter_from_template = re.compile('.*')
        try:
            self.filter_from_date = datetime.strptime(created_since, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.filter_from_date = datetime.now() - timedelta(days=30)

    async def get_assessment_list(self, page: int = 0) -> Tuple[bool, dict[str, Any]]:
        api_url = f'{self.base_url}/{OneTrustAssessmentsCollector.ASSESSMENTS_API_ENDPOINT}?assessmentArchivalState={self.archival_state.value}&size={self.page_size}&page={page}'
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            return False, {"err": str(e)}

    async def get_assessment_detail(self, assessment_id) -> Tuple[bool, dict[str, "Any"]]:
        esq = "true" if self.exc_skipped_q else "false"
        api_url = f'{self.base_url}/{OneTrustAssessmentsCollector.ASSESSMENTS_API_ENDPOINT}/{assessment_id}/export?ExcludeSkippedQuestion={esq}'
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            return False, {"err": str(e)}
    
    @staticmethod
    def clean_assessment_detail(raw_assessment_detail_json) -> tuple[dict[str, str], dict[str, str]]:
        keep_fields = ["assessmentId", "assessmentNumber", "lastUpdated", "submittedOn", "completedOn", "createdDT", "template",
                       "title", "orgGroup", "createdBy", "responseTitle", "approvalInfo", "respondent", "respondents", "riskLevel",
                       "result", "riskLevel"]
        _Q = [
            {
                "assessmentId": raw_assessment_detail_json['assessmentId'],
                "lastUpdated": raw_assessment_detail_json['lastUpdated'],
                "question": q.get("question").get("content"),
                "questionSeq": q.get("question").get("sequence"),
                "responses": ",".join([ i.get("response", "")
                     for r in q.get("questionResponses", [])
                     for i in r.get("responses", []) 
                ]),
                "description": q.get("question").get("description"),
                "sourceType": "onetrust:assessment:qna",
                "sectionName": h.get("header").get("name")
            }
            for h in raw_assessment_detail_json.get("sections", []) 
            if not OneTrustAssessmentsCollector.FAQ_REGEX.search(
                str(h.get("header", {}).get("name", ""))
            )
            for q in h.get("questions", [])
        ]
        _D = raw_assessment_detail_json
        for key in list(raw_assessment_detail_json.keys()):
            if key not in keep_fields:
                del _D[key]
        _D['sourceType'] = "onetrust:assessment:detail"
        return _D, _Q
    
    async def start(self):
        current_page = 0
        total_pages = 1
        while current_page < total_pages:
            ok, A = await self.get_assessment_list(page=current_page)  # pass page param
            if not ok:
                yield {"err": A}
                return
            total_pages = A.get("page", {}).get("totalPages", 0)
            if total_pages <= 0:
                break
            contents = A.get("content", [])
            if not contents:
                yield {"err": "No data"}
                return
            for item in contents:
                _t = item.get("templateName", "")
                _c = item.get("createDt", "")
                if not self.filter_from_template.search(_t): continue
                try:
                    created_dt = datetime.strptime(_c, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                if created_dt < self.filter_from_date: continue
                item['sourceType'] = "onetrust:assessment:summary"
                yield item
                ok, _g = await self.get_assessment_detail(assessment_id=item.get("assessmentId"))
                if not ok: continue
                _d, _QNA = self.clean_assessment_detail(raw_assessment_detail_json=_g)
                yield _d
                for qna in _QNA:
                    yield qna
            current_page += 1