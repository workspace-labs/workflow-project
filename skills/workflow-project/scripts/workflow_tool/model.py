"""Reads a workflow file and checks it.

The file describes the project (what it is, who takes part) and its parts. Each part becomes one
swimlane page: its lanes, then its nodes in the order they happen. Every problem is reported as a
plain sentence that says what to change, so the agent that wrote the file can fix it and run again.
"""

import datetime
import json
import re

from . import theme

NODE_TYPES = ("start", "step", "decision", "end", "stop")
TERMINALS = ("end", "stop")
MAX_LANES = 5
MIN_BRANCHES, MAX_BRANCHES = 2, 3
MAX_LIST_ITEMS = 8

_TOP_KEYS = {"project", "parts"}
_PROJECT_KEYS = {"name", "accent", "client", "prepared_by", "date", "version", "status", "summary",
                 "actors", "assumptions", "open_questions"}
_PART_KEYS = {"title", "summary", "lanes", "nodes"}
_NODE_KEYS = {
    "start": {"id", "type", "lane", "title", "next"},
    "step": {"id", "type", "lane", "title", "detail", "result", "next"},
    "decision": {"id", "type", "lane", "title", "detail", "branches"},
    "end": {"id", "type", "lane", "title", "detail", "to_part"},
    "stop": {"id", "type", "lane", "title", "detail"},
}
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class WorkflowError(Exception):
    """The workflow cannot be drawn yet. `problems` holds one plain sentence per problem."""

    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = list(problems)


class Node(object):
    def __init__(self, index, node_id, node_type, lane, title):
        self.index = index
        self.id = node_id
        self.type = node_type
        self.lane = lane
        self.title = title
        self.detail = ""
        self.result = ""
        self.next = None
        self.branches = []       # [(label, target id)], decisions only
        self.to_part = None      # end nodes only: the part this end leads into
        self.number = None       # steps only: 1, 2, 3 ... in reading order


class Edge(object):
    def __init__(self, source, target, label=None, branch=None):
        self.source = source
        self.target = target
        self.label = label       # a decision's answer, e.g. "Yes"
        self.branch = branch     # 0 = a decision's first answer (the normal one)
        self.main = False        # on the normal path from start to end


class Part(object):
    def __init__(self, number, title, summary, lanes):
        self.number = number
        self.title = title
        self.summary = summary
        self.lanes = lanes
        self.nodes = []
        self.by_id = {}
        self.edges = []

    def outgoing(self, node_id):
        return [e for e in self.edges if e.source == node_id]

    def incoming(self, node_id):
        return [e for e in self.edges if e.target == node_id]


class Project(object):
    def __init__(self):
        self.name = ""
        self.accent = ""
        self.client = ""
        self.prepared_by = ""
        self.date = ""
        self.version = ""
        self.status = ""
        self.summary = ""
        self.actors = []          # [(name, role)]
        self.assumptions = []
        self.open_questions = []
        self.parts = []


