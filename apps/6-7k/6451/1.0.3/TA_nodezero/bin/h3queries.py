class H3Queries:
    @property
    def action_logs_page(self):
        return """query action_logs_page($op_id:String!, $page_num:Int!) { 
                action_logs_count(
                    input: {
                        op_id: $op_id
                    }
                )

                action_logs_page(
                    input: {
                        op_id: $op_id
                    },
                    page_input: {
                        page_num: $page_num
                        page_size: 2500
                    }
                ) {
                    action_logs {
                        ...ActionLogFragment
                    } 
                }
            }


            fragment ActionLogFragment on ActionLog {
                ...ActionLogScalarFragment
                endpoint {
                    ip
                }
            }

            fragment ActionLogScalarFragment on ActionLog { 
                uuid
                entity_type
                start_time
                start_time_iso
                end_time
                end_time_iso
                correlation_id
                cmd
                module_id
                module_name
                module_description
                target_h3_names
                exit_code
                etl_module
                op_id
                op_snapshot_id
                row_created_at
                row_updated_at
            }"""

    @property
    def host_summary_csv(self):
        return "query csv($op_id:String!){host_tabs_csv(input:{op_id:$op_id})}"

    @property
    def op_status(self):
        return """
                query op_tabs {
                op_tabs_page: op_tabs_page(page_input:{
                    page_num:1, 
                    page_size:100, 
                    order_by:"scheduled_timestamp",
                    sort_order:DESC,
                    filter_by:"is_archived",
                    filter_by_in:["false"]

                    filter_by_inputs:[
                        { 
                            field_name: "op_state"
                            values: ["done","canceled"]
                        }
                    ]
                    }) {
                        op_tabs {
                            ...OpTabFragment
                        }
                    }
                }

                fragment OpTabFragment on OpTab {
                    op_name
                    op_state
                    op_id
                    op_type
                    weakness_tabs_count
                    credentials_count
                    host_tabs_count
                    impacts_headline_count
                    scheduled_timestamp
                    completed_timestamp
                }
                """

    @property
    def weakness_csv(self):
        return "query csv($op_id:String!){weakness_tabs_csv(input:{op_id:$op_id})}"
