import networkx as nx
from typing import Dict, Any, List

class LiteGraph:
    def __init__(self):
        self.G = nx.MultiDiGraph()

    def upsert_person(self, person_id: str, **attrs):
        self.G.add_node(("person", person_id), **attrs)

    def upsert_skill(self, skill_id: str, **attrs):
        self.G.add_node(("skill", skill_id), **attrs)

    def upsert_role(self, role_id: str, **attrs):
        self.G.add_node(("role", role_id), **attrs)

    def add_person_skill(self, person_id: str, skill_id: str, **attrs):
        self.G.add_edge(("person", person_id), ("skill", skill_id), key=f"p_s_{person_id}_{skill_id}", **attrs)

    def add_role_skill(self, role_id: str, skill_id: str, **attrs):
        self.G.add_edge(("role", role_id), ("skill", skill_id), key=f"r_s_{role_id}_{skill_id}", **attrs)

    def get_person_skills(self, person_id: str) -> List[Dict[str, Any]]:
        out = []
        for _, dst, key, data in self.G.out_edges(("person", person_id), keys=True, data=True):
            if dst[0] == "skill" and key.startswith("p_s_"):
                label = self.G.nodes[dst].get("canonical_label", dst[1])
                out.append({"skill_id": dst[1], "label": label, **data})
        return out

    def get_role_requirements(self, role_id: str) -> List[Dict[str, Any]]:
        out = []
        for _, dst, key, data in self.G.out_edges(("role", role_id), keys=True, data=True):
            if dst[0] == "skill" and key.startswith("r_s_"):
                label = self.G.nodes[dst].get("canonical_label", dst[1])
                out.append({"skill_id": dst[1], "label": label, **data})
        return out

GRAPH = LiteGraph()
