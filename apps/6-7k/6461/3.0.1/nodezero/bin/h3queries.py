"""GraphQL query definitions for the H3 API."""


class H3Queries:
    @property
    def action_logs_csv_url(self):
        return "query csv($input:OpInput!){action_logs_csv_presigned_url(input:$input)}"

    @property
    def hosts_csv_url(self):
        return "query csv($op_id:String!){hosts_csv_url(input:{op_id:$op_id})}"

    @property
    def pentests_page(self):
        return """
            query PentestsPage($page_input: PageInput) {
                pentests_page(page_input: $page_input) {
                    pentests {
                        ...PentestFragment
                    }
                }
            }

            fragment PentestFragment on Pentest {
                op_id
                op_type
                name
                state
                scheduled_at
                completed_at
                etl_completed_at
                hosts_count
                weaknesses_count
                credentials_count
                impacts_count
            }
        """

    @property
    def weaknesses_csv_url(self):
        return "query csv($op_id:String!){weaknesses_csv_url(input:{op_id:$op_id})}"
