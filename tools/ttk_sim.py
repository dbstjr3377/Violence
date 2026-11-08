#!/usr/bin/env python3
"""
TTK(처치까지 걸리는 시간) 분석용 매치 시뮬레이션.
실제로 생성된 맵(build-out/maps/*.txt)의 보행 칸·시야(복셀 광선)를 쓰고, 전투 규칙은 플러그인 코드 값을 따른다.
  - 머리 = 즉사, 몸통 = 쓰러짐(3초), 쓰러진 적에게 한 번 더 맞히면 사망 / 근접은 처형
  - 리스폰 2초, 리스폰 보호 없음, 리스폰 위치는 SpawnScorer 처럼 후보 24곳 중 시야에 덜 걸리는 곳
  - 무기: weapons.yml (탄수·연사·퍼짐·사거리), 재장전 없음, 빈 총은 던짐, 바닥 무기 = 인원 × 0.5
  - NPC: 반응 6+(1-skill)×14+0~4틱, 퍼짐 배율 1.6+(1-skill)×1.6, 시야 42블록·약 200°, 플레이어·쓰러진 적 우선
  - 사람: 반응 0.22~0.40초, 조준 오차 0.7°, 이동 5.8블록/초 (NPC 4.7)
시간 간격 0.25초로 단순화한 모델이므로 절대값보다 경향(맵/인원/규칙 변경 비교)을 보는 용도.
결과: build-out/ttk/results.json, docs/TTK_ANALYSIS.md 의 표에 쓰는 요약

--loadout: 지금 규칙으로 NPC 시작 무기 효과 비교 (build-out/ttk/loadout.json)
  rules="new" = 지금 플러그인: 총 몸통은 쓰러뜨리지 않고 HP 100 에서 한 발 40, 30 이하면 즉사(3초 안 맞으면 회복),
                근접 무기는 즉사, 맨주먹·투척(투척 전용 제외)은 쓰러뜨림
  npc_armed / npc_gun_share = NpcLoadout (NPC 5명 중 3명 무기, 그중 총 2 : 근접 3), 리스폰 때도
"""
import json
import math
import os
import random
import re
import sys
from collections import defaultdict, deque

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_maps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DT = 0.25
TOTAL = 50
PASSABLE = ("pane", "fence", "carpet", "potted", "trapdoor", "iron_bars", "lantern", "torch", "button", "lever", "rail", "flower", "sapling")
SEE_THROUGH = ("glass", "pane", "iron_bars", "fence", "lantern", "leaves", "potted", "carpet", "trapdoor")


# ───────────────────────── 무기 ─────────────────────────

