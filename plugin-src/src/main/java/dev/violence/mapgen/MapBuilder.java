package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * 맵 건축 도구. 층 높이 5 (바닥 y, 실내 y+1..y+4, 천장 y+5).
 * 점프가 불가능하므로 층 사이는 반 블록 계단(10칸)으로만 연결한다.
 */
public final class MapBuilder {
    public static final int H = 5;

    public final BlockAccess w;
    public final Random rnd;
    public final Theme theme;
    public final GameMap map = new GameMap();
    private int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE, minZ = Integer.MAX_VALUE;
    private int maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE, maxZ = Integer.MIN_VALUE;
    /** 문 위치 (이후 분할 벽이 문을 막지 않도록) */
    private final List<int[]> doorCells = new ArrayList<>();

    public MapBuilder(BlockAccess w, Random rnd, Theme theme) {
        this.w = w;
        this.rnd = rnd;
        this.theme = theme;
    }

    // ───────── 기본 배치 ─────────

    public void set(int x, int y, int z, String state) {
        w.set(x, y, z, state);
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (z < minZ) minZ = z;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
        if (z > maxZ) maxZ = z;
    }

    public void clear(int x, int y, int z) { w.set(x, y, z, "minecraft:air"); }

    public boolean isAir(int x, int y, int z) { return w.isAir(x, y, z); }

    /** 블록 이름 (상태 제외) */
    public String type(int x, int y, int z) { return Theme.name(w.get(x, y, z)); }

    public void fill(int x1, int y1, int z1, int x2, int y2, int z2, String d) {
        for (int x = Math.min(x1, x2); x <= Math.max(x1, x2); x++)
            for (int y = Math.min(y1, y2); y <= Math.max(y1, y2); y++)
                for (int z = Math.min(z1, z2); z <= Math.max(z1, z2); z++) set(x, y, z, d);
    }

    public void clearBox(int x1, int y1, int z1, int x2, int y2, int z2) {
        for (int x = Math.min(x1, x2); x <= Math.max(x1, x2); x++)
            for (int y = Math.min(y1, y2); y <= Math.max(y1, y2); y++)
                for (int z = Math.min(z1, z2); z <= Math.max(z1, z2); z++) clear(x, y, z);
    }

    /** 바닥판 */
    public void floor(Rect r, int y, String d) { fill(r.x1(), y, r.z1(), r.x2(), y, r.z2(), d); }

    /** 체크무늬 바닥 */
    public void checker(Rect r, int y, String a, String b) {
        for (int x = r.x1(); x <= r.x2(); x++)
            for (int z = r.z1(); z <= r.z2(); z++) set(x, y, z, ((x + z) & 1) == 0 ? a : b);
    }

    /** 바깥 벽(외벽) 상자: 바닥, 사방 벽, 천장 */
    public void shell(Rect r, int y, String wall, String floor, String ceiling) {
        floor(r, y, floor);
        floor(r, y + H, ceiling);
        for (int yy = y + 1; yy < y + H; yy++) {
            for (int x = r.x1(); x <= r.x2(); x++) {
                set(x, yy, r.z1(), wall);
                set(x, yy, r.z2(), wall);
            }
            for (int z = r.z1(); z <= r.z2(); z++) {
                set(r.x1(), yy, z, wall);
                set(r.x2(), yy, z, wall);
            }
        }
    }

    /** X 축을 따라 놓인 벽 (z 고정) */
    public void wallX(int x1, int x2, int z, int y, String d) {
        for (int x = Math.min(x1, x2); x <= Math.max(x1, x2); x++)
            for (int yy = y + 1; yy < y + H; yy++) set(x, yy, z, d);
    }

    /** Z 축을 따라 놓인 벽 (x 고정) */
    public void wallZ(int x, int z1, int z2, int y, String d) {
        for (int z = Math.min(z1, z2); z <= Math.max(z1, z2); z++)
            for (int yy = y + 1; yy < y + H; yy++) set(x, yy, z, d);
    }

    // ───────── 문 / 창문 ─────────

    /**
     * 밀어서 여는 문. (x,z) 는 벽 위의 칸, alongX = 벽이 X 축 방향.
     */
    public void door(int x, int y, int z, boolean alongX) {
        clear(x, y + 1, z);
        clear(x, y + 2, z);
        set(x, y + 3, z, theme.trim);
        map.doors.add(new GameMap.DoorSpec(x, y + 1, z, alongX, rnd.nextBoolean()));
        doorCells.add(new int[]{x, y, z, alongX ? 1 : 0});
    }

