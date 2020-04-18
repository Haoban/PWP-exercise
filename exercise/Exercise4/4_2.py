import requests

URL = "https://pwpcourse.eu.pythonanywhere.com"

def check_room(s, room_href):
    resp = s.get(URL + room_href)
    body = resp.json()
    if body["content"] is not None:
        print("****************************")
        print(body["handle"])
        print("****************************")
        
    else:
    # print(body["handle"])
    # if body["item"]:
    #     print(body)
    # else:
        next_room_hrefs = get_next_rooms(body["@controls"])
        if next_room_hrefs is None:
            pass
        for a in next_room_hrefs:
            check_room(s,a)

def get_next_rooms(centre):
    result = []
    dirs = ["maze:south","maze:east"]
    for direct in dirs:
        try:
            result.append(centre[direct]["href"])
        except KeyError:
            pass
    return result
    # print(n,e,w,s)
    # for direc in (n,e,w,s):
    #     if direc:
    #         result.append(direc["href"])

with requests.Session() as s:
    s.headers.update({"Accept": "application/vnd.mason+json"})
    resp = s.get(URL+"/api/")
    if resp.status_code != 200:
        print("Unable to access API.")
    else:
        body = resp.json()
        print(body)
        entrance_href = body["@controls"]["maze:entrance"]["href"]
        check_room(s,entrance_href)

        