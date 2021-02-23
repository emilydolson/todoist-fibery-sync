import todoist
import pycurl
import certifi
from io import BytesIO
from urllib.parse import urlencode
import json
from inspect import getframeinfo, stack
import os
get_tasks_query = '[{"command": "fibery.entity/query", "args": {"query": {"q/from": "Strategy and Planning/Task","q/select": ["Strategy and Planning/name",  "fibery/id", {"workflow/state": ["fibery/id", "enum/name"]}, {"Strategy and Planning/Sub-Tasks": {"q/select": ["fibery/id"], "q/limit": "q/no-limit" }}, {"Strategy and Planning/Idea" :["fibery/id","Strategy and Planning/name"]}, {"Strategy and Planning/Parent Task" :["fibery/id","Strategy and Planning/name"]}, {"Todoist/Todoist Task" :["fibery/id","Todoist/Todoist id"]} ], "q/limit": "q/no-limit"}}}]'
get_ideas_query = '[{"command": "fibery.entity/query", "args": {"query": {"q/from": "Strategy and Planning/Idea","q/select": ["Strategy and Planning/name",  "fibery/id", {"workflow/state": ["fibery/id", "enum/name"]}, {"Strategy and Planning/Sub-ideas": {"q/select": ["fibery/id"], "q/limit": "q/no-limit" }}, {"Strategy and Planning/Parent Idea" :["fibery/id","Strategy and Planning/name"]}, {"Todoist/Todoist Project" :["fibery/id","Todoist/Todoist id"]} ], "q/limit": "q/no-limit"}}}]'

if os.path.exists("todoist_secret.txt"):
    td_file = open("todoist_secret.txt")
    todoist_secret = td_file.readlines()[0]
    td_file.close()

if os.path.exists("fibery_token.txt"):
    fb_file = open("fibery_token.txt")
    fibery_token = fb_file.readlines()[0]
    fb_file.close()


api = todoist.TodoistAPI(todoist_secret)
api.sync()
# for project in api.projects.all():
#     print(project)

def validate_result(result):
    if result[0]["success"] != True:
        print("Error:", getframeinfo(stack()[1][0]), result)
        exit()


def make_api_call(post_data):
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://ecode.fibery.io/api/commands")
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.setopt(c.VERBOSE, True)

    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    c.setopt(c.POSTFIELDS, post_data)
    c.setopt(pycurl.HTTPHEADER, ['Authorization: Token ' + fibery_token, 'Content-Type: application/json'])
    c.perform()
    body = buffer.getvalue()
    body = body.decode('iso-8859-1')
    data = json.loads(body)
    # s = json.dumps(data, indent=4, sort_keys=True)
    return data



# tasks = make_api_call(get_tasks_query)
ideas = make_api_call(get_ideas_query)

idea_dict = {}
idea_dict_by_name = {}

for idea in ideas[0]["result"]:
    idea_dict[idea["fibery/id"]] = idea
    idea_dict_by_name[idea["Strategy and Planning/name"]] = idea


def make_new_todoist_project(idea, parent_id="None", parent_todoist_id="None"):
    if parent_todoist_id != "None":
        todoist_project = api.projects.add(idea["Strategy and Planning/name"], parent_id=parent_todoist_id)
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Project", "entity": {{"Todoist/name" : "{todoist_project["name"]}", "Todoist/Todoist id" : "{todoist_project["id"]}", "Todoist/Idea" : {{"fibery/id" : "{idea["fibery/id"]}"}}, "Todoist/Parent Project" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
    else:
        todoist_project = api.projects.add(idea["Strategy and Planning/name"])
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Project", "entity": {{"Todoist/name" : "{todoist_project["name"]}", "Todoist/Todoist id" : "{todoist_project["id"]}", "Todoist/Idea" : {{"fibery/id" : "{idea["fibery/id"]}"}}  }}}}}}]')
    validate_result(result)
    api.commit()
    for subproject in idea['Strategy and Planning/Sub-ideas']:
        make_new_todoist_project(idea_dict[subproject["fibery/id"]], result[0]["result"]["fibery/id"], todoist_project["id"])    