def load_weapons():
    yml = open(os.path.join(ROOT, "plugin-src", "src", "main", "resources", "weapons.yml"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^  ([a-z0-9_]+):\s*\n((?:    .*\n)+)", yml, re.M):
        wid, block = m.group(1), m.group(2)

        def g(key, default=None, cast=float):
            mm = re.search(r"^    " + key + r":\s*([^\s#]+)", block, re.M)
            return cast(mm.group(1)) if mm else default
        out[wid] = {"id": wid, "cat": g("category", "MELEE", str), "ammo": g("ammo", 0, int), "rpm": g("rpm", 0.0),
                    "auto": g("automatic", "false", str) == "true", "spread": g("spread", 0.0), "range": g("range", 50.0),
                    "pellets": g("pellets", g("pellets-min", 1, int), int), "mrange": g("melee-range", 2.2),
                    "mcd": g("melee-cooldown", 10, int), "weight": g("spawn-weight", 0, int), "exec": g("execution", "AUTO", str),
                    "hits": g("execution-hits", 1, int)}
    return out


# ───────────────────────── 맵 ─────────────────────────

class Map:
    def __init__(self, mid):
        _, _, bounds, grid, doors, weapons, spawns = render_maps.load(os.path.join(ROOT, "build-out", "maps", mid + ".txt"))
        self.id = mid
        self.min = np.array(bounds[:3]) - 1
        size = np.array(bounds[3:]) - self.min + 3
        self.solid = np.zeros(size, dtype=bool)       # 이동을 막는 블록
        self.opaque = np.zeros(size, dtype=bool)      # 시야/총알을 막는 블록
        for (x, y, z), name in grid.items():
            i = (x - self.min[0], y - self.min[1], z - self.min[2])
            if not any(p in name for p in PASSABLE) or "pane" in name or "bars" in name or "fence" in name:
                self.solid[i] = True
            if not any(p in name for p in SEE_THROUGH):
                self.opaque[i] = True
        # 보행 칸: 발밑이 막혀 있고 몸 두 칸이 비어 있음
        s = self.solid
        walk = np.zeros_like(s)
        walk[:, 1:-1, :] = s[:, :-2, :] & ~s[:, 1:-1, :] & ~s[:, 2:, :]
        idx = np.argwhere(walk)
        self.nodes = idx
        self.node_of = {tuple(p): k for k, p in enumerate(idx)}
        self.adj = [[] for _ in range(len(idx))]
        for k, (x, y, z) in enumerate(idx):
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                for dy in (0, 1, -1):
                    n = self.node_of.get((x + dx, y + dy, z + dz))
                    if n is not None:
                        if dx and dz and (s[x + dx, y, z] or s[x, y, z + dz]):
                            continue
                        self.adj[k].append(n)
                        break
        # 가장 큰 연결 덩어리만 사용
        comp = [-1] * len(idx)
        best, best_size = 0, 0
        cid = 0
        for k in range(len(idx)):
            if comp[k] >= 0:
                continue
            q = deque([k])
            comp[k] = cid
            n = 0
            while q:
                u = q.popleft()
                n += 1
                for v in self.adj[u]:
                    if comp[v] < 0:
                        comp[v] = cid
                        q.append(v)
            if n > best_size:
                best, best_size = cid, n
            cid += 1
        self.main = np.array([k for k in range(len(idx)) if comp[k] == best])
        self.pos = (idx + self.min + np.array([0.5, 0.0, 0.5])).astype(float)
        self.spawns = [k for k in (self.nearest_node(np.array(sp)) for sp in spawns) if k is not None]
        if len(self.spawns) < 8:
            # 리스폰 지점이 걸어 다닐 수 있는 곳과 안 맞으면 보행 칸에서 골고루 (GameService 와 같은 보충)
            self.spawns += [int(k) for k in self.main[:: max(1, len(self.main) // 60)]]
        self.weapon_spots = [self.nearest_node(np.array(w[:3])) for w in weapons]
        self.weapon_spots = [k for k in self.weapon_spots if k is not None]
        self.area = len(self.main)
        self.path_cache = {}

    def nearest_node(self, p):
        """도달 가능한 보행 칸 중 가장 가까운 곳 (탁자 위 무기 지점 → 탁자 옆 바닥)"""
        if not hasattr(self, "main_set"):
            self.main_set = set(int(k) for k in self.main)
        cell = tuple((np.floor(p) - self.min).astype(int))
        k = self.node_of.get(cell)
        if k is not None and k in self.main_set:
            return k
        d = np.linalg.norm(self.pos[self.main] - p, axis=1)
        j = int(np.argmin(d))
        return int(self.main[j]) if d[j] < 3 else None

    def path(self, a, b):
        """BFS 경로 (목표에서 거꾸로 한 번 계산해 캐시)"""
        if b not in self.path_cache:
            if len(self.path_cache) > 400:
                self.path_cache.clear()
            prev = {b: -1}
            q = deque([b])
            while q:
                u = q.popleft()
                for v in self.adj[u]:
                    if v not in prev:
                        prev[v] = u
                        q.append(v)
            self.path_cache[b] = prev
        prev = self.path_cache[b]
        if a not in prev:
            return []
        out, u = [], a
        while u != -1 and len(out) < 400:
            out.append(u)
            u = prev[u]
        return out[1:]

    def los(self, A, B):
        """A[i] → B[i] 시야 (불투명 블록만 막음), 벡터 DDA"""
        n = len(A)
        if n == 0:
            return np.zeros(0, dtype=bool)
        d = B - A
        L = np.linalg.norm(d, axis=1)
        d = d / np.maximum(L, 1e-6)[:, None]
        o = A - self.min
        cell = np.floor(o).astype(np.int64)
        step = np.where(d > 0, 1, -1)
        with np.errstate(divide="ignore"):
            inv = np.where(np.abs(d) > 1e-9, 1.0 / d, 1e12)
        tm = (cell + (step > 0) - o) * inv
        td = np.abs(inv)
        clear = np.ones(n, dtype=bool)
        active = np.ones(n, dtype=bool)
        rows = np.arange(n)
        shape = np.array(self.opaque.shape)
        for _ in range(160):
            idx = rows[active]
            if idx.size == 0:
                break
            ax = np.argmin(tm[idx], axis=1)
            t = tm[idx, ax]
            cell[idx, ax] += step[idx, ax]
            tm[idx, ax] += td[idx, ax]
            done = t >= L[idx]
            c = cell[idx]
            inside = np.all((c >= 0) & (c < shape), axis=1)
            blk = np.zeros(idx.size, dtype=bool)
            ci = c[inside]
            blk[inside] = self.opaque[ci[:, 0], ci[:, 1], ci[:, 2]]
            blk &= ~done
            clear[idx[blk]] = False
            active[idx[blk | done | ~inside]] = False
        return clear


# ───────────────────────── 매치 ─────────────────────────

class Agent:
    def __init__(self, i, human, skill, rng):
        self.i, self.human, self.skill = i, human, skill
        self.heavy = (not human) and rng.random() < 0.12
        self.node = None
        self.path = []
        self.weapon = None          # (무기 정의, 남은 탄)
        self.state = "alive"        # alive / downed / dead
        self.until = 0.0
        self.facing = np.array([1.0, 0, 0])
        self.target = None
        self.react_at = 1e9
        self.next_attack = 0.0
        self.kills = self.deaths = self.streak = 0
        self.best_streak = 0
        self.masks = 0
        self.spawned_at = 0.0
        self.last_seen_enemy = 0.0
        self.saw = {}               # 적 id → 마지막으로 본 시각
        self.search_gaps = []
        self.gap_start = 0.0
        self.engaged_time = 0.0
        self.alive_time = 0.0
        self.unarmed_time = 0.0
        self.gun_time = 0.0
        self.hp = 100.0
        self.hurt_at = -99.0
        self.melee_time = 0.0
        self.lives = []
        self.goal = None


class Match:
    def __init__(self, mp, weapons, humans, rng, spawn_protect=0.0, target_kills=30, limit=600.0, weapon_ratio=0.5,
                 npc_react_mul=1.0, downed=3.0, respawn=2.0, rules="old", npc_armed=0.0, npc_gun_share=0.4,
                 weapon_respawn=0.0):
        self.m, self.W, self.rng = mp, weapons, rng
        self.spawn_protect, self.target_kills, self.limit = spawn_protect, target_kills, limit
        self.npc_react_mul, self.downed_time, self.respawn_time = npc_react_mul, downed, respawn
        self.t = 0.0
        self.rules, self.npc_armed, self.npc_gun_share = rules, npc_armed, npc_gun_share
        self.spawnable = [w for w in weapons.values() if w["weight"] > 0]
        self.agents = [Agent(i, i < humans, 1.0 if i < humans else rng.uniform(0.35, 0.8), rng) for i in range(TOTAL)]
        self.ground = []            # [노드, 무기 정의, 탄]
        spawnable = [w for w in weapons.values() if w["weight"] > 0]
        weights = [w["weight"] for w in spawnable]
        spots = list(mp.weapon_spots) or list(mp.main)
        rng.shuffle(spots)
        self.weapon_respawn = weapon_respawn
        self.spots = spots[: int(round(TOTAL * weapon_ratio))]
        self.spot_empty_since = {}
        for k in self.spots:
            w = rng.choices(spawnable, weights)[0]
            self.ground.append([k, w, w["ammo"]])
        self.events = defaultdict(int)
        self.kill_log = []
        for a in self.agents:
            self.spawn(a)

    # ── 리스폰 (SpawnScorer 근사: 후보 24곳 중 시야에 걸리는 적이 가장 적은 곳) ──
    def spawn(self, a):
        m = self.m
        cands = self.rng.sample(m.spawns, min(24, len(m.spawns)))
        alive = [b for b in self.agents if b is not a and b.state == "alive" and b.node is not None]
        best, best_score = cands[0], 1e9
        if alive:
            ep = np.array([m.pos[b.node] + [0, 1.6, 0] for b in alive])
            for c in cands:
                p = m.pos[c] + [0, 1.6, 0]
                d = np.linalg.norm(ep - p, axis=1)
                near = np.argsort(d)[:10]
                seen = m.los(np.repeat(p[None], len(near), 0), ep[near])
                score = seen.sum() * 10 - min(d.min(), 30) * 0.2
                if score < best_score:
                    best, best_score = c, score
        a.node = best
        a.path = []
        a.state = "alive"
        a.weapon = None
        a.hp = 100.0
        # NpcLoadout: NPC 는 시작·리스폰 때 일정 비율로 무기를 들고 나옴
        if not a.human and self.npc_armed > 0 and self.rng.random() < self.npc_armed:
            cat = "GUN" if self.rng.random() < self.npc_gun_share else "MELEE"
            pool = [w for w in self.spawnable if w["cat"] == cat]
            w = self.rng.choices(pool, [x["weight"] for x in pool])[0]
            a.weapon = (w, w["ammo"])
        a.target = None
        a.spawned_at = self.t
        a.gap_start = self.t
        a.saw = {}

    def weapon_of(self, a):
        if a.weapon is None:
            return self.W["fist"], 0
        return a.weapon

    # ── 피격 ──
    def hit(self, v, attacker, head, kind):
        if v.state == "dead":
            return
        if self.t - v.spawned_at < self.spawn_protect:
            self.events["spawn_protect_block"] += 1
            return
        if head or v.state == "downed":
            self.kill(v, attacker, kind)
        elif self.rules == "new" and kind == "gun":
            # 지금 규칙: 총은 쓰러뜨리지 않음, HP 30 이하면 즉사
            v.hp -= 40
            v.hurt_at = self.t
            if v.hp <= 30:
                self.kill(v, attacker, kind)
        elif self.rules == "new" and kind == "melee":
            self.kill(v, attacker, kind)       # 근접 무기는 즉사
        else:
            if kind == "fist" and v.heavy:
                return
            v.state = "downed"
            v.until = self.t + self.downed_time
            if v.weapon:
                self.ground.append([v.node, v.weapon[0], v.weapon[1]])
                v.weapon = None
            self.events["knockdown"] += 1

    def kill(self, v, k, kind):
        v.state = "dead"
        v.until = self.t + self.respawn_time
        v.deaths += 1
        v.lives.append(self.t - v.spawned_at)
        life = self.t - v.spawned_at
        if life < 3.0:
            self.events["spawn_death"] += 1
            if v.human:
                self.events["human_spawn_death"] += 1
        if v.human and k is not None and v.saw.get(k.i, -99) < self.t - 1.0:
            self.events["human_death_unseen"] += 1
        if v.human:
            self.events["human_death"] += 1
        if v.weapon:
            self.ground.append([v.node, v.weapon[0], v.weapon[1]])
            v.weapon = None
        v.streak = 0
        if k is not None:
            k.kills += 1
            k.streak += 1
            k.best_streak = max(k.best_streak, k.streak)
            if k.streak in (3, 5):
                k.masks += 1
            self.kill_log.append((self.t, k.i, v.i, kind, k.human, v.human))

    # ── 한 단계 ──
    def step(self):
        m, rng, t = self.m, self.rng, self.t
        ag = self.agents
        for a in ag:
            if a.state == "dead" and t >= a.until:
                self.spawn(a)
            elif a.state == "downed" and t >= a.until:
                a.state = "alive"
                a.hp = 100.0
            if a.state == "alive" and a.hp < 100 and t - a.hurt_at > 3.0:
                a.hp = 100.0
        # (선택) 바닥 무기 다시 생성: 무기 지점이 weapon_respawn 초 동안 비어 있으면 새 무기
        if self.weapon_respawn > 0:
            occupied = {g[0] for g in self.ground}
            for k in self.spots:
                if k in occupied:
                    self.spot_empty_since.pop(k, None)
                    continue
                since = self.spot_empty_since.setdefault(k, t)
                if t - since >= self.weapon_respawn:
                    w = rng.choices(self.spawnable, [x["weight"] for x in self.spawnable])[0]
                    self.ground.append([k, w, w["ammo"]])
                    self.spot_empty_since.pop(k, None)
        alive = [a for a in ag if a.state != "dead"]
        pos = np.array([m.pos[a.node] for a in alive])
        n = len(alive)
        # 시야 쌍 (42블록 이내)
        D = np.linalg.norm(pos[:, None] - pos[None], axis=2)
        I, J = np.where(np.triu(D < 42, 1))
        eye = pos + [0, 1.6, 0]
        vis = m.los(eye[I], eye[J] - [0, 0.4, 0]) if len(I) else np.zeros(0, bool)
        seen = defaultdict(list)
        for i, j, v in zip(I, J, vis):
            if v:
                seen[i].append(j)
                seen[j].append(i)
        for ii, a in enumerate(alive):
            if a.state != "alive":
                continue
            a.alive_time += DT
            if t < getattr(a, "busy_until", 0.0):      # 처형 중: 움직이거나 다른 행동을 할 수 없음
                a.engaged_time += DT
                continue
            # 1) 무기 줍기 (NpcManager.act 처럼 매 틱 먼저: 1.5블록 안이면 바로)
            if a.weapon is None or (a.weapon[0]["cat"] == "GUN" and a.weapon[1] <= 0):
                g = self.nearest_ground(a, 1.5)
                if g is not None:
                    if a.weapon is not None:
                        self.ground.append([a.node, a.weapon[0], a.weapon[1]])
                    self.ground.remove(g)
                    a.weapon = (g[1], g[2])
                    a.path = []
            w, ammo = self.weapon_of(a)
            if w["cat"] == "GUN":
                a.gun_time += DT
            elif w["id"] == "fist":
                a.unarmed_time += DT
            else:
                a.melee_time += DT
            # 시야 안 (사람 FOV 약 110°, NPC 약 200°, 5블록 이내는 소리로 앎)
            cands = []
            for jj in seen.get(ii, []):
                b = alive[jj]
                to = pos[jj] - pos[ii]
                dist = D[ii, jj]
                cos = (to @ a.facing) / max(dist, 1e-6)
                if dist < 5 or cos > (0.57 if a.human else -0.2):
                    cands.append((dist - (4 if b.state == "downed" else 0) - (2 if (b.human and not a.human) else 0), jj))
            if cands:
                if t - a.last_seen_enemy > DT * 1.5 and a.human:
                    a.search_gaps.append(t - a.gap_start)
                a.last_seen_enemy = t
                a.engaged_time += DT
                _, jj = min(cands)
                b = alive[jj]
                for _, k in cands:
                    a.saw[alive[k].i] = t
                if a.target is not b:
                    a.target = b
                    if a.human:
                        a.react_at = t + rng.uniform(0.22, 0.40) + (0.15 if (pos[jj] - pos[ii]) @ a.facing < 0 else 0)
                    else:
                        a.react_at = t + (6 + (1 - a.skill) * 14 + rng.randint(0, 4)) / 20.0 * self.npc_react_mul
                self.fight(a, b, D[ii, jj], w, ammo)
            else:
                if t - a.last_seen_enemy <= DT * 1.5:
                    a.gap_start = t
                a.target = None
                self.roam(a, w)
        self.t += DT

    def fight(self, a, b, dist, w, ammo):
        m, rng, t = self.m, self.rng, self.t
        to = m.pos[b.node] - m.pos[a.node]
        if np.linalg.norm(to) > 0:
            a.facing = to / np.linalg.norm(to)
        if t < a.react_at:
            return
        if w["cat"] == "GUN":
            if ammo <= 0:
                # 빈 총: 가까우면 던짐, 아니면 무기 찾기
                if 2.5 < dist < 13 and t >= a.next_attack:
                    a.weapon = None
                    self.ground.append([b.node, w, 0])
                    a.next_attack = t + 0.3
                    if rng.random() < max(0.15, 0.85 - dist * 0.05):
                        self.hit(b, a, False, "throw")
                        self.events["throw_hit"] += 1
                    return
                self.move_to(a, b.node, speed=1.0)
                return
            if dist > w["range"]:
                self.move_to(a, b.node)
                return
            # 발사 수 (사람: 단발은 초당 6번 클릭 한도, NPC: nextShot 간격)
            if w["auto"]:
                shots = int(rng.random() + w["rpm"] / 60 * DT * (1.0 if a.human else 0.75))
            elif a.human:
                shots = 1 if rng.random() < min(1.0, min(w["rpm"] / 60, 6) * DT) else 0
            else:
                shots = 1 if t >= a.next_attack else 0
                if shots:
                    a.next_attack = t + (6 + (1 - a.skill) * 12 + rng.randint(0, 5)) / 20.0
            shots = min(shots, ammo)
            if shots <= 0:
                return
            a.weapon = (w, ammo - shots)
            penalty = 1.0 if a.human else 1.6 + (1 - a.skill) * 1.6
            aim = 0.7 if a.human else 0.0
            sigma = math.radians(math.hypot(w["spread"] * penalty * 0.5, aim))
            r = 0.3 / max(dist, 0.5)
            p_hit = 1 - math.exp(-(r * r) / (2 * sigma * sigma + 1e-9))
            head_p = 0.3 if a.human else 0.2
            for _ in range(shots):
                hits = sum(rng.random() < p_hit for _ in range(max(1, w["pellets"])))
                for _h in range(hits):
                    self.hit(b, a, rng.random() < head_p * 0.6, "gun")
                    if b.state == "dead":
                        break
                if b.state == "dead":
                    break
            self.events["shots"] += shots
        else:
            reach = w["mrange"] - 0.3
            if dist <= reach:
                if t >= a.next_attack:
                    a.next_attack = t + w["mcd"] / 20.0
                    if b.state == "downed":
                        # 처형: AUTO 0.5초, HITS 는 클릭 수만큼 (그동안 무방비)
                        dur = 0.5 if w["exec"] == "AUTO" else 0.3 + 0.25 * w["hits"]
                        a.busy_until = t + dur
                        b.state = "dead"                       # 처형 중에는 다른 공격을 받지 않음
                        self.kill(b, a, "execution")
                        self.events["execution"] += 1
                    elif rng.random() < (0.85 if a.human else 0.6 + a.skill * 0.3):
                        self.hit(b, a, False, "fist" if w["id"] == "fist" else "melee")
            else:
                if w["id"] == "fist" and dist > 8 and self.ground:
                    g = self.nearest_ground(a)
                    if g is not None:
                        self.move_to(a, g[0])
                        return
                self.move_to(a, b.node)

    def nearest_ground(self, a, maxd=12):
        m = self.m
        p = m.pos[a.node]
        best, bd = None, maxd
        for g in self.ground:
            d = np.linalg.norm(m.pos[g[0]] - p)
            if d < bd and (g[1]["cat"] != "GUN" or g[2] > 0):
                best, bd = g, d
        return best

    def roam(self, a, w):
        m, rng = self.m, self.rng
        # 바닥 무기 줍기 (지나가다 1.5 블록 안)
        if a.weapon is None or (a.weapon[0]["cat"] == "GUN" and a.weapon[1] <= 0):
            g = self.nearest_ground(a, 14 if a.human else 10)
            if g is not None:
                if np.linalg.norm(m.pos[g[0]] - m.pos[a.node]) < 1.5:
                    self.ground.remove(g)
                    a.weapon = (g[1], g[2])
                    a.path = []
                    return
                self.move_to(a, g[0])
                return
        # 사람: 가장 가까운 적 쪽으로 / NPC: 목적지 없이 돌아다님 (총소리 쪽)
        if not a.path:
            if a.human:
                others = [b for b in self.agents if b is not a and b.state != "dead"]
                b = min(others, key=lambda b: np.linalg.norm(m.pos[b.node] - m.pos[a.node]))
                a.goal = b.node
            else:
                a.goal = int(rng.choice(m.main))
            a.path = m.path(a.node, a.goal)[:40]
        self.advance(a, 5.8 if a.human else (3.8 if a.heavy else 4.7))

    def move_to(self, a, node, speed=None):
        if not a.path or a.goal != node or len(a.path) > 60:
            a.goal = node
            a.path = self.m.path(a.node, node)[:60]
        self.advance(a, speed or (5.8 if a.human else (3.8 if a.heavy else 4.7)))

    def advance(self, a, speed):
        # 남은 이동량을 다음 단계로 넘김 (대각선 한 칸 1.41 > 한 단계 이동량이어도 멈추지 않게)
        a.carry = min(getattr(a, "carry", 0.0) + speed * DT, speed * DT * 2)
        m = self.m
        while a.path:
            nxt = a.path[0]
            d = np.linalg.norm(m.pos[nxt] - m.pos[a.node])
            if d > a.carry:
                break
            a.carry -= d
            mv = m.pos[nxt] - m.pos[a.node]
            if np.linalg.norm(mv) > 0:
                a.facing = mv / np.linalg.norm(mv)
            a.node = nxt
            a.path.pop(0)

    def run(self):
        while self.t < self.limit:
            self.step()
            if max(a.kills for a in self.agents) >= self.target_kills:
                break
        return self.summary()

    def summary(self):
        H = [a for a in self.agents if a.human]
        N = [a for a in self.agents if not a.human]
        mins = self.t / 60
        gaps = [g for a in H for g in a.search_gaps]
        lives = [l for a in H for l in a.lives]
        human_kills = sum(1 for k in self.kill_log if k[4])
        hk_npc = sum(1 for k in self.kill_log if k[4] and not k[5])
        hd = self.events["human_death"]
        top = max(self.agents, key=lambda a: a.kills)
        alive_t = sum(a.alive_time for a in H) or 1
        return {
            "map": self.m.id, "humans": len(H), "minutes": round(mins, 2), "ended_by_kills": top.kills >= self.target_kills,
            "leader_human": top.human, "leader_kills": top.kills,
            "human_kpm": round(sum(a.kills for a in H) / max(1, len(H)) / mins, 2),
            "human_dpm": round(sum(a.deaths for a in H) / max(1, len(H)) / mins, 2),
            "npc_kpm": round(sum(a.kills for a in N) / max(1, len(N)) / mins, 2),
            "human_kd": round(sum(a.kills for a in H) / max(1, sum(a.deaths for a in H)), 2),
            "life_median_s": round(float(np.median(lives)), 1) if lives else None,
            "search_gap_median_s": round(float(np.median(gaps)), 1) if gaps else None,
            "search_gap_p90_s": round(float(np.percentile(gaps, 90)), 1) if gaps else None,
            "search_time_share": round(1 - sum(a.engaged_time for a in H) / alive_t, 2),
            "unarmed_share": round(sum(a.unarmed_time for a in H) / alive_t, 2),
            "gun_share": round(sum(a.gun_time for a in H) / alive_t, 2),
            "human_spawn_death_share": round(self.events["human_spawn_death"] / max(1, hd), 2),
            "human_death_unseen_share": round(self.events["human_death_unseen"] / max(1, hd), 2),
            "human_kills_on_humans_share": round(1 - hk_npc / max(1, human_kills), 2),
            "masks_per_human": round(sum(a.masks for a in H) / max(1, len(H)), 2),
            "best_streak_median": float(np.median([a.best_streak for a in H])),
            "executions": self.events["execution"], "knockdowns": self.events["knockdown"],
            "kills_by_kind": {k: sum(1 for x in self.kill_log if x[3] == k) for k in ("gun", "throw", "melee", "fist", "execution")},
            "ground_weapons_left": len(self.ground),
            "ground_guns_with_ammo": sum(1 for g in self.ground if g[1]["cat"] == "GUN" and g[2] > 0),
        }


def run(maps, humans_list, seeds, variants):
    W = load_weapons()
    out = []
    cache = {}
    for mid in maps:
        cache[mid] = Map(mid)
        print(mid, "보행 칸", cache[mid].area, "리스폰", len(cache[mid].spawns), "무기 지점", len(cache[mid].weapon_spots), flush=True)
    for vname, kw in variants:
        for mid in maps:
            for h in humans_list:
                for s in seeds:
                    res = Match(cache[mid], W, h, random.Random(s * 1000 + h), **kw).run()
                    res["variant"] = vname
                    res["seed"] = s
                    out.append(res)
                    print(vname, mid, h, s, res["minutes"], "분", "KPM", res["human_kpm"], "탐색", res["search_gap_median_s"], flush=True)
    return out


if __name__ == "__main__":
    maps = ["club", "prison", "apartment_a", "sewer", "restaurant"]
    variants = [("기본", {})]
    if "--loadout" in sys.argv:
        variants = [("예전 규칙 (문서 기준)", {}), ("지금 규칙, NPC 맨손", {"rules": "new"}),
                    ("지금 규칙 + NPC 시작 무기", {"rules": "new", "npc_armed": 0.6, "npc_gun_share": 0.4}),
                    ("+ 바닥 무기 25초 뒤 다시 생성", {"rules": "new", "npc_armed": 0.6, "npc_gun_share": 0.4, "weapon_respawn": 25.0})]
    if "--levers" in sys.argv:
        maps = ["prison", "sewer"]
        variants = [("기본", {}), ("리스폰 보호 1.5초", {"spawn_protect": 1.5}), ("NPC 반응 1.5배 느림", {"npc_react_mul": 1.5}),
                    ("무기 비율 1.0", {"weapon_ratio": 1.0}), ("쓰러짐 2초", {"downed": 2.0})]
    res = run(maps, [8, 16, 24], [1, 2], variants)
    os.makedirs(os.path.join(ROOT, "build-out", "ttk"), exist_ok=True)
    name = "levers.json" if "--levers" in sys.argv else "loadout.json" if "--loadout" in sys.argv else "results.json"
    json.dump(res, open(os.path.join(ROOT, "build-out", "ttk", name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
