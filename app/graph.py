from collections import defaultdict, deque
from app.search import coordinate_to_id


def load_graph(link_file):
    graph = defaultdict(list)

    if isinstance(link_file, bytes):
        text = link_file.decode("utf-8", errors="ignore")
    elif isinstance(link_file, str):
        import os
        if os.path.exists(link_file):
            with open(link_file, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            text = link_file
    elif hasattr(link_file, "read"):
        content = link_file.read()
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="ignore")
        else:
            text = str(content)
    else:
        text = str(link_file)

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()
        if len(parts) == 4:
            lon_a, lat_a, lon_b, lat_b = map(float, parts)
            a = coordinate_to_id(lat_a, lon_a)
            b = coordinate_to_id(lat_b, lon_b)
        elif len(parts) == 2:
            a, b = map(int, parts)
        else:
            continue

        graph[a].append(b)
        graph[b].append(a)

    return graph


def shortest_distances(source, graph):
    distances = {source: 0}
    queue = deque([source])

    while queue:
        current = queue.popleft()

        for neighbour in graph[current]:
            if neighbour not in distances:
                distances[neighbour] = distances[current] + 1
                queue.append(neighbour)

    return distances