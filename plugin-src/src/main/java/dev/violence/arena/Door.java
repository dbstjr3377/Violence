package dev.violence.arena;

import dev.violence.combat.Combatant;
import dev.violence.logic.DoorPhysics;
import dev.violence.math.Obb;
import dev.violence.math.Vec3;
import org.bukkit.entity.ItemDisplay;

/**
 * 밀어서 여는 문 하나. 문틀 아래칸 블록 좌표와 방향으로 정의된다.
 * alongX = true 이면 닫힌 문판이 X 축을 따라 놓임 (법선은 Z).
 */
public final class Door {
    public final int bx, by, bz;
    public final boolean alongX;
    /** 경첩이 문틀의 큰 좌표 쪽에 있는가 */
    public final boolean hingeMax;
    public final DoorPhysics physics = new DoorPhysics();
    public ItemDisplay display;
    public boolean barrierPlaced;
    public Combatant lastPusher;
    public boolean lastPushWasKick;
    public double lastSentAngle = Double.NaN;

    public Door(int bx, int by, int bz, boolean alongX, boolean hingeMax) {
        this.bx = bx;
        this.by = by;
        this.bz = bz;
        this.alongX = alongX;
        this.hingeMax = hingeMax;
    }

    public Vec3 hinge() {
        if (alongX) return new Vec3(bx + (hingeMax ? 1 : 0), by, bz + 0.5);
        return new Vec3(bx + 0.5, by, bz + (hingeMax ? 1 : 0));
    }

    /** 닫혔을 때 경첩→문 끝 방향 */
    public Vec3 baseDir() {
        if (alongX) return new Vec3(hingeMax ? -1 : 1, 0, 0);
        return new Vec3(0, 0, hingeMax ? -1 : 1);
    }

    public Vec3 normal() {
        return alongX ? new Vec3(0, 0, 1) : new Vec3(1, 0, 0);
    }

    public Vec3 center() {
        return new Vec3(bx + 0.5, by + 1, bz + 0.5);
    }

    /** 현재 각도에서 경첩→문 끝 방향 */
    public Vec3 dir() {
        return baseDir().rotateY(Math.toRadians(physics.angle()));
    }

    /** 월드 기준 문판 회전각 (라디안, Vec3.rotateY 규약) */
    public double yawRad() {
        Vec3 d = dir();
        return Math.atan2(d.z(), d.x());
    }

    public Obb obb() {
        Vec3 d = dir();
        Vec3 c = hinge().add(d.mul(0.5)).add(0, 1, 0);
        return new Obb(c, new Vec3(0.5, 1.0, 0.09), yawRad());
    }

    /**
     * side 쪽(법선 기준 +1/-1)으로 문 끝이 이동하려면 각속도 부호를 어떻게 해야 하는가.
     */
    public int rotationSignToward(int side) {
        Vec3 closedEnd = hinge().add(baseDir());
        Vec3 test = hinge().add(baseDir().rotateY(Math.toRadians(5)));
        double moved = test.sub(closedEnd).dot(normal());
        return (moved * side) > 0 ? 1 : -1;
    }

    /** dirVec 방향으로 밀었을 때 (총알, 사람이 걸어 들어감 등) */
    public void pushAlong(Vec3 dirVec, double strength, Combatant pusher, boolean kick) {
        int side = dirVec.dot(normal()) >= 0 ? 1 : -1;
        physics.push(rotationSignToward(side), strength);
        if (pusher != null) {
            lastPusher = pusher;
            lastPushWasKick = kick;
        }
    }

    /** 사람이 서 있는 위치 기준, 문틀 중심에서 법선 방향 거리 */
    public double planeDistance(Vec3 p) {
        return p.sub(center()).dot(normal());
    }

    /** 문틀 평면 방향(법선과 수직)으로 얼마나 벗어났는가 */
    public double lateralDistance(Vec3 p) {
        Vec3 along = alongX ? new Vec3(1, 0, 0) : new Vec3(0, 0, 1);
        return Math.abs(p.sub(center()).dot(along));
    }
}
