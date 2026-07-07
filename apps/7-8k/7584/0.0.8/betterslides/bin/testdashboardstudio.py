import splunk.rest as rest
from splunk.util import normalizeBoolean
from io import BytesIO
import base64
import json

def export_dashboard_to_png(dashboard_name, namespace, owner, session_key):
  """
  Exports a Splunk Dashboard Studio dashboard to a PNG image.

  Args:
      dashboard_name (str): Name of the dashboard to export.
      namespace (str): Namespace of the dashboard.
      owner (str): Owner of the dashboard.
      session_key (str): Splunk session key.

  Returns:
      bytes: PNG image data or None if an error occurred.

  Raises:
      Exception: If an error occurs during export.
  """
  try:
    # Check if dashboard content can be retrieved (indicates a Studio dashboard)
    dashboard_content = rest.get(
        f"/services/data/dashboards/{namespace}/{owner}/{dashboard_name}",
        sessionKey=session_key
    )
    if not dashboard_content:
      raise Exception("Dashboard not found or not a Studio dashboard")

    # Set file format to PNG
    file_format = "png"

    # Check if PNG export is supported for Studio dashboards
    if "error" in dashboard_content:
      raise Exception(f"Error retrieving dashboard content: {dashboard_content['error']}")
    if not normalizeBoolean(dashboard_content.get("isPNGExportable", False)):
      raise Exception("PNG export is not supported for this dashboard")

    # Use existing logic to handle Studio dashboard export (modify as needed)
    response = rest.post(
        "/services/pdfgen/render",
        sessionKey=session_key,
        data={
            "input-dashboard": dashboard_name,
            "namespace": namespace,
            "owner": owner,
            "type": file_format,
        }
    )

    if response.status != 200:
      raise Exception(f"Error exporting dashboard: {response.reason}")

    # Extract PNG image data from response
    error_message = response.content.get("error_messages")
    if error_message:
      raise Exception(f"Error exporting dashboard: {error_message[0]}")

    png_data = response.content.get("data")
    if not png_data:
      raise Exception("Failed to retrieve PNG data from response")

    return base64.b64decode(png_data)

  except Exception as e:
    print(f"Error exporting dashboard: {str(e)}")
    return None

# Example usage
dashboard_name = "my_dashboard"
namespace = "default"
owner = "-"
session_key = splunk.auth.getSessionKey()  # Get your session key

png_data = export_dashboard_to_png(dashboard_name, namespace, owner, session_key)

if png_data:
  # Use the PNG data (e.g., write to a file)
  with open("dashboard.png", "wb") as f:
    f.write(png_data)
  print("Dashboard exported successfully!")
else:
  print("Failed to export dashboard")
