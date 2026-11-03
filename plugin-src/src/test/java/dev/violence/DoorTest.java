package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.arena.Door;
import dev.violence.math.Vec3;
import org.junit.jupiter.api.Test;

/** 문은 민 방향(반대편)으로 열려야 하고, 문판 판정 상자가 실제 문 위치와 맞아야 한다. */
class DoorTest {

    private static void swing(Door d, Vec3 pushDir) {
        d.pushAlong(pushDir, 12, null, false);
        for (int i = 0; i < 40; i++) d.physics.tick();
    }

    @Test
    void opensAwayFromPusherAllOrientations() {
        for (boolean alongX : new boolean[]{true, false}) {
            for (boolean hingeMax : new boolean[]{true, false}) {
                for (int side : new int[]{1, -1}) {
                    Door d = new Door(0, 64, 0, alongX, hingeMax);
                    Vec3 push = d.normal().mul(side);
                    swing(d, push);
                    assertFalse(d.physics.isClosed(), "열려야 함");
                    // 문 끝이 민 방향 쪽으로 이동했는가
                    Vec3 end = d.hinge().add(d.dir());
                    double moved = end.sub(d.center().add(0, -1, 0)).dot(d.normal());
                    assertTrue(moved * side > 0.3, "alongX=" + alongX + " hingeMax=" + hingeMax + " side=" + side + " moved=" + moved);
                }
            }
        }
    }

    @Test
    void closedDoorObbCoversDoorway() {
        Door d = new Door(5, 64, 9, true, false);
        // 문틀 앞에서 법선 방향으로 쏘면 맞아야 함
        Vec3 origin = new Vec3(5.5, 65, 7);
        double t = d.obb().rayIntersect(origin, new Vec3(0, 0, 1), 10);
        assertTrue(t > 0 && t < 3, "t=" + t);
        // 옆 칸으로 쏘면 빗나감
        assertEquals(-1, d.obb().rayIntersect(new Vec3(7.5, 65, 7), new Vec3(0, 0, 1), 10));
    }

    @Test
    void openDoorMovesOutOfDoorway() {
        Door d = new Door(5, 64, 9, true, false);
        swing(d, new Vec3(0, 0, 1));
        // 90도 이상 열리면 문틀 중앙을 지나는 총알이 문판에 맞지 않음
        if (Math.abs(d.physics.angle()) > 80) {
            double t = d.obb().rayIntersect(new Vec3(5.6, 65, 7), new Vec3(0, 0, 1), 4);
            assertEquals(-1, t, "열린 문이 문틀을 막음, angle=" + d.physics.angle());
        }
    }

    @Test
    void walkingThroughPushesPanelOutOfTheBodyWithoutKnockingDown() {
        // 북쪽으로 걸어 문을 밀고 지나가는 동안 문판이 몸과 겹친 채로 남지 않아야 함
        Door d = new Door(0, 64, 0, true, false);
        Vec3 walk = new Vec3(0, 0, -1);
        d.pushAlong(walk, 9, null, false);
        d.physics.tick();
        Vec3 p = new Vec3(0.5, 64, 1.3);
        for (int t = 0; t < 12; t++) {
            p = p.add(walk.mul(0.29));                  // 사람 걷는 속도 (블록/틱)
            Vec3 body = p.add(0, 0.9, 0);
            if (!d.physics.isClosed() && d.obb().overlapsPoint(body, 0.32)) {
                Vec3 away = p.sub(d.hinge()).horizontal();
                Vec3 tangent = new Vec3(-d.dir().z(), 0, d.dir().x());
                int side = away.dot(tangent) >= 0 ? -1 : 1;
                int toward = tangent.mul(side).dot(d.normal()) >= 0 ? 1 : -1;
                d.pushOutOf(body, 0.32, d.rotationSignToward(toward));
                assertFalse(d.obb().overlapsPoint(body, 0.32) && Math.abs(d.physics.angle()) < dev.violence.logic.DoorPhysics.MAX_ANGLE,
                        "문판이 몸을 비켜나야 함 (틱 " + t + ")");
                assertFalse(d.physics.isDangerous(), "걸어서 민 문은 사람을 쓰러뜨릴 만큼 빠르면 안 됨");
            }
            d.physics.tick();
        }
        assertTrue(Math.abs(d.physics.angle()) > 45, "지나간 뒤 문이 충분히 열려 있어야 함: " + d.physics.angle());
    }
}
