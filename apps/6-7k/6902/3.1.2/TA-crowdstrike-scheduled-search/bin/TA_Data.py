import copy


def create_TA_Data(ta_data, ta_data_sets, collection_ids, status_count, exec_details, log_label, helper):

    #check executions have successfully completed with details
    for result in exec_details:
        if result.get('status') == "DONE" and result.get('status_display') == 'Success':
            result_meta = result.get('result_metadata', {})
            event_count = result_meta.get('result_count', 0)
            run_type    = result.get('execution_metadata', {}).get('unscheduled_execution_type', '')
            #log manual or regular execution type
            if run_type:
                helper.log_info(f'{log_label} Report execution type: {run_type}')

            if event_count == 0:
                helper.log_info(f'{log_label} The report execution {result["id"]} successfully ran but there were no results')

            #append id to collection list and create ta_data dictionary if there were results
            else:
                entry = copy.deepcopy(ta_data)
                entry['Execution_Data'] = result
                execution_id = result['id']
                ta_data_sets[execution_id] = entry
                collection_ids.append(execution_id)
        else:
            result_status = result.get('status', 'unknown')
            status_msg = result.get("status_msg", "unknown")
            result_id = result.get('id', 'unknown')
            helper.log_info(f'{log_label} Non-collectable execution {result_id}: status={result_status}, status_msg={status_msg}')
            status_count[result_status] = status_count.get(result_status, 0) + 1
    if len(status_count) != 0:
        helper.log_info(f'{log_label} Non-collectable execution results overview {status_count}')

    return collection_ids, ta_data_sets