    /** 문짝 없는 출입구 (폭 w) */
    public void doorway(int x, int y, int z, boolean alongX, int width) {
        for (int i = 0; i < width; i++) {
            int xx = alongX ? x + i : x, zz = alongX ? z : z + i;
            clear(xx, y + 1, zz);
            clear(xx, y + 2, zz);
            doorCells.add(new int[]{xx, y, zz, alongX ? 1 : 0});
        }
    }

    /** 벽에 유리창 (높이 y+2..y+3, 아래 y+1 은 창턱이라 넘어갈 수 없음) */
    public void window(int x, int y, int z, boolean alongX, int width, boolean pane) {
        String g = pane ? glassPane(alongX) : theme.glass;
        for (int i = 0; i < width; i++) {
            int xx = alongX ? x + i : x, zz = alongX ? z : z + i;
            set(xx, y + 2, zz, g);
            set(xx, y + 3, zz, g);
        }
    }

    /** 바닥까지 내려오는 유리벽 (사무실 칸막이) */
    public void glassWall(int x, int y, int z, boolean alongX, int width) {
        String g = glassPane(alongX);
        for (int i = 0; i < width; i++) {
            int xx = alongX ? x + i : x, zz = alongX ? z : z + i;
            for (int yy = y + 1; yy < y + H; yy++) set(xx, yy, zz, g);
        }
    }

    public String glassPane(boolean alongX) {
        String base = Theme.name(theme.glass);
        String pane = base.endsWith("_pane") ? base : base + "_pane";
        if (pane.equals("tinted_glass_pane")) pane = "gray_stained_glass_pane";
        return "minecraft:" + pane + (alongX ? "[east=true,west=true]" : "[north=true,south=true]");
    }

    // ───────── 계단 ─────────

    /**
     * 반 블록 계단 (점프 없이 오를 수 있음). 시작점 (x,z) 에서 dx/dz 방향으로 10칸 올라가
     * 위층(y+H) 바닥과 이어진다. width 는 계단 폭.
     */
    public void stairs(int x, int y, int z, int dx, int dz, int width, String solid, String slab) {
        int steps = H * 2;
        int px = dz != 0 ? 1 : 0, pz = dx != 0 ? 1 : 0; // 폭 방향
        for (int i = 0; i < steps; i++) {
            double top = 0.5 * (i + 1);
            int k = (int) Math.floor(top);
            boolean half = top - k > 0.25;
            for (int wv = 0; wv < width; wv++) {
                int cx = x + dx * i + px * wv, cz = z + dz * i + pz * wv;
                for (int yy = y + 1; yy <= y + k; yy++) set(cx, yy, cz, solid);
                if (half) set(cx, y + 1 + k, cz, slab);
                // 머리 공간 확보 (위층 바닥 뚫기)
                for (int yy = y + 1 + k + (half ? 1 : 0); yy <= y + H + 2; yy++) {
                    if (yy == y + H && i == steps - 1) continue;
                    if (yy > y + k + 3 && yy > y + H) break;
                    clear(cx, yy, cz);
                }
            }
        }
        // 마지막 칸 위에 위층과 같은 높이 바닥
        for (int wv = 0; wv < width; wv++) {
            int cx = x + dx * (steps - 1) + px * wv, cz = z + dz * (steps - 1) + pz * wv;
            set(cx, y + H, cz, solid);
        }
        // 위층 구멍 옆 난간 (떨어짐 방지)
        String rail = "minecraft:dark_oak_fence";
        for (int i = 0; i < steps - 1; i++) {
            int ax = x + dx * i - px, az = z + dz * i - pz;
            int bx = x + dx * i + px * width, bz = z + dz * i + pz * width;
            if (isAir(ax, y + H + 1, az) && !isAir(ax, y + H, az)) set(ax, y + H + 1, az, rail);
            if (isAir(bx, y + H + 1, bz) && !isAir(bx, y + H, bz)) set(bx, y + H + 1, bz, rail);
        }
        int ex = x - dx, ez = z - dz;
        for (int wv = 0; wv < width; wv++) {
            int cx = ex + px * wv, cz = ez + pz * wv;
            if (isAir(cx, y + H + 1, cz) && !isAir(cx, y + H, cz)) set(cx, y + H + 1, cz, rail);
        }
    }

    // ───────── 조명 / 가구 ─────────

    public void lights(Rect r, int y, int spacing) {
        int ceil = y + H;
        for (int x = r.x1() + spacing / 2; x <= r.x2(); x += spacing)
            for (int z = r.z1() + spacing / 2; z <= r.z2(); z += spacing) set(x, ceil, z, theme.light);
    }