def make_new_todoist_task(task, parent_id="None", parent_todoist_id="None"):
    if parent_todoist_id != "None":
        todoist_task = api.items.add(task["Strategy and Planning/name"], parent_id=parent_todoist_id)
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}", "Todoist/Task" : {{"fibery/id" : "{task["fibery/id"]}"}}, "Todoist/Parent Task" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
    else:
        todoist_task = api.items.add(task["Strategy and Planning/name"])
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}", "Todoist/Task" : {{"fibery/id" : "{task["fibery/id"]}"}}  }}}}}}]')
    
    if task["workflow/state"]["enum/name"] == "Done":
        todoist_task["checked"] = 1
    # print(task, parent_id, getframeinfo(stack()[1][0]))
    validate_result(result)
    api.commit()
    for subtask in task['Strategy and Planning/Sub-Tasks']:
        make_new_todoist_task(idea_dict[subtask["fibery/id"]], result[0]["result"]["fibery/id"], todoist_task["id"])    


def make_new_todoist_task_in_project(task, parent_id, parent_todoist_id):

    todoist_task = api.items.add(task["Strategy and Planning/name"], project_id=parent_todoist_id)
    result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}", "Todoist/Task" : {{"fibery/id" : "{task["fibery/id"]}"}}, "Todoist/Todoist Project" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')

    if task["workflow/state"]["enum/name"] == "Done":
        todoist_task["checked"] = 1

    api.commit()
    validate_result(result)
    for subtask in task['Strategy and Planning/Sub-Tasks']:
        make_new_todoist_task(task_dict[subtask["fibery/id"]], result[0]["result"]["fibery/id"], todoist_task["id"])    


# Create all top-level projects that don't have todoist tasks yet. This could be made wildly more efficient by making some more API calls.
for idea in ideas[0]["result"]:

    if idea["Todoist/Todoist Project"] is None:
        if idea["Strategy and Planning/Parent Idea"] is None:
            make_new_todoist_project(idea)
        else:
            parent_idea = idea_dict[idea["Strategy and Planning/Parent Idea"]["fibery/id"]]
            if parent_idea["Todoist/Todoist Project"] is None:
                # this sub-project will get added when the parent is
                continue
            make_new_todoist_project(idea, parent_idea["Todoist/Todoist Project"]["fibery/id"], parent_idea["Todoist/Todoist Project"]["Todoist/Todoist id"])

ideas = make_api_call(get_ideas_query)

idea_dict = {}
idea_dict_by_name = {}

for idea in ideas[0]["result"]:
    idea_dict[idea["fibery/id"]] = idea
    idea_dict_by_name[idea["Strategy and Planning/name"]] = idea

for project in api.projects.all():
    if project["name"] not in idea_dict_by_name:
        curr = project
        parents = []
        # print(curr)
        while ("parent_id" in curr and curr["parent_id"] is not None) and curr["name"] not in idea_dict_by_name:
            # print(curr)
            parents.append(curr)
            curr = api.projects.get(curr["parent_id"])
            if "project" in curr:
                curr = curr["project"]
            # print(curr)
        if ("name" in curr and curr["name"] in idea_dict_by_name) or ("project" in curr and curr["project"]["name"] in idea_dict_by_name):
            if "project" in curr:
                curr = curr["project"]
            parent_id = idea_dict_by_name[curr["name"]]["fibery/id"]
            parent_todoist_id = idea_dict_by_name[curr["name"]]["Todoist/Todoist Project"]["fibery/id"]
            for proj in reversed(parents):
                result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Strategy and Planning/Idea", "entity": {{"Strategy and Planning/name" : "{proj["name"]}", "Strategy and Planning/Parent Idea" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
                # print(result)
                result2 = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Project", "entity": {{"Todoist/name" : "{proj["name"]}", "Todoist/Todoist id" : "{proj["id"]}", "Todoist/Idea" : {{"fibery/id" : "{result[0]["result"]["fibery/id"]}"}}, "Todoist/Parent Project" : {{"fibery/id" : "{parent_todoist_id}"}}  }}}}}}]')
                # print(result2)
                parent_id = result[0]["result"]["fibery/id"]
                parent_todoist_id = result2[0]["result"]["fibery/id"]


