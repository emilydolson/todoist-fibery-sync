import todoist
import pycurl
import certifi
from io import BytesIO
from urllib.parse import urlencode
import json
from inspect import getframeinfo, stack
import os
import sys

relevant_project_ids = set([2251589958, 2251590566, 2251683318])
idea_project_ids = set([2251589958, 2251590566])


get_tasks_query = '[{"command": "fibery.entity/query", "args": {"query": {"q/from": "Strategy and Planning/Task","q/select": ["Strategy and Planning/name",  "fibery/id", {"workflow/state": ["fibery/id", "enum/name"]}, {"Strategy and Planning/Sub-Tasks": {"q/select": ["fibery/id"], "q/limit": "q/no-limit" }}, {"Strategy and Planning/Parent Idea" :["fibery/id","Strategy and Planning/name"]}, {"Strategy and Planning/Parent Task" :["fibery/id","Strategy and Planning/name"]}, {"Todoist/Todoist Task" :["fibery/id","Todoist/Todoist id"]} ], "q/limit": "q/no-limit"}}}]'
get_ideas_query = '[{"command": "fibery.entity/query", "args": {"query": {"q/from": "Strategy and Planning/Idea","q/select": ["Strategy and Planning/name",  "fibery/id", {"workflow/state": ["fibery/id", "enum/name"]}, {"Strategy and Planning/Sub-ideas": {"q/select": ["fibery/id"], "q/limit": "q/no-limit" }}, {"Strategy and Planning/Parent Idea" :["fibery/id","Strategy and Planning/name"]}, {"Strategy and Planning/Todoist Task" :["fibery/id","Todoist/Todoist id"]} ], "q/limit": "q/no-limit"}}}]'

if os.path.exists("todoist_secret.txt"):
    td_file = open("todoist_secret.txt")
    todoist_secret = td_file.readlines()[0]
    td_file.close()
else:
    todoist_secret = sys.argv[2]

if os.path.exists("fibery_token.txt"):
    fb_file = open("fibery_token.txt")
    fibery_token = fb_file.readlines()[0]
    fb_file.close()
else:
    fibery_token = sys.argv[1]


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
    # c.setopt(c.VERBOSE, True)

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


def get_tasks():
    tasks = make_api_call(get_tasks_query)
    validate_result(tasks)

    task_dict = {}
    task_dict_by_name = {}

    for task in tasks[0]["result"]:
        task_dict[task["fibery/id"]] = task
        task_dict_by_name[task["Strategy and Planning/name"]] = task

    return tasks, task_dict, task_dict_by_name


def get_ideas():
    ideas = make_api_call(get_ideas_query)
    validate_result(ideas)

    idea_dict = {}
    idea_dict_by_name = {}

    for idea in ideas[0]["result"]:
        idea_dict[idea["fibery/id"]] = idea
        idea_dict_by_name[idea["Strategy and Planning/name"]] = idea

    return ideas, idea_dict, idea_dict_by_name


def make_new_todoist_task(task, parent_id="None", parent_todoist_id="None"):
    # print(task, parent_id, parent_todoist_id)
    task_or_idea = "Task" if "Sub-ideas" in task else "Idea"
    if parent_todoist_id != "None":
        todoist_task = api.items.add(task["Strategy and Planning/name"], parent_id=parent_todoist_id)
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}", "Todoist/Parent Task" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
    else:
        todoist_task = api.items.add(task["Strategy and Planning/name"])
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{todoist_task["content"]}", "Todoist/Todoist id" : "{todoist_task["id"]}" }}}}}}]')
    
    if task["workflow/state"]["enum/name"] == "Done":
        todoist_task["checked"] = 1
    # print(task, parent_id, getframeinfo(stack()[1][0]))
    validate_result(result)
    api.commit()
    if 'Strategy and Planning/Sub-Tasks' in task:
        for subtask in task['Strategy and Planning/Sub-Tasks']:
            make_new_todoist_task(task_dict[subtask["fibery/id"]], result[0]["result"]["fibery/id"], todoist_task["id"])    
    if 'Strategy and Planning/Sub-ideas' in task:
        for subproject in task['Strategy and Planning/Sub-ideas']:
            make_new_todoist_task(idea_dict[subproject["fibery/id"]], result[0]["result"]["fibery/id"], todoist_task["id"])    


def add_todoist_task(proj, parent_id="None", parent_todoist_id="None", task_or_idea="Task", parent_task_or_idea="Task"):

    if parent_id != "None":
        # print(proj, parent_id, parent_todoist_id, task_or_idea, parent_task_or_idea)
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Strategy and Planning/{task_or_idea}", "entity": {{"Strategy and Planning/name" : "{proj["content"]}", "Strategy and Planning/Parent {parent_task_or_idea}" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
        validate_result(result)
        result2 = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{proj["content"]}", "Todoist/Todoist id" : "{proj["id"]}", "Todoist/Parent Task" : {{"fibery/id" : "{parent_todoist_id}"}}  }}}}}}]')
        validate_result(result2)
    else:
        result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Strategy and Planning/{task_or_idea}", "entity": {{"Strategy and Planning/name" : "{proj["content"]}" }}}}}}]')
        validate_result(result)
        result2 = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Todoist/Todoist Task", "entity": {{"Todoist/Name" : "{proj["content"]}", "Todoist/Todoist id" : "{proj["id"]}" }}}}}}]')
        validate_result(result2)

    parent_id = result[0]["result"]["fibery/id"]
    parent_todoist_id = result2[0]["result"]["fibery/id"]
    for child in proj["children"]:
        add_todoist_task(task_id_map[child], parent_id, parent_todoist_id, "Task", task_or_idea)


# tasks, task_dict, task_dict_by_name = get_tasks()
ideas, idea_dict, idea_dict_by_name = get_ideas()

