package dev.violence.logic;

import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/** NavGrid 위의 A* 길찾기 + 직선 경로 다듬기. */
public final class AStar {
    private AStar() {}

    private record Entry(NavGrid.Node node, double f) {}

    public static List<Vec3> find(NavGrid grid, NavGrid.Node start, NavGrid.Node goal, int maxExpansions) {
        if (start == null || goal == null) return List.of();
        if (start == goal) return List.of(goal.pos());
        PriorityQueue<Entry> open = new PriorityQueue<>((a, b) -> Double.compare(a.f, b.f));
        Map<Long, Double> gScore = new HashMap<>();
        Map<Long, NavGrid.Node> came = new HashMap<>();
        gScore.put(start.key, 0.0);
        open.add(new Entry(start, h(start, goal)));
        int expansions = 0;
        NavGrid.Node best = start;
        double bestH = h(start, goal);
        while (!open.isEmpty() && expansions < maxExpansions) {
            Entry e = open.poll();
            NavGrid.Node cur = e.node;
            double g = gScore.getOrDefault(cur.key, Double.MAX_VALUE);
            if (e.f - h(cur, goal) > g + 1e-6) continue; // 오래된 항목
            if (cur == goal) return smooth(grid, rebuild(came, cur));
            expansions++;
            double ch = h(cur, goal);
            if (ch < bestH) { bestH = ch; best = cur; }
            for (NavGrid.Node n : grid.neighbors(cur)) {
                double step = (n.x != cur.x && n.z != cur.z) ? 1.41421356 : 1.0;
                step += Math.abs(n.h - cur.h) * 0.5 + n.extraCost;
                double ng = g + step;
                if (ng < gScore.getOrDefault(n.key, Double.MAX_VALUE)) {
                    gScore.put(n.key, ng);
                    came.put(n.key, cur);
                    open.add(new Entry(n, ng + h(n, goal)));
                }
            }
        }
        // 목표에 도달 못하면 가장 가까이 간 곳까지의 경로
        if (best == start) return List.of();
        return smooth(grid, rebuild(came, best));
    }

    private static double h(NavGrid.Node a, NavGrid.Node b) {
        double dx = Math.abs(a.x - b.x), dz = Math.abs(a.z - b.z);
        double oct = Math.max(dx, dz) + (1.41421356 - 1) * Math.min(dx, dz);
        return oct + Math.abs(a.h - b.h);
    }

    private static List<NavGrid.Node> rebuild(Map<Long, NavGrid.Node> came, NavGrid.Node end) {
        List<NavGrid.Node> path = new ArrayList<>();
        NavGrid.Node c = end;
        while (c != null) {
            path.add(c);
            c = came.get(c.key);
        }
        Collections.reverse(path);
        return path;
    }

    /** 직선으로 걸을 수 있는 중간 노드를 건너뛴다 (string pulling). */
    static List<Vec3> smooth(NavGrid grid, List<NavGrid.Node> path) {
        List<Vec3> out = new ArrayList<>();
        if (path.isEmpty()) return out;
        int i = 0;
        while (i < path.size() - 1) {
            int j = Math.min(path.size() - 1, i + 12);
            while (j > i + 1) {
                NavGrid.Node a = path.get(i), b = path.get(j);
                if (Math.abs(a.h - b.h) < 0.01 && b.extraCost == 0 && grid.walkableLine(a, b)) break;
                j--;
            }
            out.add(path.get(j).pos());
            i = j;
        }
        return out;
    }
}