tasks = make_api_call(get_tasks_query)

task_dict = {}
task_dict_by_name = {}

for task in tasks[0]["result"]:
    task_dict[task["fibery/id"]] = task
    task_dict_by_name[task["Strategy and Planning/name"]] = task


for idea in ideas[0]["result"]:
    # print(idea)

    if idea["Todoist/Todoist Project"] is None:
        if idea["Strategy and Planning/Parent Idea"] is None:
            make_new_todoist_project(idea)
        else:
            parent_idea = idea_dict[idea["Strategy and Planning/Parent Idea"]["fibery/id"]]
            if parent_idea["Todoist/Todoist Project"] is None:
                # this sub-project will get added when the parent is
                continue
            make_new_todoist_project(idea, parent_idea["Todoist/Todoist Project"]["fibery/id"], parent_idea["Todoist/Todoist Project"]["Todoist/Todoist id"])

tasks = make_api_call(get_tasks_query)

task_dict = {}
task_dict_by_name = {}

for task in tasks[0]["result"]:
    task_dict[task["fibery/id"]] = task
    task_dict_by_name[task["Strategy and Planning/name"]] = task


for task in tasks[0]["result"]:
    if task["Todoist/Todoist Task"] is None:
        if task["Strategy and Planning/Parent Task"] is None:
            if task["Strategy and Planning/Idea"] is None:
                make_new_todoist_task(task)
                # todoist_task = api.items.add(task["Strategy and Planning/name"])
                # api.commit()
                # result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}", "Todoist/Task" : {{"fibery/id" : "{task["fibery/id"]}"}}  }}}}}}]')
                # print(result)
            else:
                # print(idea_dict[task["Strategy and Planning/Idea"]["fibery/id"]]["fibery/id"])
                make_new_todoist_task_in_project(task, idea_dict[task["Strategy and Planning/Idea"]["fibery/id"]]["Todoist/Todoist Project"]["fibery/id"], idea_dict[task["Strategy and Planning/Idea"]["fibery/id"]]["Todoist/Todoist Project"]["Todoist/Todoist id"] )
        elif task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"] is not None:
            # if the parent doesn't have a todoist task yet, it's going to get created and this one will be handled in the process
            # we care here about the case where a new child task has been created for an already synced parent.

            todoist_parent_id = task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"]["Todoist/Todoist id"]
            parent_id = task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"]["fibery/id"]
            make_new_todoist_task(task, parent_id, todoist_parent_id)

    else:
        todoist_task = api.items.get(task["Todoist/Todoist Task"]["Todoist/Todoist id"])
        # print(task)
        if "item" in todoist_task:
            todoist_task = todoist_task["item"]
        if task["workflow/state"]["enum/name"] == "Done":
            todoist_task["checked"] = 1
        elif todoist_task["checked"]:
            # print(task)
            result = make_api_call(f'[{{"command": "fibery.entity/update", "args": {{"type": "Strategy and Planning/Task", "entity": {{"fibery/id": "{task["fibery/id"]}", "workflow/state": {{"fibery/id": "29ac67a0-09fa-11ea-a3d8-6c6046a7a9a7"}}  }}}}}}]')
            # result = make_api_call(f'[{{"command": "fibery.entity/update", "args": {{"type": "workflow/state_Strategy and Planning/Task", "entity": {{"fibery/id":"{task["workflow/state"]["fibery/id"]}", "enum/name":"Done"  }}}}}}]')
            # print(result)
            validate_result(result)