# Create all top-level projects that don't have todoist tasks yet. This could be made wildly more efficient by making some more API calls.
for idea in ideas[0]["result"]:

    if idea["Strategy and Planning/Todoist Task"] is None:
        if idea["Strategy and Planning/Parent Idea"] is None:
            make_new_todoist_task(idea)
        else:
            parent_idea = idea_dict[idea["Strategy and Planning/Parent Idea"]["fibery/id"]]
            if parent_idea["Strategy and Planning/Todoist Task"] is None:
                # this sub-project will get added when the parent is
                continue
            make_new_todoist_task(idea, parent_idea["Strategy and Planning/Todoist Task"]["fibery/id"], parent_idea["Strategy and Planning/Todoist Task"]["Todoist/Todoist id"])

ideas, idea_dict, idea_dict_by_name = get_ideas()

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
            parent_todoist_id = idea_dict_by_name[curr["name"]]["Strategy and Planning/Todoist Task"]["fibery/id"]
            for proj in reversed(parents):
                result = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Strategy and Planning/Idea", "entity": {{"Strategy and Planning/name" : "{proj["name"]}", "Strategy and Planning/Parent Idea" : {{"fibery/id" : "{parent_id}"}}  }}}}}}]')
                result2 = make_api_call(f'[{{"command": "fibery.entity/create", "args": {{"type": "Strategy and Planning/Todoist Task", "entity": {{"Todoist/name" : "{proj["name"]}", "Todoist/Todoist id" : "{proj["id"]}", "Todoist/Idea" : {{"fibery/id" : "{result[0]["result"]["fibery/id"]}"}}, "Todoist/Parent Project" : {{"fibery/id" : "{parent_todoist_id}"}}  }}}}}}]')
                parent_id = result[0]["result"]["fibery/id"]
                parent_todoist_id = result2[0]["result"]["fibery/id"]


tasks, task_dict, task_dict_by_name = get_tasks()

for task in tasks[0]["result"]:
    if task["Todoist/Todoist Task"] is None:
        if task["Strategy and Planning/Parent Task"] is None:
            if task["Strategy and Planning/Parent Idea"] is None:
                make_new_todoist_task(task)
            else:
                make_new_todoist_task(task, idea_dict[task["Strategy and Planning/Parent Idea"]["fibery/id"]]["Strategy and Planning/Todoist Task"]["fibery/id"], idea_dict[task["Strategy and Planning/Parent Idea"]["fibery/id"]]["Strategy and Planning/Todoist Task"]["Todoist/Todoist id"] )
        elif task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"] is not None:
            # if the parent doesn't have a todoist task yet, it's going to get created and this one will be handled in the process
            # we care here about the case where a new child task has been created for an already synced parent.

            todoist_parent_id = task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"]["Todoist/Todoist id"]
            parent_id = task_dict[task["Strategy and Planning/Parent Task"]["fibery/id"]]["Todoist/Todoist Task"]["fibery/id"]
            make_new_todoist_task(task, parent_id, todoist_parent_id)

    else:

        todoist_task = api.items.get(task["Todoist/Todoist Task"]["Todoist/Todoist id"])

        if "item" in todoist_task:
            todoist_task = todoist_task["item"]
        print(todoist_task["content"])
        if task["workflow/state"]["enum/name"] == "Done":
            print("done in fibery")
            todoist_task["checked"] = 1
        elif todoist_task["checked"] == 1:
            print("updating state")
            result = make_api_call(f'[{{"command": "fibery.entity/update", "args": {{"type": "Strategy and Planning/Task", "entity": {{"fibery/id": "{task["fibery/id"]}", "workflow/state": {{"fibery/id": "29ac67a0-09fa-11ea-a3d8-6c6046a7a9a7"}}  }}}}}}]')
            validate_result(result)

tasks, task_dict, task_dict_by_name = get_tasks()

task_id_map = {}
roots = []
for project in api.items.all():
    if not (project["project_id"] in relevant_project_ids):
        continue
    if project["content"] not in task_dict_by_name and project["content"] not in idea_dict_by_name:
        project["children"] = []
        task_id_map[project["id"]] = project

for pid in task_id_map.keys():
    if task_id_map[pid]["parent_id"] in task_id_map:
        task_id_map[task_id_map[pid]["parent_id"]]["children"].append(pid)
    else:
        roots.append(pid)

for pid in roots:
    task = task_id_map[pid]
    # print(task)
    if task["parent_id"] is not None and task_id_map[task["parent_id"]]["content"] in task_dict_by_name:
        # print("parent task")
        fibery_parent_id = task_dict_by_name[task_id_map[task["parent_id"]]["content"]]["fibery/id"]
        todoist_parent_id = task_dict_by_name[task_id_map[task["parent_id"]]["content"]]["Todoist/Todoist Task"]["fibery/id"]
        add_todoist_task(task, fibery_parent_id, todoist_parent_id, "Task", "Task")        
    if task["parent_id"] is not None and task_id_map[task["parent_id"]]["content"] in idea_dict_by_name:        
        # print("parent idea")
        fibery_parent_id = task_dict_by_name[task_id_map[task["parent_id"]]["content"]]["fibery/id"]
        todoist_parent_id = task_dict_by_name[task_id_map[task["parent_id"]]["content"]]["Todoist/Todoist Task"]["fibery/id"]
        add_todoist_task(task, fibery_parent_id, todoist_parent_id, "Task", "Idea")        
    else:
        if task["project_id"] in idea_project_ids and (task["parent_id"] is None or task["parent_id"] in idea_project_ids):
            # print("idea")
            add_todoist_task(task, "None", "None", "Idea", "None")        
        else:
            # print("task")
            add_todoist_task(task, "None", "None", "Task", "None")        

