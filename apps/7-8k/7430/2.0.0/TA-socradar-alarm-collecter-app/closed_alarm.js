function closeIncident(alarmId) {
  const status = document.getElementById('status_' + alarmId).value;
  const comments = document.getElementById('comments_' + alarmId).value;

  const endpoint = '/servicesNS/admin/your_app_name/your_custom_endpoint';
  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alarm_id: alarmId, status: status, comments: comments })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      alert(`Alarm ${alarmId} status updated successfully.`);
      location.reload();
    } else {
      alert(`Failed to update alarm ${alarmId}: ${data.message}`);
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert(`An unexpected error occurred for alarm ${alarmId}.`);
  });
}

