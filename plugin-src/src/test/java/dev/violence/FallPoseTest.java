package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.fx.FallPose;
import org.joml.Vector3d;
import org.junit.jupiter.api.Test;

class FallPoseTest {
    private final FallPose pose = FallPose.load();

    @Test
    void sixFramesAtTwentyFpsThenHoldUntilVanillaPoseFinishesBlending() {
        assertEquals(6, pose.frameCount());
        // 바닐라 엎드리기 전환: 틱당 0.09 → 12틱이면 끝남
        assertTrue(pose.holdTicks() >= Math.ceil(1 / 0.09), "인형을 바닐라 전환이 끝날 때까지 보여줘야 함");
        assertEquals(5, pose.frameAt(40));
        assertEquals(0, pose.frameAt(0));
    }

    @Test
    void lastFrameMatchesVanillaLyingPose() {
        int last = pose.frameCount() - 1;
        for (FallPose.Part p : FallPose.Part.values()) {
            for (double scale : new double[] {1.0, 1.2}) {
                FallPose.Placement a = pose.place(last, p, scale);
                FallPose.Placement b = FallPose.vanillaLying(p, scale);
                assertTrue(a.center().distance(b.center()) < 1e-6, p + " 위치 " + a.center() + " / " + b.center());
                assertTrue(FallPose.angleBetween(a.rotation(), b.rotation()) < 1e-6, p + " 회전");
            }
        }
    }

    @Test
    void lyingBodyIsFaceDownAndHeadFacesForward() {
        FallPose.Placement body = FallPose.vanillaLying(FallPose.Part.BODY, 1);
        Vector3d up = body.rotation().transform(new Vector3d(0, 1, 0));
        Vector3d front = body.rotation().transform(new Vector3d(0, 0, 1));
        assertTrue(up.z > 0.99, "몸 위쪽이 앞을 향함 (머리가 앞)");
        assertTrue(front.y < -0.99, "가슴이 바닥을 향함");
        assertEquals(0.3, body.center().y, 0.01);
    }

    @Test
    void noPartSinksIntoTheFloorDuringTheFall() {
        for (int f = 0; f < pose.frameCount(); f++) {
            for (FallPose.Part p : FallPose.Part.values()) {
                FallPose.Placement pl = pose.place(f, p, 1);
                Vector3d h = new Vector3d(p.size).mul(FallPose.PX / 2);
                double low = Double.MAX_VALUE;
                for (int i = 0; i < 8; i++) {
                    Vector3d corner = new Vector3d((i & 1) == 0 ? -h.x : h.x, (i & 2) == 0 ? -h.y : h.y, (i & 4) == 0 ? -h.z : h.z);
                    low = Math.min(low, pl.rotation().transform(corner).add(pl.center()).y);
                }
                assertTrue(low > -0.12, "프레임 " + f + " " + p + " 바닥 아래 " + low);
            }
        }
    }

    @Test
    void worldTransformFollowsYaw() {
        // 바닐라: yaw 0 = 남쪽(+Z), yaw 90 = 서쪽(-X)
        Vector3d fwd = FallPose.toWorld(new Vector3d(0, 0, 1), 90);
        assertEquals(-1, fwd.x, 1e-9);
        assertEquals(0, fwd.z, 1e-9);
        Vector3d left = FallPose.toWorld(new Vector3d(1, 0, 0), 0);
        assertEquals(1, left.x, 1e-9);   // 남쪽을 보면 왼쪽이 동쪽(+X)
    }
}
