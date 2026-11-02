package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.math.Aabb;
import dev.violence.math.Hitbox;
import dev.violence.math.Obb;
import dev.violence.math.Vec3;
import org.junit.jupiter.api.Test;

class MathTest {

    @Test
    void yawPitchRoundTrip() {
        for (double yaw = -170; yaw <= 180; yaw += 37) {
            for (double pitch = -80; pitch <= 80; pitch += 23) {
                Vec3 d = Vec3.fromYawPitch(yaw, pitch);
                assertEquals(1.0, d.length(), 1e-9);
                assertEquals(pitch, d.pitch(), 1e-6);
                double dy = ((d.yaw() - yaw) % 360 + 540) % 360 - 180;
                assertEquals(0, dy, 1e-6);
            }
        }
        // 마인크래프트: yaw 0 = +Z (남쪽)
        Vec3 south = Vec3.fromYawPitch(0, 0);
        assertEquals(1, south.z(), 1e-9);
    }

    @Test
    void aabbRay() {
        Aabb box = new Aabb(0, 0, 0, 1, 1, 1);
        assertEquals(2.0, box.rayIntersect(new Vec3(-2, 0.5, 0.5), new Vec3(1, 0, 0), 10), 1e-9);
        assertEquals(-1, box.rayIntersect(new Vec3(-2, 2, 0.5), new Vec3(1, 0, 0), 10));
        assertEquals(-1, box.rayIntersect(new Vec3(-2, 0.5, 0.5), new Vec3(1, 0, 0), 1.5));
    }

    @Test
    void headshotVsBodyshot() {
        Vec3 feet = new Vec3(10, 64, 0);
        // 눈높이로 수평 사격 → 머리
        Hitbox.Result head = Hitbox.raycastStanding(feet, 1, new Vec3(0, 64 + 1.62, 0), new Vec3(1, 0, 0), 50);
        assertEquals(Hitbox.Part.HEAD, head.part());
        // 허리 높이 → 몸통
        Hitbox.Result body = Hitbox.raycastStanding(feet, 1, new Vec3(0, 64 + 0.9, 0), new Vec3(1, 0, 0), 50);
        assertEquals(Hitbox.Part.BODY, body.part());
        // 빗나감
        Hitbox.Result miss = Hitbox.raycastStanding(feet, 1, new Vec3(0, 64 + 0.9, 3), new Vec3(1, 0, 0), 50);
        assertFalse(miss.hit());
    }

    @Test
    void obbRotatedDoor() {
        // 폭 1, 높이 2, 두께 0.2 문판을 90도 회전
        Obb door = new Obb(new Vec3(0, 1, 0), new Vec3(0.5, 1, 0.1), Math.PI / 2);
        // 회전 후 문판은 Z 축을 따라 길어짐 → X 방향 레이로 두께 부분을 맞춤
        assertTrue(door.rayIntersect(new Vec3(-3, 1, 0.3), new Vec3(1, 0, 0), 10) > 0);
        assertEquals(-1, door.rayIntersect(new Vec3(-3, 1, 0.8), new Vec3(1, 0, 0), 10));
    }
}
