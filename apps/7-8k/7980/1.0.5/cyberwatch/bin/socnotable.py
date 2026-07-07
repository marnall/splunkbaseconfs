#!/usr/bin/env python

import os
import sys
import json
import time
import splunk.rest as rest
import logging
import traceback
from datetime import datetime

def get_next_incident_number():
    """Generate next unique incident number in ascending order"""
    try:
        # Path for storing the last incident number and queue
        inc_file = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'last_incident.json')
        lock_file = inc_file + '.lock'
        transaction_log = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'apps', 'cyberwatch', 'static', 'incident_transactions.log')
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(inc_file), exist_ok=True)
        os.makedirs(os.path.dirname(transaction_log), exist_ok=True)
        
        # Initialize last_incident.json if it doesn't exist
        if not os.path.exists(inc_file):
            try:
                with open(inc_file, 'w') as f:
                    json.dump({'last_number': 0}, f)
            except Exception as e:
                logging.error(f"Failed to initialize incident file: {str(e)}")
                # Try to recover by reading existing incidents
                last_number = 0
                try:
                    with open(os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'socnotable.json'), 'r') as f:
                        for line in f:
                            try:
                                incident = json.loads(line)
                                if incident.get('inc_number', '').startswith('INC-'):
                                    num = int(incident['inc_number'].split('-')[1])
                                    last_number = max(last_number, num)
                            except:
                                continue
                    with open(inc_file, 'w') as f:
                        json.dump({'last_number': last_number}, f)
                except:
                    pass
        
        # Generate a unique request ID
        request_id = f"{int(time.time())}_{os.getpid()}_{hash(str(time.time_ns()))}"
        
        # Log the start of transaction
        with open(transaction_log, 'a') as f:
            f.write(json.dumps({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                "request_id": request_id,
                "action": "start_transaction",
                "pid": os.getpid()
            }) + '\n')
            
        # Run cleanup after writing to transaction log
        try:
            cleanup_logs(2000)
        except Exception as cleanup_error:
            logging.error(f"Failed to cleanup logs: {str(cleanup_error)}")
        
        max_retries = 10
        retry_count = 0
        backoff_time = 0.1  # Initial backoff time
        
        while retry_count < max_retries:
            try:
                # Remove stale lock file if it exists
                if os.path.exists(lock_file):
                    try:
                        lock_age = time.time() - os.path.getctime(lock_file)
                        if lock_age > 30:  # Lock older than 30 seconds is considered stale
                            os.remove(lock_file)
                        else:
                            with open(lock_file, 'r') as f:
                                pid = int(f.read().strip())
                                if not os.path.exists(f'/proc/{pid}') and not os.path.exists(f'C:\\Windows\\System32\\{pid}.pid'):
                                    os.remove(lock_file)
                    except:
                        if os.path.exists(lock_file):
                            try:
                                os.remove(lock_file)
                            except:
                                pass
                
                # Try to create lock file with exclusive access
                try:
                    with open(lock_file, 'x') as f:
                        f.write(str(os.getpid()))
                except FileExistsError:
                    retry_count += 1
                    time.sleep(backoff_time)
                    backoff_time *= 1.5  # Exponential backoff
                    continue
                
                try:
                    # Read the current incident number with file locking
                    try:
                        with open(inc_file, 'r') as f:
                            data = json.load(f)
                            last_number = data.get('last_number', 0)
                    except:
                        # If reading fails, try to recover from socnotable.json
                        last_number = 0
                        try:
                            with open(os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'socnotable.json'), 'r') as f:
                                for line in f:
                                    try:
                                        incident = json.loads(line)
                                        if incident.get('inc_number', '').startswith('INC-'):
                                            num = int(incident['inc_number'].split('-')[1])
                                            last_number = max(last_number, num)
                                    except:
                                        continue
                        except:
                            pass
                    
                    # Increment and save atomically
                    next_number = last_number + 1
                    temp_file = inc_file + '.tmp'
                    
                    try:
                        # Write to temp file first
                        with open(temp_file, 'w') as f:
                            json.dump({'last_number': next_number}, f)
                        
                        # Atomic replace
                        os.replace(temp_file, inc_file)
                        
                        # Log the successful transaction
                        with open(transaction_log, 'a') as f:
                            f.write(json.dumps({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                "request_id": request_id,
                                "action": "number_generated",
                                "number": next_number
                            }) + '\n')
                        
                        # Format and return incident number
                        return f"INC-{next_number:06d}"
                        
                    except Exception as e:
                        logging.error(f"Failed to save incident number: {str(e)}")
                        if os.path.exists(temp_file):
                            try:
                                os.remove(temp_file)
                            except:
                                pass
                        raise
                    
                finally:
                    # Cleanup: Remove lock file
                    try:
                        if os.path.exists(lock_file):
                            with open(lock_file, 'r') as f:
                                pid = int(f.read().strip())
                                if pid == os.getpid():
                                    os.remove(lock_file)
                    except:
                        if os.path.exists(lock_file):
                            try:
                                os.remove(lock_file)
                            except:
                                pass
            
            except Exception as e:
                logging.error(f"Error in incident number generation: {str(e)}")
                retry_count += 1
                time.sleep(backoff_time)
                backoff_time *= 1.5
                continue
        
        # If we reach here, we've exhausted retries
        # Instead of returning INC-ERROR, let's try one last recovery attempt
        try:
            # Read the last incident from socnotable.json
            last_number = 0
            with open(os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'socnotable.json'), 'r') as f:
                for line in f:
                    try:
                        incident = json.loads(line)
                        if incident.get('inc_number', '').startswith('INC-'):
                            num = int(incident['inc_number'].split('-')[1])
                            last_number = max(last_number, num)
                    except:
                        continue
            
            # Generate next number and try to save
            next_number = last_number + 1
            try:
                with open(inc_file, 'w') as f:
                    json.dump({'last_number': next_number}, f)
            except:
                pass
            
            return f"INC-{next_number:06d}"
            
        except Exception as e:
            logging.error(f"Final recovery attempt failed: {str(e)}")
            # If all else fails, use timestamp + random number as last resort
            timestamp = int(time.time())
            random_num = hash(str(time.time_ns())) % 1000
            return f"INC-{timestamp}{random_num:03d}"
            
    except Exception as e:
        logging.error(f"Fatal error in incident number generation: {str(e)}")
        # Last resort: use timestamp + random number
        timestamp = int(time.time())
        random_num = hash(str(time.time_ns())) % 1000
        return f"INC-{timestamp}{random_num:03d}"

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for logs"""
    def format(self, record):
        try:
            # Parse the message if it's a JSON string
            if isinstance(record.msg, str):
                msg_dict = json.loads(record.msg)
                if msg_dict.get('action') == 'socnotable_received' and 'data' in msg_dict:
                    data = msg_dict['data']
                    config = data.get('configuration', {})
                    results_file = data.get('results_file', '')
                    
                    # Check if results file exists
                    if not os.path.exists(results_file):
                        return None
                    
                    # Read and process the CSV file
                    import csv
                    import gzip
                    
                    # Create log file path
                    log_file = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'socnotable.json')
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(log_file), exist_ok=True)
                    
                    # Track processed rows to avoid duplicates
                    processed_rows = set()
                    
                    # Process each row and write directly to file
                    with gzip.open(results_file, 'rt', encoding='utf-8') as gz_file:
                        csv_reader = csv.DictReader(gz_file)
                        for row in csv_reader:
                            # Create a unique key for this row
                            row_key = json.dumps(row, sort_keys=True)
                            if row_key in processed_rows:
                                continue
                            processed_rows.add(row_key)
                            
                            # Filter out __mv_* fields from the row
                            filtered_row = {k: v for k, v in row.items() if not k.startswith('__mv_')}
                            
                            # Generate unique incident number
                            inc_number = get_next_incident_number()
                            
                            # Create log entry
                            log_entry = {
                                "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                "inc_number": inc_number,
                                "action": msg_dict.get('action'),
                                "owner": 'unassigned',
                                "results_file": results_file,
                                "results_link": data.get('results_link'),
                                "search_uri": data.get('search_uri'),
                                "server_host": data.get('server_host'),
                                "server_uri": data.get('server_uri'),
                                "session_key": data.get('session_key'),
                                "sid": data.get('sid'),
                                "app": data.get('app'),
                                "search_name": data.get('search_name'),
                                "rule_title": data.get('search_name'),
                                "rule_description": config.get('rule_description'),
                                "severity": config.get('severity'),
                                "group": config.get('group'),
                                "killchain": config.get('killchain'),
                                "mitreattack": config.get('mitreattack'),
                                "cis": config.get('cis'),
                                "status": config.get('status'),
                                "security_domain": config.get('security_domain'),
                                "notable_title_field": config.get('notable_title_field', ''),
                                "title": f"{data.get('search_name', '')} - {filtered_row.get(config.get('notable_title_field', ''), '')}",
                                "results": filtered_row
                            }
                            
                            # Write to file
                            with open(log_file, 'a') as f:
                                f.write(json.dumps(log_entry) + '\n')
                            
                            # Run cleanup after writing logs
                            try:
                                cleanup_logs(2000)
                            except Exception as cleanup_error:
                                logging.error(f"Failed to cleanup logs: {str(cleanup_error)}")
                    
                    # Return None since we've handled the logging directly
                    return None
                
                # For non-notable events, return the original message
                return json.dumps(msg_dict)
            
            # For non-JSON messages, return as is
            return record.msg
            
        except Exception as e:
            # Log any formatting errors
            try:
                error_log = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'apps', 'cyberwatch', 'static', 'formatter_errors.log')
                os.makedirs(os.path.dirname(error_log), exist_ok=True)
                with open(error_log, 'a') as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "record_msg": record.msg if hasattr(record, 'msg') else None,
                        "results_file": results_file if 'results_file' in locals() else None
                    }) + '\n')
            except:
                pass
            return str(e)

class LogFilter(logging.Filter):
    """Filter out specific log messages"""
    def filter(self, record):
        # Skip logs about starting event creation and session key not found
        if isinstance(record.msg, str):
            msg_dict = json.loads(record.msg)
            if msg_dict.get('action') == 'create_notable_event' and msg_dict.get('status') == 'starting':
                return False
            if msg_dict.get('action') == 'get_session_key' and msg_dict.get('status') == 'failed':
                return False
        return True

def setup_logging():
    """Configure logging for the script with JSON formatting"""
    # Create console handler for non-notable events
    console_handler = logging.StreamHandler(sys.stderr)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Create file handler for notable events
    log_file = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk', 'socnotable.json')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(LogFilter())
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def write_event(session_key, event_data):
    """Write event directly to index using /services/receivers/simple"""
    try:
        response, content = rest.simpleRequest(
            '/services/receivers/simple?sourcetype=notable&index=soc_notable',
            sessionKey=session_key,
            method='POST',
            postargs=event_data,
            raiseAllErrors=True
        )
        return True
    except Exception as e:
        logging.error(json.dumps({
            "error": str(e),
            "action": "write_event",
            "status": "failed"
        }))
        return False

def create_notable_event(settings):
    """Create notable events in SOC indexes"""
    try:
        setup_logging()
        logging.info(json.dumps({
            "action": "create_notable_event",
            "status": "starting"
        }))

        # Read configuration from stdin
        config = json.loads(sys.stdin.read())
        logging.info(json.dumps({
            "action": "socnotable_received",
            "data": config
        }))

        # Get session key from environment
        session_key = os.environ.get('SPLUNK_SESSION_KEY')
        if not session_key:
            logging.error(json.dumps({
                "error": "Session key not found",
                "action": "get_session_key",
                "status": "failed"
            }))
            return False

        # Extract parameters
        search_name = config.get('search_name', 'Unknown Search')
        results = config.get('results', [])
        configuration = config.get('configuration', {})

        # Create event data
        event_data = {
            'rule_name': configuration.get('rule_title', search_name),
            'rule_description': configuration.get('rule_description', ''),
            'severity': configuration.get('severity', 'low'),
            'security_domain': configuration.get('security_domain', 'endpoint'),
            'status': 'new',
            'source': 'Correlation Search',
            '_time': str(int(time.time())),
            'mitreattack': configuration.get('mitreattack', ''),
            'killchain': configuration.get('killchain', ''),
            'cis20': configuration.get('cis20', ''),
            'group': 'correlation',
            'notable_title_field': configuration.get('notable_title_field', '')
        }

        # Add search results if available
        if results:
            event_data['results'] = results

        # Write event
        logging.info(json.dumps({
            "action": "writing_event",
            "data": event_data
        }))

        if write_event(session_key, json.dumps(event_data)):
            logging.info(json.dumps({
                "action": "create_notable_event",
                "status": "success"
            }))
            return True
        else:
            logging.error(json.dumps({
                "action": "create_notable_event",
                "status": "failed",
                "error": "Failed to write event"
            }))
            return False

    except Exception as e:
        logging.error(json.dumps({
            "action": "create_notable_event",
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc()
        }))
        return False

def handle_getinfo():
    """Handle getinfo request from Splunk"""
    logging.info(json.dumps({
        "action": "handle_getinfo",
        "status": "success"
    }))
    return {
        "type": "reporting",
        "generating": False,
        "streaming": True,
        "retainsevents": True,
        "supports_getinfo": True,
        "supports_rawargs": True,
        "supports_multivalues": True
    }

def cleanup_logs(max_lines=2000):
    """Cleanup incident_transactions.log file if it exceeds the maximum number of lines
    Args:
        max_lines (int): Maximum number of lines to keep in log files (default: 2000)
    Returns:
        dict: Status of cleanup operation for each file
    """
    status = {}
    try:
        # Only handle incident_transactions.log
        log_path = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'apps', 'cyberwatch', 'static', 'incident_transactions.log')
        
        try:
            if not os.path.exists(log_path):
                status["transactions"] = {"status": "skipped", "reason": "file_not_found"}
                return status

            # Clean up any stale temporary files first
            temp_path = f"{log_path}.tmp"
            backup_path = f"{log_path}.bak"
            
            for stale_file in [temp_path, backup_path]:
                try:
                    if os.path.exists(stale_file):
                        os.remove(stale_file)
                except:
                    pass

            # Read all lines in memory with explicit file closing
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                status["transactions"] = {"status": "error", "error": f"Failed to read file: {str(e)}"}
                return status

            total_lines = len(lines)
            if total_lines <= max_lines:
                status["transactions"] = {"status": "skipped", "reason": "under_limit", "lines": total_lines}
                return status

            # Keep only the last max_lines
            lines_to_keep = lines[-max_lines:]
            lines_removed = total_lines - max_lines

            # Create backup first
            try:
                import shutil
                shutil.copy2(log_path, backup_path)
            except Exception as backup_error:
                pass

            # Write to temporary file
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines_to_keep)

                # Verify temp file
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    # Force close any open handles
                    import gc
                    gc.collect()

                    # Replace original file with temp file
                    try:
                        # On Windows, we need to remove the target file first
                        if os.path.exists(log_path):
                            os.remove(log_path)
                        os.rename(temp_path, log_path)

                        # Write cleanup status to the new file
                        with open(log_path, 'a') as f:
                            f.write(json.dumps({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                "action": "log_cleanup",
                                "log_file": "transactions",
                                "lines_removed": lines_removed,
                                "lines_kept": len(lines_to_keep)
                            }) + '\n')

                        status["transactions"] = {
                            "status": "success",
                            "lines_before": total_lines,
                            "lines_after": len(lines_to_keep),
                            "lines_removed": lines_removed
                        }

                    except Exception as replace_error:
                        # If replace fails, restore from backup
                        if os.path.exists(backup_path):
                            try:
                                if os.path.exists(log_path):
                                    os.remove(log_path)
                                os.rename(backup_path, log_path)
                            except:
                                pass
                        raise replace_error

            except Exception as e:
                # Restore from backup if anything fails
                if os.path.exists(backup_path):
                    try:
                        if os.path.exists(log_path):
                            os.remove(log_path)
                        os.rename(backup_path, log_path)
                    except:
                        pass
                status["transactions"] = {"status": "error", "error": str(e)}

            finally:
                # Clean up temporary files
                for temp_file in [temp_path, backup_path]:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass

        except Exception as e:
            status["transactions"] = {"status": "error", "error": str(e)}

    except Exception as e:
        status["global"] = {"status": "error", "error": str(e)}

    return status

def cleanup_logs_main():
    """Main function to run log cleanup independently"""
    try:
        # Setup basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Run cleanup with default 2000 lines limit
        status = cleanup_logs(2000)

        # Print results
        print(json.dumps(status, indent=2))
        return 0

    except Exception as e:
        print(f"Error during cleanup: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    setup_logging()
    
    # Check if this is a getinfo request
    if len(sys.argv) > 1 and sys.argv[1] == '--getinfo':
        info = handle_getinfo()
        print(json.dumps(info))
        sys.exit(0)
    
    # Check if this is a cleanup request
    if len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        sys.exit(cleanup_logs_main())
        
    # Normal alert action execution
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            settings = json.load(f)
    else:
        settings = dict()

    if not create_notable_event(settings):
        sys.exit(3) 