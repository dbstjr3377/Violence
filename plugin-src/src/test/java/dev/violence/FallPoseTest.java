package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.fx.FallPose;
import java.util.Map;
import org.joml.Quaterniond;
import org.joml.Vector3d;
import org.junit.jupiter.api.Test;

class FallPoseTest {
    private final Map<FallPose.Kind, FallPose> all = FallPose.loadAll();

    private static void same(FallPose.Placement a, FallPose.Placement b, String what) {
        assertTrue(a.center().distance(b.center()) < 1e-3, what + " 위치 " + a.center() + " / " + b.center());
        assertTrue(FallPose.angleBetween(a.rotation(), b.rotation()) < 1e-3, what + " 회전");
    }

    private static FallPose.Placement shifted(FallPose.Placement p, double dz, double scale) {
        return new FallPose.Placement(new Vector3d(p.center()).add(0, 0, dz * scale), new Quaterniond(p.rotation()));
    }

    @Test
    void everyKindIsLoaded() {
        for (FallPose.Kind k : FallPose.Kind.values()) assertTrue(all.get(k).frameCount() >= 6, k + " 프레임");
        assertEquals(FallPose.End.FACE_UP, all.get(FallPose.Kind.BACK).end());
        assertEquals(FallPose.End.FACE_UP, all.get(FallPose.Kind.BLAST).end());
        assertEquals(FallPose.End.SIT, all.get(FallPose.Kind.WALL).end());
        assertEquals(FallPose.End.FACE_UP, all.get(FallPose.Kind.WALL_DEATH).end());
        assertEquals(FallPose.End.STAND, all.get(FallPose.Kind.KICK).end());
    }

    @Test
    void lyingKindsEndInVanillaSleepingPose() {
        for (FallPose.Kind k : new FallPose.Kind[] {FallPose.Kind.BACK, FallPose.Kind.BLAST, FallPose.Kind.WALL_DEATH}) {
            FallPose p = all.get(k);
            int last = p.frameCount() - 1;
            for (FallPose.Part part : FallPose.Part.values()) {
                same(p.place(last, part, 1.2), shifted(FallPose.vanillaBack(part, 1.2, p.lift()), p.endForward(), 1.2), k + " " + part);
            }
        }
    }

    @Test
    void wallSlumpEndsInVanillaSittingPoseAndDeathStartsThere() {
        FallPose wall = all.get(FallPose.Kind.WALL);
        FallPose death = all.get(FallPose.Kind.WALL_DEATH);
        FallPose.Config c = wall.config();
        for (FallPose.Part part : FallPose.Part.values()) {
            FallPose.Placement sit = FallPose.vanillaSit(part, 1.0, c.seatY(), c.sitHeadPitch());
            same(wall.place(wall.frameCount() - 1, part, 1.0), sit, "벽 끝 " + part);
            same(death.place(0, part, 1.0), sit, "벽 사망 시작 " + part);
        }
        // 누운 머리가 벽(앉은 자리 뒤 wall_gap)을 뚫지 않음
        FallPose.Placement head = death.place(death.frameCount() - 1, FallPose.Part.HEAD, 1.0);
        assertTrue(head.center().z - 4 * FallPose.PX > -c.wallGap(), "머리가 벽 안으로 " + head.center().z);
    }

    @Test
    void kickEndsStandingAndReachesForward() {
        FallPose kick = all.get(FallPose.Kind.KICK);
        int last = kick.frameCount() - 1;
        FallPose stand = new FallPose(java.util.List.of(new FallPose.Frame(0, 0, 0, 1, Map.of())), 1);
        for (FallPose.Part part : FallPose.Part.values()) same(kick.place(last, part, 1), stand.place(0, part, 1), "발차기 끝 " + part);
        FallPose.Placement leg = kick.place(kick.contact(), FallPose.Part.LEG_R, 1);
        Vector3d foot = leg.rotation().transform(new Vector3d(0, -6 * FallPose.PX, 0)).add(leg.center());
        assertTrue(foot.z > 0.4 && foot.y > 0.95, "발이 앞 위로 " + foot);
    }

    @Test
    void sleepingPoseLiesOnTheBackWithHeadBehind() {
        FallPose.Placement body = FallPose.vanillaBack(FallPose.Part.BODY, 1, 0.14);
        Vector3d up = body.rotation().transform(new Vector3d(0, 1, 0));
        Vector3d front = body.rotation().transform(new Vector3d(0, 0, 1));
        Vector3d left = body.rotation().transform(new Vector3d(1, 0, 0));
        assertTrue(up.z < -0.99, "머리가 뒤쪽");
        assertTrue(front.y > 0.99, "얼굴(가슴)이 위");
        assertTrue(left.x > 0.99, "좌우는 그대로");
        assertEquals(-90, FallPose.sleepingYaw(0), 1e-6);
        assertEquals(180, Math.abs(FallPose.sleepingYaw(90)), 1e-6);
    }

    @Test
    void alwaysFallsBackward() {
        assertEquals(FallPose.Kind.BACK, FallPose.kindFor(false, false));
        assertEquals(FallPose.Kind.BLAST, FallPose.kindFor(true, false));
        assertEquals(FallPose.Kind.WALL, FallPose.kindFor(true, true));
        // 등 뒤에서 맞으면 처음 3프레임에 걸쳐 맞은 쪽으로 돌아섬 (짧은 쪽으로)
        assertEquals(170, FallPose.spinYaw(170, -10, 0), 1e-6);
        assertEquals(350, ((FallPose.spinYaw(170, -10, 3) % 360) + 360) % 360, 1e-6);
        assertEquals(-20, FallPose.spinYaw(10, -20, 5), 1e-6);
        assertEquals(70, FallPose.spinYaw(10, 70, 9), 1e-6);
    }

    @Test
    void noPartSinksIntoTheFloorDuringAnyFall() {
        FallPose.Config c = all.get(FallPose.Kind.BACK).config();
        for (Map.Entry<FallPose.Kind, FallPose> e : all.entrySet()) {
            FallPose pose = e.getValue();
            for (int f = 0; f < pose.frameCount(); f++) {
                for (FallPose.Part p : FallPose.Part.values()) {
                    FallPose.Placement pl = pose.place(f, p, 1);
                    Vector3d h = new Vector3d(p.size).mul(FallPose.PX / 2);
                    double low = Double.MAX_VALUE;
                    for (int i = 0; i < 8; i++) {
                        Vector3d corner = new Vector3d((i & 1) == 0 ? -h.x : h.x, (i & 2) == 0 ? -h.y : h.y, (i & 4) == 0 ? -h.z : h.z);
                        low = Math.min(low, pl.rotation().transform(corner).add(pl.center()).y);
                    }
                    assertTrue(low > -0.12, e.getKey() + " 프레임 " + f + " " + p + " 바닥 아래 " + low);
                }
            }
        }
        assertTrue(c.seatY() < 0);
    }

    @Test
    void worldTransformFollowsYaw() {
        Vector3d fwd = FallPose.toWorld(new Vector3d(0, 0, 1), 90);
        assertEquals(-1, fwd.x, 1e-9);
        assertEquals(0, fwd.z, 1e-9);
        Vector3d left = FallPose.toWorld(new Vector3d(1, 0, 0), 0);
        assertEquals(1, left.x, 1e-9);
    }
}