    /** 탁자 (위가 막힌 반블록) - 위에 무기를 올릴 수 있음 */
    public void table(int x, int y, int z, boolean weapon) {
        set(x, y + 1, z, theme.table);
        if (weapon) weaponSpot(x + 0.5, y + 2, z + 0.5);
    }

    public void counter(int x1, int z1, int x2, int z2, int y) {
        fill(x1, y + 1, z1, x2, y + 1, z2, theme.counter);
    }

    public void weaponSpot(double x, double y, double z) {
        map.weaponSpots.add(new GameMap.WeaponSpot(new Vec3(x, y, z), rnd.nextFloat() * 360, null));
    }

    public void spawn(double x, double y, double z) {
        map.spawns.add(new Vec3(x, y, z));
    }

    /** 방 내부에 리스폰 위치와 바닥 무기를 흩뿌림 */
    public void populate(Rect room, int y, int spawns, int weapons) {
        Rect in = room.shrink(1);
        if (in.width() <= 0 || in.depth() <= 0) in = room;
        for (int i = 0; i < spawns; i++) {
            int x = in.x1() + rnd.nextInt(in.width()), z = in.z1() + rnd.nextInt(in.depth());
            if (isAir(x, y + 1, z) && isAir(x, y + 2, z) && !isAir(x, y, z)) spawn(x + 0.5, y + 1, z + 0.5);
        }
        for (int i = 0; i < weapons; i++) {
            int x = in.x1() + rnd.nextInt(in.width()), z = in.z1() + rnd.nextInt(in.depth());
            if (isAir(x, y + 1, z) && !isAir(x, y, z)) weaponSpot(x + 0.5, y + 1, z + 0.5);
        }
    }

    // ───────── 방 분할 (BSP) ─────────

    public record Room(Rect rect, int y, int depth) {}

    /**
     * 사각형 영역(벽 안쪽)을 무작위로 방들로 나눈다. 나누는 벽마다 문을 하나 이상 낸다.
     * @param doorChance 문짝을 달 확률 (나머지는 뚫린 출입구)
     * @param glassChance 나누는 벽에 유리창을 낼 확률
     */
    public List<Room> subdivide(Rect area, int y, int minSize, int maxSize, String wall, double doorChance, double glassChance) {
        List<Room> out = new ArrayList<>();
        split(area, y, minSize, maxSize, wall, doorChance, glassChance, out, 0);
        return out;
    }

    private boolean blocked(int coord, boolean wallAlongX, Rect r) {
        // 이 위치에 벽을 세우면 기존 문 옆을 막는가
        for (int[] d : doorCells) {
            boolean doorAlongX = d[3] == 1;
            if (wallAlongX) {
                // 새 벽은 z=coord, 경계의 Z 방향 벽(x 고정)에 있는 문을 막을 수 있음
                if (!doorAlongX && Math.abs(d[2] - coord) <= 1 && (d[0] == r.x1() - 1 || d[0] == r.x2() + 1)) return true;
            } else {
                if (doorAlongX && Math.abs(d[0] - coord) <= 1 && (d[2] == r.z1() - 1 || d[2] == r.z2() + 1)) return true;
            }
        }
        return false;
    }

