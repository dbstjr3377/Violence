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

    @Test
    void narrowCorridorFindsAClearSpotAwayFromTheTarget() {
        // 복도: 가로 3칸, 높이 3칸, 길이 방향으로만 트임 → 옆·위 후보는 모두 막힘
        Vec3 look = new Vec3(0, 1, 0);
        CameraPlacer.Ray corridor = (from, to) -> {
            Vec3 d = to.sub(from);
            double len = d.length();
            for (double t = 0; t <= len; t += 0.01) {
                Vec3 p = from.add(d.mul(t / len));
                if (Math.abs(p.x()) > 1.5 || p.y() < 0 || p.y() > 3) return t;
            }
            return len;
        };
        Vec3 cam = CameraPlacer.place(look, List.of(new Vec3(2.6, 3.1, -0.5), new Vec3(-2.6, 3.1, -0.5), new Vec3(0, 4.2, 0)), corridor);
        assertTrue(cam.distance(look) >= 1.5 - 1e-6, "인형 머리 속이 아니라 떨어진 자리 " + cam);
        assertTrue(Math.abs(cam.x()) <= 1.5 && cam.y() <= 3, "복도 안 " + cam);
    }

    @Test
    void rejectsASpotHuggingTheWall() {
        // 벽에서 0.1블록 떨어진 자리는 시야가 트였어도 쓰지 않음 (화면이 벽 속으로 들어가 어두워짐)
        Vec3 look = new Vec3(0, 1, 0);
        Vec3 hugging = new Vec3(1.4, 2.0, 0);
        Vec3 inside = new Vec3(0, 2.4, -1.8);
        assertEquals(inside, CameraPlacer.place(look, List.of(hugging, inside), CameraPlacerTest::roomRay));
        // 다른 후보가 없으면 둘레에서 벽과 떨어진 자리를 찾음
        Vec3 cam = CameraPlacer.place(look, List.of(hugging), CameraPlacerTest::roomRay);
        assertTrue(1.5 - Math.abs(cam.x()) >= CameraPlacer.CLEARANCE - 1e-6 && 2.5 - Math.abs(cam.z()) >= CameraPlacer.CLEARANCE - 1e-6
                && 3 - cam.y() >= CameraPlacer.CLEARANCE - 1e-6, "벽과 떨어짐 " + cam);
    }
}
