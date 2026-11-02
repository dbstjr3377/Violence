package dev.violence.logic;

import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * NPC 길찾기용 보행 그리드. 각 노드는 "디딜 수 있는 블록" 위의 서 있는 위치.
 * 점프가 불가능한 게임이므로 높이 차 0.6 이하로만 이동할 수 있다 (반 블록 계단 오르기).
 */
public final class NavGrid {

    /** 블록 형태 질의. 서버 월드나 테스트용 가짜 월드가 구현한다. */
    public interface BlockQuery {
        /** 이 블록 윗면의 높이 (0..1). 디딜 수 없으면 NaN. 예) 일반 블록 1.0, 아래 반블록 0.5 */
        double topHeight(int x, int y, int z);
        /** 사람이 통과할 수 있는 블록인가 (공기, 열린 공간, 문틀 등) */
        boolean passable(int x, int y, int z);
    }

    public static final class Node {
        public final int x, y, z;
        public final double h;
        public final long key;
        public double extraCost;
        Node(int x, int y, int z, double h) {
            this.x = x; this.y = y; this.z = z; this.h = h;
            this.key = key(x, y, z);
        }
        public Vec3 pos() { return new Vec3(x + 0.5, h, z + 0.5); }
    }

    private final Map<Long, Node> nodes = new HashMap<>();
    private final Map<Long, List<Node>> columns = new HashMap<>();
    private final List<Node> all = new ArrayList<>();

    public static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (z & 0x3FFFFFF) << 12) | (y & 0xFFF);
    }

    private static long colKey(int x, int z) {
        return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
    }

    public static NavGrid build(BlockQuery q, int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {
        NavGrid g = new NavGrid();
        for (int x = minX; x <= maxX; x++) {
            for (int z = minZ; z <= maxZ; z++) {
                for (int y = minY; y <= maxY; y++) {
                    double t = q.topHeight(x, y, z);
                    if (Double.isNaN(t)) continue;
                    if (q.passable(x, y + 1, z) && q.passable(x, y + 2, z)) {
                        g.add(new Node(x, y, z, y + t));
                    }
                }
            }
        }
        return g;
    }

    void add(Node n) {
        nodes.put(n.key, n);
        columns.computeIfAbsent(colKey(n.x, n.z), k -> new ArrayList<>()).add(n);
        all.add(n);
    }

    public int size() { return all.size(); }
    public List<Node> nodes() { return all; }

    public Node get(int x, int y, int z) { return nodes.get(key(x, y, z)); }

    /** (x,z) 열에서 높이 h 와 가장 가까운 노드 (허용 오차 이내). */
    public Node nodeAt(int x, int z, double h, double tolerance) {
        List<Node> col = columns.get(colKey(x, z));
        if (col == null) return null;
        Node best = null;
        double bd = tolerance;
        for (Node n : col) {
            double d = Math.abs(n.h - h);
            if (d <= bd) { bd = d; best = n; }
        }
        return best;
    }

    /** 월드 좌표에서 가장 가까운 노드 (주변 2칸까지 탐색). */
    public Node nearest(Vec3 p) {
        int bx = (int) Math.floor(p.x()), bz = (int) Math.floor(p.z());
        Node best = null;
        double bd = Double.MAX_VALUE;
        for (int r = 0; r <= 2 && best == null; r++) {
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    List<Node> col = columns.get(colKey(bx + dx, bz + dz));
                    if (col == null) continue;
                    for (Node n : col) {
                        double d = n.pos().distanceSq(p) + Math.abs(n.h - p.y()) * 4;
                        if (n.h - p.y() > 1.2) continue; // 위층 노드는 제외
                        if (d < bd) { bd = d; best = n; }
                    }
                }
            }
        }
        return best;
    }

    private static final int[][] DIRS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
    public static final double MAX_STEP = 0.6;

    public List<Node> neighbors(Node n) {
        List<Node> out = new ArrayList<>(8);
        for (int[] d : DIRS) {
            Node m = nodeAt(n.x + d[0], n.z + d[1], n.h, MAX_STEP);
            if (m == null) continue;
            if (d[0] != 0 && d[1] != 0) {
                // 대각선 이동은 양쪽 직교 칸이 모두 걸을 수 있어야 한다 (모서리 끼임 방지)
                if (nodeAt(n.x + d[0], n.z, n.h, MAX_STEP) == null || nodeAt(n.x, n.z + d[1], n.h, MAX_STEP) == null) continue;
            }
            out.add(m);
        }
        return out;
    }

    /** 두 노드 사이를 직선으로 걸어갈 수 있는가 (경로 다듬기용). */
    public boolean walkableLine(Node a, Node b) {
        double dx = b.x - a.x, dz = b.z - a.z;
        int steps = (int) Math.ceil(Math.max(Math.abs(dx), Math.abs(dz)) * 2);
        if (steps == 0) return true;
        Node prev = a;
        for (int i = 1; i <= steps; i++) {
            double t = i / (double) steps;
            double px = a.x + 0.5 + dx * t, pz = a.z + 0.5 + dz * t;
            // 사람 폭(0.6)을 고려해 좌우 모서리도 확인
            for (double ox : new double[]{-0.3, 0.3}) {
                for (double oz : new double[]{-0.3, 0.3}) {
                    Node c = nodeAt((int) Math.floor(px + ox), (int) Math.floor(pz + oz), prev.h, MAX_STEP);
                    if (c == null) return false;
                }
            }
            Node c = nodeAt((int) Math.floor(px), (int) Math.floor(pz), prev.h, MAX_STEP);
            if (c == null) return false;
            prev = c;
        }
        return true;
    }
}
