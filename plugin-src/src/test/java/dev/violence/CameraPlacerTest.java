package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.combat.CameraPlacer;
import dev.violence.math.Vec3;
import java.util.List;
import org.junit.jupiter.api.Test;

class CameraPlacerTest {
    /** 가로 3칸, 세로 5칸, 높이 3칸 방 (x: -1.5..1.5, y: 0..3, z: -2.5..2.5) 안에서만 시야가 트임 */
    private static double roomRay(Vec3 from, Vec3 to) {
        Vec3 d = to.sub(from);
        double len = d.length();
        for (double t = 0; t <= len; t += 0.01) {
            Vec3 p = from.add(d.mul(t / len));
            if (Math.abs(p.x()) > 1.5 || p.y() < 0 || p.y() > 3 || Math.abs(p.z()) > 2.5) return t;
        }
        return len;
    }

    @Test
    void picksFirstClearCandidate() {
        Vec3 look = new Vec3(0, 1, 0);
        Vec3 inWall = new Vec3(2.6, 2.1, 0);      // 오른쪽 벽 너머
        Vec3 clear = new Vec3(0, 2.6, -2.0);       // 방 안 뒤쪽 위
        assertEquals(clear, CameraPlacer.place(look, List.of(inWall, clear), CameraPlacerTest::roomRay));
    }

    @Test
    void allBlockedPullsTheCameraInsideTheRoom() {
        Vec3 look = new Vec3(0, 1, 0);
        Vec3 cam = CameraPlacer.place(look, List.of(new Vec3(2.6, 2.1, 0), new Vec3(-2.6, 2.1, 0), new Vec3(0, 4.2, 0)), CameraPlacerTest::roomRay);
        assertTrue(Math.abs(cam.x()) < 1.5 && cam.y() < 3 && cam.y() > 0, "방 안 " + cam);
        assertTrue(cam.distance(look) >= CameraPlacer.MIN_DIST - 1e-9, "너무 가깝지 않게");
    }
}
