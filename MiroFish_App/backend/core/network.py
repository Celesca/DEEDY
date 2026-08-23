"""
เครือข่ายหลายชั้น (Multi-layer Network) สำหรับจำลองสังคมไทย (Phase 5 / Task 3)

ประกอบด้วย 4 ชั้น:
1. ออนไลน์สาธารณะ (Social Media): กว้าง, เร็ว, อ่อนแอ (homophily สูง)
2. กลุ่มปิด (LINE): แคบ, ไว้ใจสูง
3. ที่ทำงาน/โรงเรียน: ข้ามรุ่น, ข้ามขั้วได้ (homophily ต่ำกว่า)
4. ชุมชน/ครอบครัว: เล็ก, อิทธิพลสูงมาก, ข้ามขั้ว

ข่าวสารและการแพร่อารมณ์จะไหลผ่านท่อเหล่านี้ตาม media_access ของแต่ละคน
"""
import logging
import random
from typing import Dict, List, Set

import networkx as nx

from .agent import GenerativeAgent

logger = logging.getLogger("mirofish.core.network")


class MultiLayerNetwork:
    def __init__(self, agents: List[GenerativeAgent], rng: random.Random):
        self.agents = agents
        self.rng = rng
        self.agent_map = {a.profile.agent_id: a for a in agents}
        
        # กราฟ 4 ชั้น
        self.G_social = nx.Graph()
        self.G_line = nx.Graph()
        self.G_work = nx.Graph()
        self.G_community = nx.Graph()
        
        self._build_networks()

    def _build_networks(self):
        """สร้างเครือข่ายตามคุณสมบัติของประชากร"""
        # Add nodes to all relevant graphs based on media_access
        for a in self.agents:
            aid = a.profile.agent_id
            if a.profile.media.social_media:
                self.G_social.add_node(aid)
            if a.profile.media.line:
                self.G_line.add_node(aid)
            self.G_work.add_node(aid) # ทุกคนมีที่ทำงาน/โรงเรียน (หรือเคยมี)
            if a.profile.media.community:
                self.G_community.add_node(aid)

        # 1. Social Media (Homophily สูงตามความสนใจ/วัย)
        social_nodes = list(self.G_social.nodes())
        for i in range(len(social_nodes)):
            for j in range(i + 1, len(social_nodes)):
                u, v = self.agent_map[social_nodes[i]], self.agent_map[social_nodes[j]]
                # เชื่อมกันง่ายถ้าอายุใกล้กัน หรือ base_personality คล้ายกัน
                prob = 0.05
                if abs(u.profile.age - v.profile.age) <= 10:
                    prob += 0.10
                if self.rng.random() < prob:
                    self.G_social.add_edge(u.profile.agent_id, v.profile.agent_id, weight=0.2)

        # 2. LINE (กลุ่มปิด, Homophily กลาง-สูง, เชื่อมตามภูมิภาคและอาชีพ)
        line_nodes = list(self.G_line.nodes())
        for i in range(len(line_nodes)):
            for j in range(i + 1, len(line_nodes)):
                u, v = self.agent_map[line_nodes[i]], self.agent_map[line_nodes[j]]
                prob = 0.02
                if u.profile.occupation == v.profile.occupation:
                    prob += 0.08
                if u.profile.region == v.profile.region:
                    prob += 0.05
                if self.rng.random() < prob:
                    self.G_line.add_edge(u.profile.agent_id, v.profile.agent_id, weight=0.6)

        # 3. Work/School (Homophily ต่ำ, บังคับเชื่อมข้ามรุ่น/ข้ามขั้ว)
        work_nodes = list(self.G_work.nodes())
        for i in range(len(work_nodes)):
            for j in range(i + 1, len(work_nodes)):
                u, v = self.agent_map[work_nodes[i]], self.agent_map[work_nodes[j]]
                prob = 0.01
                if u.profile.occupation == v.profile.occupation and u.profile.region == v.profile.region:
                    # คนอาชีพเดียวกัน ที่เดียวกัน มีโอกาสเจอกันสูงแม้จะคนละวัย
                    prob += 0.20
                if self.rng.random() < prob:
                    self.G_work.add_edge(u.profile.agent_id, v.profile.agent_id, weight=0.8)

        # 4. Community/Family (เล็ก, อิทธิพลสูงมาก)
        community_nodes = list(self.G_community.nodes())
        for i in range(len(community_nodes)):
            for j in range(i + 1, len(community_nodes)):
                u, v = self.agent_map[community_nodes[i]], self.agent_map[community_nodes[j]]
                prob = 0.005
                if u.profile.region == v.profile.region:
                    prob += 0.05
                if self.rng.random() < prob:
                    self.G_community.add_edge(u.profile.agent_id, v.profile.agent_id, weight=1.0)

        logger.info(
            f"Built Networks: Social({self.G_social.number_of_edges()} edges), "
            f"LINE({self.G_line.number_of_edges()} edges), "
            f"Work({self.G_work.number_of_edges()} edges), "
            f"Community({self.G_community.number_of_edges()} edges)"
        )

    def get_neighbors_with_weights(self, agent_id: str) -> Dict[str, float]:
        """ดึงเพื่อนบ้านทั้งหมดพร้อมน้ำหนักรวม (อิทธิพล) จากทุกชั้นกราฟ"""
        neighbors: Dict[str, float] = {}
        
        def _add_edges(G, weight_multiplier):
            if G.has_node(agent_id):
                for neighbor in G.neighbors(agent_id):
                    w = G[agent_id][neighbor].get('weight', 1.0) * weight_multiplier
                    neighbors[neighbor] = neighbors.get(neighbor, 0.0) + w

        _add_edges(self.G_social, 0.5)
        _add_edges(self.G_line, 1.0)
        _add_edges(self.G_work, 1.5)
        _add_edges(self.G_community, 2.0)
        
        return neighbors

    def calculate_contagion(self) -> Dict[str, float]:
        """คำนวณอารมณ์/ความโกรธที่ไหลมาจากเพื่อนบ้านสำหรับแต่ละ agent"""
        contagion_map = {}
        for agent_id, agent in self.agent_map.items():
            neighbors = self.get_neighbors_with_weights(agent_id)
            if not neighbors:
                contagion_map[agent_id] = 0.0
                continue
                
            total_influence = 0.0
            weighted_anger = 0.0
            
            for neighbor_id, weight in neighbors.items():
                neighbor_agent = self.agent_map[neighbor_id]
                # influence multiplier based on neighbor's profile
                inf = neighbor_agent.profile.influence * weight
                weighted_anger += neighbor_agent.state.anger * inf
                total_influence += inf
                
            contagion_map[agent_id] = weighted_anger / total_influence if total_influence > 0 else 0.0
            
        return contagion_map
