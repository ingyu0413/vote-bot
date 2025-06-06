from datetime import datetime
import json

with open("data.json", "r") as fd:
    data = json.load(fd)

election_name = data["name"]
election_rule = data["rule"]
election_position = data["position"]
election_number = data["number"]
election_term = data["term"]
election_server_id = data["server_id"]
election_server_name = data["server_name"]
voter = {
    "start": datetime.strptime(data["date"]["voter"]["start"], "%Y-%m-%dT%H:%M:%S+09:00"),
    "end": datetime.strptime(data["date"]["voter"]["end"], "%Y-%m-%dT%H:%M:%S+09:00")
}
candidate = {
    "start": datetime.strptime(data["date"]["candidate"]["start"], "%Y-%m-%dT%H:%M:%S+09:00"),
    "end": datetime.strptime(data["date"]["candidate"]["end"], "%Y-%m-%dT%H:%M:%S+09:00")
}
resigncand = {
    "start": datetime.strptime(data["date"]["resigncand"]["start"], "%Y-%m-%dT%H:%M:%S+09:00"),
    "end": datetime.strptime(data["date"]["resigncand"]["end"], "%Y-%m-%dT%H:%M:%S+09:00")
}
electionpre = {
    "start": datetime.strptime(data["date"]["electionpre"]["start"], "%Y-%m-%dT%H:%M:%S+09:00"),
    "end": datetime.strptime(data["date"]["electionpre"]["end"], "%Y-%m-%dT%H:%M:%S+09:00")
}
electionmain = {    
    "start": datetime.strptime(data["date"]["electionmain"]["start"], "%Y-%m-%dT%H:%M:%S+09:00"),
    "end": datetime.strptime(data["date"]["electionmain"]["end"], "%Y-%m-%dT%H:%M:%S+09:00")
}
condition = {
    "voter": data["condition"]["voter"],
    "candidate": data["condition"]["candidate"],
}