def load(path):
    """Reads and checks a workflow file. Raises WorkflowError listing every problem found."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as err:
        raise WorkflowError(["Could not read the workflow file %s: %s." % (path, err)])
    try:
        data = json.loads(text)
    except ValueError as err:
        where = ""
        if getattr(err, "lineno", None):
            where = " (line %d, column %d)" % (err.lineno, err.colno)
        raise WorkflowError(["The workflow file is not valid JSON%s: %s." % (where, getattr(err, "msg", err))])
    return parse(data)


def parse(data):
    """Turns the loaded JSON into a checked Project. Raises WorkflowError listing every problem."""
    problems = []
    if not isinstance(data, dict):
        raise WorkflowError(['The workflow file must be one JSON object with "project" and "parts".'])
    _unknown_keys(data, _TOP_KEYS, "The file", problems)

    project = _parse_project(data.get("project"), problems)

    raw_parts = data.get("parts")
    if not isinstance(raw_parts, list) or not raw_parts:
        problems.append('Add "parts": a list with at least one part.')
        raw_parts = []
    actor_names = [name for name, _ in project.actors]
    for number, raw in enumerate(raw_parts, 1):
        part = _parse_part(number, raw, actor_names, problems)
        if part is not None:
            project.parts.append(part)

    for part in project.parts:
        for node in part.nodes:
            if node.to_part is None:
                continue
            valid = isinstance(node.to_part, int) and not isinstance(node.to_part, bool)
            if not valid or not 1 <= node.to_part <= len(raw_parts) or node.to_part == part.number:
                problems.append('%s: "to_part" must be the number of another part (1 to %d).'
                                % (_where(part, node), len(raw_parts)))

    missing = sorted(set(ch for text in _all_text(data) for ch in theme.missing_characters(text)))
    if missing:
        problems.append("Some text uses characters the house font cannot draw: %s. The workflow PDF "
                        "supports English text only for now; replace them."
                        % ", ".join('"%s"' % ch for ch in missing[:12]))

    if problems:
        raise WorkflowError(problems)
    return project


# ---------------------------------------------------------------- the project

def _parse_project(raw, problems):
    project = Project()
    if not isinstance(raw, dict):
        problems.append('Add "project": an object with at least "name", "summary" and "actors".')
        return project
    _unknown_keys(raw, _PROJECT_KEYS, "The project", problems)
    project.name = _text(raw.get("name"), 'The project\'s "name"', problems, limit=70)
    project.accent = _text(raw.get("accent"), 'The project\'s "accent"', problems, required=False, limit=30)
    if project.name and project.accent and project.accent not in project.name.split():
        problems.append('The project\'s "accent" must be one word of its name ("%s").' % project.name)
    if project.name and not project.accent:
        project.accent = project.name.split()[-1]
    project.client = _text(raw.get("client"), 'The project\'s "client"', problems, required=False, limit=80)
    project.prepared_by = _text(raw.get("prepared_by"), 'The project\'s "prepared_by"', problems,
                                required=False, limit=60)
    project.date = _text(raw.get("date"), 'The project\'s "date"', problems, required=False, limit=40) \
        or datetime.date.today().isoformat()
    project.version = _text(raw.get("version"), 'The project\'s "version"', problems, required=False, limit=20) or "1.0"
    project.status = _text(raw.get("status"), 'The project\'s "status"', problems, required=False, limit=40) \
        or "Draft for review"
    project.summary = _text(raw.get("summary"), 'The project\'s "summary" (what it is, in 2 or 3 sentences)',
                            problems, limit=700)
    project.actors = _parse_actors(raw.get("actors"), problems)
    project.assumptions = _text_list(raw.get("assumptions"), 'The project\'s "assumptions"', problems)
    project.open_questions = _text_list(raw.get("open_questions"), 'The project\'s "open_questions"', problems)
    return project


def _parse_actors(raw, problems):
    if not isinstance(raw, list) or not raw:
        problems.append('Add the project\'s "actors": every person, team or system that takes part, '
                        'each with a "name" and a "role".')
        return []
    actors, seen = [], set()
    for position, item in enumerate(raw, 1):
        what = "Actor %d" % position
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            problems.append('%s must be an object with "name" and "role".' % what)
            continue
        _unknown_keys(item, {"name", "role"}, what, problems)
        name = _text(item.get("name"), '%s\'s "name"' % what, problems, limit=28)
        role = _text(item.get("role"), '%s\'s "role"' % what, problems, required=False, limit=180)
        if name and name in seen:
            problems.append('The actor "%s" is listed twice.' % name)
        if name:
            seen.add(name)
            actors.append((name, role))
    return actors


# ---------------------------------------------------------------- parts and nodes

def _parse_part(number, raw, actor_names, problems):
    label = "Part %d" % number
    if not isinstance(raw, dict):
        problems.append('%s must be an object with "title", "lanes" and "nodes".' % label)
        return None
    _unknown_keys(raw, _PART_KEYS, label, problems)
    title = _text(raw.get("title"), '%s\'s "title"' % label, problems, limit=64)
    summary = _text(raw.get("summary"), '%s\'s "summary"' % label, problems, required=False, limit=220)
    part = Part(number, title, summary, [])
    part.lanes = _parse_lanes(part, raw.get("lanes"), actor_names, problems)

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or len(raw_nodes) < 2:
        problems.append('%s needs "nodes": a start, the steps and decisions in order, and an end.' % _part_name(part))
        return part
    for index, item in enumerate(raw_nodes):
        node = _parse_node(part, index, item, problems)
        if node is None:
            continue
        if node.id in part.by_id:
            problems.append('%s: two nodes use the id "%s"; every id must be different.' % (_part_name(part), node.id))
            continue
        part.nodes.append(node)
        part.by_id[node.id] = node

    _check_shape(part, problems)
    _connect(part, problems)
    if part.edges:
        _check_flow(part, problems)
    used = set(node.lane for node in part.nodes)
    for lane in part.lanes:
        if lane not in used:
            problems.append('%s: the lane "%s" has nothing in it; remove it from "lanes".' % (_part_name(part), lane))
    return part


def _parse_lanes(part, raw, actor_names, problems):
    where = _part_name(part)
    if not isinstance(raw, list) or not raw:
        problems.append('%s needs "lanes": the people, teams or systems in it, left to right.' % where)
        return []
    if len(raw) > MAX_LANES:
        problems.append('%s has %d lanes; a page holds %d. Split the part, or join lanes that do the same job.'
                        % (where, len(raw), MAX_LANES))
    lanes = []
    for lane in raw:
        if not isinstance(lane, str) or not lane.strip():
            problems.append('%s: every lane must be an actor\'s name.' % where)
            continue
        lane = " ".join(lane.split())
        if lane in lanes:
            problems.append('%s: the lane "%s" is listed twice.' % (where, lane))
            continue
        if actor_names and lane not in actor_names:
            close = [a for a in actor_names if a.lower() == lane.lower()]
            hint = ' (did you mean "%s"?)' % close[0] if close else ' Add it to the project\'s "actors" with its role.'
            problems.append('%s: the lane "%s" is not one of the project\'s actors.%s' % (where, lane, hint))
        lanes.append(lane)
    return lanes


def _parse_node(part, index, raw, problems):
    where = '%s, node %d' % (_part_name(part), index + 1)
    if not isinstance(raw, dict):
        problems.append('%s must be an object.' % where)
        return None
    node_id = raw.get("id")
    if not isinstance(node_id, str) or not _ID_PATTERN.match(node_id) or len(node_id) > 40:
        problems.append('%s needs an "id": a short name made of letters, numbers, "-" or "_" (for example "check-docs").'
                        % where)
        return None
    where = '%s, node "%s"' % (_part_name(part), node_id)
    node_type = raw.get("type")
    if node_type not in NODE_TYPES:
        problems.append('%s: "type" must be one of %s.' % (where, ", ".join(NODE_TYPES)))
        return None
    _unknown_keys(raw, _NODE_KEYS[node_type], where, problems)
    lane = raw.get("lane")
    if not isinstance(lane, str):
        problems.append('%s: "lane" must be the name of one of this part\'s lanes (%s), written as text; it is %s.'
                        % (where, ", ".join(part.lanes), describe_value(lane, "lane" in raw)))
        lane = None
    elif part.lanes and lane not in part.lanes:
        problems.append('%s: "lane" must be one of this part\'s lanes (%s).' % (where, ", ".join(part.lanes)))
    title_limit = 50 if node_type == "decision" else 70
    title = _text(raw.get("title"), '%s: the "title"' % where, problems, limit=title_limit)
    node = Node(index, node_id, node_type, lane, title)
    node.detail = _text(raw.get("detail"), '%s: the "detail"' % where, problems, required=False, limit=90)
    node.result = _text(raw.get("result"), '%s: the "result"' % where, problems, required=False, limit=90)
    node.next = raw.get("next")
    if node.next is not None and not isinstance(node.next, str):
        problems.append('%s: "next" must be the id of another node.' % where)
        node.next = None
    node.to_part = raw.get("to_part")
    if node_type == "decision":
        node.branches = _parse_branches(where, raw.get("branches"), problems)
    return node


def _parse_branches(where, raw, problems):
    if not isinstance(raw, list) or not MIN_BRANCHES <= len(raw) <= MAX_BRANCHES:
        problems.append('%s: a decision needs "branches": %d or %d answers, the normal answer first '
                        '(for example [{"label": "Yes", "to": "next-step"}, {"label": "No", "to": "stop"}]).'
                        % (where, MIN_BRANCHES, MAX_BRANCHES))
        return []
    branches, labels = [], set()
    for position, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            problems.append('%s: answer %d must be an object with "label" and "to".' % (where, position))
            continue
        _unknown_keys(item, {"label", "to"}, '%s, answer %d' % (where, position), problems)
        label = _text(item.get("label"), '%s: answer %d\'s "label"' % (where, position), problems, limit=14)
        target = item.get("to")
        if not isinstance(target, str) or not target:
            problems.append('%s: answer %d needs "to", the id of the node it leads to.' % (where, position))
            continue
        if label in labels:
            problems.append('%s: two answers are both labelled "%s".' % (where, label))
        labels.add(label)
        branches.append((label, target))
    return branches


def _check_shape(part, problems):
    where = _part_name(part)
    starts = [n for n in part.nodes if n.type == "start"]
    if len(starts) != 1:
        problems.append('%s needs exactly one "start" (it has %d).' % (where, len(starts)))
    elif part.nodes[0].type != "start":
        problems.append('%s: put the "start" first in "nodes"; the list is read in the order things happen.' % where)
    if not any(n.type == "end" for n in part.nodes):
        problems.append('%s needs at least one "end": where the normal path finishes.' % where)
    number = 0
    for node in part.nodes:
        if node.type == "step":
            number += 1
            node.number = number


def _connect(part, problems):
    for position, node in enumerate(part.nodes):
        where = _where(part, node)
        if node.type in ("start", "step"):
            target = node.next
            if target is None and position + 1 < len(part.nodes):
                target = part.nodes[position + 1].id
            if target is None:
                problems.append('%s: nothing comes after it. Add "next", or put an end after it.' % where)
            elif target == node.id:
                problems.append('%s: "next" points to itself.' % where)
            elif target not in part.by_id:
                problems.append('%s: "next" points to "%s", but this part has no node with that id.' % (where, target))
            else:
                part.edges.append(Edge(node.id, target))
        elif node.type == "decision":
            for branch, (label, target) in enumerate(node.branches):
                if target == node.id:
                    problems.append('%s: the answer "%s" points back to the same decision.' % (where, label))
                elif target not in part.by_id:
                    problems.append('%s: the answer "%s" goes to "%s", but this part has no node with that id.'
                                    % (where, label, target))
                else:
                    part.edges.append(Edge(node.id, target, label, branch))


def _check_flow(part, problems):
    where = _part_name(part)
    start = part.nodes[0]
    if start.type != "start":
        return
    reached, todo = {start.id}, [start.id]
    while todo:
        current = todo.pop()
        for edge in part.outgoing(current):
            if edge.target not in reached:
                reached.add(edge.target)
                todo.append(edge.target)
    for node in part.nodes:
        if node.id not in reached:
            problems.append('%s: nothing leads to "%s". Connect it, or remove it.' % (where, node.id))

    finishes = set(n.id for n in part.nodes if n.type in TERMINALS)
    todo = list(finishes)
    while todo:
        current = todo.pop()
        for edge in part.incoming(current):
            if edge.source not in finishes:
                finishes.add(edge.source)
                todo.append(edge.source)
    for node in part.nodes:
        if node.id in reached and node.id not in finishes:
            problems.append('%s: after "%s" there is no way to finish; the flow goes round forever. '
                            'Add a decision with a way out.' % (where, node.id))

    # The normal path: from the start, always the first answer, until an end.
    seen, current = {start.id}, start
    while current.type not in TERMINALS:
        outgoing = [e for e in part.outgoing(current.id) if e.branch in (None, 0)]
        if not outgoing:
            return
        edge = outgoing[0]
        if edge.target in seen:
            problems.append('%s: the normal path (the first answer of every decision) goes back to "%s". Put the '
                            'answer that moves forward first.' % (where, edge.target))
            return
        edge.main = True
        seen.add(edge.target)
        current = part.by_id[edge.target]
    if current.type != "end":
        problems.append('%s: the normal path (the first answer of every decision) finishes at the stop "%s". Put '
                        'the normal answer first, so the normal path reaches an end.' % (where, current.id))


# ---------------------------------------------------------------- small helpers

def _part_name(part):
    return 'Part %d ("%s")' % (part.number, part.title) if part.title else "Part %d" % part.number


def _where(part, node):
    return '%s, node "%s"' % (_part_name(part), node.id)


def describe_value(value, present=True):
    """A plain name for a wrong value, for refusal messages."""
    if not present:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true/false"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, list):
        return "a list"
    if isinstance(value, dict):
        return "an object"
    return "not text"


def _unknown_keys(raw, allowed, what, problems):
    for key in raw:
        if key not in allowed:
            problems.append('%s has an unknown field "%s" (allowed: %s).' % (what, key, ", ".join(sorted(allowed))))


def _text(value, what, problems, required=True, limit=None):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            problems.append("%s is missing." % what)
        return ""
    if not isinstance(value, str):
        problems.append("%s must be text." % what)
        return ""
    value = " ".join(value.split())
    if limit and len(value) > limit:
        problems.append("%s is too long (%d characters; keep it to %d)." % (what, len(value), limit))
    return value


def _text_list(raw, what, problems):
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_LIST_ITEMS:
        problems.append("%s must be a list of up to %d short sentences." % (what, MAX_LIST_ITEMS))
        return []
    items = []
    for position, item in enumerate(raw, 1):
        text = _text(item, "%s, item %d" % (what, position), problems, limit=220)
        if text:
            items.append(text)
    return items


def _all_text(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for text in _all_text(item):
                yield text
    elif isinstance(value, list):
        for item in value:
            for text in _all_text(item):
                yield text
