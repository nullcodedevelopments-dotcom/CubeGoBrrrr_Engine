import json

class Config:
  @staticmethod
  def loadData(filename, *segments):
    # checks for file type to get the correct path
    if isinstance(segments[0], (list,tuple)):
      segments = segments[0]
    
    with open(filename, "r") as file:
      data = json.load(file)
    # loops through the segment to get the final json
    main = data
    path = segments
    for i in segments:
      main = main[i]
    # path is the segmdnts list and main is the requested data
    return [path, main]
  
  @staticmethod
  def saveData(filename, obj):
    path = obj[0]
    data = obj[1]
    
    with open(filename, "r") as file:
      full_data = json.load(file)
    
    # if whole json is chnaged then update it whole
    if not path:
      full_data = data
    else:
      current = full_data
      for i in path[:-1]:
        current = current[i]
      current[path[-1]] = data
      
    with open(filename, "w") as file:
      json.dump(full_data, file, indent=4)

# Example Usage
if __name__ == "__main__":
  tup = ["logging_types", "calculation_types", "vector_operations"]
  data = Config.loadData("config.json", tup)
  
  data[1]["enabled"] = True
  Config.saveData("config.json",data)