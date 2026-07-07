def read_file_to_list(filepath):
  """Reads a text file and converts it to a Python list."""
  with open(filepath, "r") as file:
    lines = file.readlines()
    data = (line.strip() for line in lines)
  return list(data)

def update_file_with_list(filepath, list_data):
  """Updates a text file with a Python list."""
  with open(filepath, "w") as file:
    for item in list_data:
      file.write(item + "\n")

def get_definition(filepath):
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("definition = "):
                definition = line.split("=")[1].strip()
                return definition
            
def get_base_url(filepath):
    with open(filepath, "r") as f:
        for line in f:
            if line.startswith("api_url = "):
                base_url = line.split("=")[1].strip()
                if base_url.startswith("http://"):
                    base_url = base_url.replace("http://", "https://")
                return base_url

def get_severity_level(score):
    if score >= 9.0:
        return "Critical"
    elif score >= 7.0:
        return "High"
    elif score >= 4.0:
        return "Medium"
    else:
        return "Low"
