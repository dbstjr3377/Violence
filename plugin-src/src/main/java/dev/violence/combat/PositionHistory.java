package dev.violence.combat;

import dev.violence.math.Vec3;

/** 지난 N 틱 동안의 발 위치 기록 (지연 보상용). */
public final class PositionHistory {
    private final Vec3[] pos;
    private final boolean[] downed;
    private int head = -1;
    private int size;

    public PositionHistory(int capacity) {
        this.pos = new Vec3[capacity];
        this.downed = new boolean[capacity];
    }

    public void record(Vec3 p, boolean isDowned) {
        head = (head + 1) % pos.length;
        pos[head] = p;
        downed[head] = isDowned;
        if (size < pos.length) size++;
    }

    /** ticksAgo 틱 전 위치. 기록이 부족하면 가장 오래된 위치. */
    public Vec3 get(int ticksAgo) {
        if (size == 0) return null;
        int t = Math.min(ticksAgo, size - 1);
        return pos[(head - t + pos.length) % pos.length];
    }

    public void clear() {
        size = 0;
        head = -1;
    }
}