    private void split(Rect r, int y, int min, int max, String wall, double doorChance, double glassChance, List<Room> out, int depth) {
        boolean canX = r.width() >= min * 2 + 1;
        boolean canZ = r.depth() >= min * 2 + 1;
        boolean mustSplit = r.width() > max || r.depth() > max;
        if ((!canX && !canZ) || (!mustSplit && rnd.nextDouble() < 0.25 && depth > 0)) {
            out.add(new Room(r, y, depth));
            return;
        }
        boolean splitX = canX && (!canZ || r.width() > r.depth() || (r.width() == r.depth() && rnd.nextBoolean()));
        for (int attempt = 0; attempt < 8; attempt++) {
            if (splitX) {
                int c = r.x1() + min + rnd.nextInt(r.width() - min * 2);
                if (blocked(c, false, r)) continue;
                wallZ(c, r.z1(), r.z2(), y, wall);
                int dz = r.z1() + 1 + rnd.nextInt(Math.max(1, r.depth() - 2));
                connect(c, y, dz, false, doorChance);
                if (r.depth() > 8 && rnd.nextDouble() < glassChance) {
                    int gz = dz + 3 <= r.z2() - 2 ? dz + 3 : r.z1() + 1;
                    if (Math.abs(gz - dz) > 2) window(c, y, gz, false, Math.min(3, r.z2() - gz), true);
                }
                split(new Rect(r.x1(), r.z1(), c - 1, r.z2()), y, min, max, wall, doorChance, glassChance, out, depth + 1);
                split(new Rect(c + 1, r.z1(), r.x2(), r.z2()), y, min, max, wall, doorChance, glassChance, out, depth + 1);
                return;
            } else {
                int c = r.z1() + min + rnd.nextInt(r.depth() - min * 2);
                if (blocked(c, true, r)) continue;
                wallX(r.x1(), r.x2(), c, y, wall);
                int dx = r.x1() + 1 + rnd.nextInt(Math.max(1, r.width() - 2));
                connect(dx, y, c, true, doorChance);
                if (r.width() > 8 && rnd.nextDouble() < glassChance) {
                    int gx = dx + 3 <= r.x2() - 2 ? dx + 3 : r.x1() + 1;
                    if (Math.abs(gx - dx) > 2) window(gx, y, c, true, Math.min(3, r.x2() - gx), true);
                }
                split(new Rect(r.x1(), r.z1(), r.x2(), c - 1), y, min, max, wall, doorChance, glassChance, out, depth + 1);
                split(new Rect(r.x1(), c + 1, r.x2(), r.z2()), y, min, max, wall, doorChance, glassChance, out, depth + 1);
                return;
            }
        }
        out.add(new Room(r, y, depth));
    }

    public void connect(int x, int y, int z, boolean alongX, double doorChance) {
        if (rnd.nextDouble() < doorChance) door(x, y, z, alongX);
        else doorway(x, y, z, alongX, 1);
    }

    /** 외벽에 일정 간격으로 창문 (안쪽 벽이 맞닿은 곳은 피함) */
    public void exteriorWindows(Rect r, int y, int spacing, int width) {
        for (int x = r.x1() + 2; x + width <= r.x2() - 1; x += spacing) {
            if (canWindow(x, y, r.z1(), true, width, 0, 1)) window(x, y, r.z1(), true, width, true);
            if (canWindow(x, y, r.z2(), true, width, 0, -1)) window(x, y, r.z2(), true, width, true);
        }
        for (int z = r.z1() + 2; z + width <= r.z2() - 1; z += spacing) {
            if (canWindow(r.x1(), y, z, false, width, 1, 0)) window(r.x1(), y, z, false, width, true);
            if (canWindow(r.x2(), y, z, false, width, -1, 0)) window(r.x2(), y, z, false, width, true);
        }
    }

    private boolean canWindow(int x, int y, int z, boolean alongX, int width, int inX, int inZ) {
        for (int i = -1; i <= width; i++) {
            int xx = alongX ? x + i : x, zz = alongX ? z : z + i;
            // 벽 자체가 막혀 있어야 하고(출입구 아님), 안쪽 칸은 비어 있어야 함
            if (i >= 0 && i < width && isAir(xx, y + 2, zz)) return false;
            if (!isAir(xx + inX, y + 2, zz + inZ)) return false;
        }
        return true;
    }

    public GameMap finish(String id, String name) {
        map.id = id;
        map.displayName = name;
        map.minX = minX - 1;
        map.minY = minY - 1;
        map.minZ = minZ - 1;
        map.maxX = maxX + 1;
        map.maxY = maxY + 2;
        map.maxZ = maxZ + 1;
        map.lobbySpawn = new Vec3((minX + maxX) / 2.0, maxY + 8, (minZ + maxZ) / 2.0);
        // 겹치는 무기 지점 정리
        List<GameMap.WeaponSpot> uniq = new ArrayList<>();
        for (GameMap.WeaponSpot s : map.weaponSpots) {
            boolean dup = false;
            for (GameMap.WeaponSpot u : uniq) if (u.pos().distanceSq(s.pos()) < 1.0) dup = true;
            if (!dup && isAir((int) Math.floor(s.pos().x()), (int) Math.floor(s.pos().y()), (int) Math.floor(s.pos().z()))) uniq.add(s);
        }
        map.weaponSpots.clear();
        map.weaponSpots.addAll(uniq);
        List<Vec3> sp = new ArrayList<>();
        for (Vec3 s : map.spawns) {
            int x = (int) Math.floor(s.x()), y = (int) Math.floor(s.y()), z = (int) Math.floor(s.z());
            if (isAir(x, y, z) && isAir(x, y + 1, z)) sp.add(s);
        }
        map.spawns.clear();
        map.spawns.addAll(sp);
        return map;
    }
}
