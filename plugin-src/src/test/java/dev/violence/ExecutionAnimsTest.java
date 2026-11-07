package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.fx.ExecutionAnims;
import dev.violence.fx.FallPose;
import dev.violence.mask.Mask;
import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.joml.Vector3d;
import org.junit.jupiter.api.Test;

class ExecutionAnimsTest {
    private final ExecutionAnims anims = ExecutionAnims.load();

    private WeaponRegistry weapons() {
        return WeaponRegistry.load(new InputStreamReader(
                getClass().getClassLoader().getResourceAsStream("weapons.yml"), StandardCharsets.UTF_8));
    }

    @Test
    void sixAnimationsWithConsistentTiming() {
        for (String n : new String[] {"fist", "stomp", "blunt", "heavy", "light", "blade"}) {
            ExecutionAnims.Anim a = anims.get(n);
            assertNotNull(a, n);
            if (a.hits()) {
                assertNotNull(a.readyExec(), n);
                assertTrue(a.impact() > 0 && a.impact() < a.strikeLength(), n + " 닿는 틱");
                assertEquals(a.strikeLength(), a.strikeVictim().length(), n + " 처형자·피처형자 길이");
            } else {
                assertTrue(a.impacts().length > 0, n);
                for (int i : a.impacts()) assertTrue(i > 0 && i < a.fullLength(), n + " 닿는 틱");
                assertTrue(a.kill() >= a.impacts()[0] && a.kill() < a.fullLength(), n + " 처치 틱");
                assertEquals(a.fullLength(), a.fullVictim().length(), n + " 처형자·피처형자 길이");
            }
        }
        assertEquals("both", anims.get("blunt").weapon());
        assertEquals("right", anims.get("light").weapon());
        assertEquals("none", anims.get("fist").weapon());
    }

    @Test
    void everyMeleeWeaponHasAGroupAndMatchingStyle() {
        WeaponRegistry r = weapons();
        Map<String, ExecutionStyle> want = Map.of("blunt", ExecutionStyle.HITS, "light", ExecutionStyle.HITS,
                "heavy", ExecutionStyle.AUTO, "blade", ExecutionStyle.AUTO);
        for (WeaponType t : r.all()) {
            if (!t.isMelee()) continue;
            String g = anims.groupOf(t.id());
            assertNotNull(g, t.id() + " 처형 묶음 없음");
            assertEquals(want.get(g), t.execution(), t.id() + " 처형 방식");
            if (g.equals("blunt") || g.equals("light")) assertEquals(3, t.executionHits(), t.id());
        }
        assertEquals(5, r.fist().executionHits());
        assertNotNull(r.get("sledgehammer"), "오함마");
        assertEquals("heavy", anims.groupOf("sledgehammer"));
    }

    @Test
    void animationChoice() {
        WeaponRegistry r = weapons();
        assertEquals("fist", anims.animFor(r.fist(), null));
        assertEquals("fist", anims.animFor(r.fist(), Mask.TONY));
        assertEquals("stomp", anims.animFor(r.fist(), Mask.JAKE));
        assertEquals("stomp", anims.animFor(r.fist(), Mask.PIG_BUTCHER));
        assertEquals("stomp", anims.animFor(r.fist(), Mask.MARK));
        assertEquals("blunt", anims.animFor(r.get("crowbar"), Mask.JAKE));
        assertEquals("heavy", anims.animFor(r.get("katana"), null));
        assertEquals("light", anims.animFor(r.get("frying_pan"), null));
        assertEquals("blade", anims.animFor(r.get("pool_cue_short"), null));
    }

    /** 처형자 기준 좌표의 누운 머리 중심 (기준점 = 발에서 머리 쪽 anchor) */
    private static Vector3d headInExecutorFrame(ExecutionAnims.Anim a) {
        FallPose.Placement h = FallPose.vanillaBack(FallPose.Part.HEAD, 1, FallPose.Config.DEFAULT.backLift());
        return new Vector3d(-h.center().x, h.center().y, -h.center().z - a.anchor());
    }

    private static Vector3d weaponPoint(ExecutionAnims.Anim a, ExecutionAnims.Track t, int frame, double[] grip, double alongPx) {
        FallPose.Placement w = ExecutionAnims.weapon(t, frame, 1, grip);
        double s = ExecutionAnims.WEAPON_SCALE;
        Vector3d p = new Vector3d(grip[0] / 16 - 0.5, (grip[1] + alongPx) / 16 - 0.5, grip[2] / 16 - 0.5).mul(s);
        return w.rotation().transform(p).add(w.center());
    }

    @Test
    void weaponsLandOnTheHeadAtImpact() {
        double[][] cases = {{22, 0}, {23.5, 1}, {8.5, 2}};
        String[] names = {"blunt", "heavy", "light"};
        String[] sample = {"bat", "sledgehammer", "cleaver"};
        for (int i = 0; i < names.length; i++) {
            ExecutionAnims.Anim a = anims.get(names[i]);
            ExecutionAnims.Track t = a.hits() ? a.strikeExec() : a.fullExec();
            int f = a.hits() ? a.impact() : a.impacts()[0];
            Vector3d p = weaponPoint(a, t, f, anims.grip(sample[i]), cases[i][0]);
            double d = p.distance(headInExecutorFrame(a).add(0, 0.18, 0));
            assertTrue(d < 0.3, names[i] + " 무기가 머리에서 " + d);
            // 들어 올린 대기 자세는 머리 위
            if (a.hits()) assertTrue(weaponPoint(a, a.readyExec(), 0, anims.grip(sample[i]), cases[i][0]).y > 1.6, names[i] + " 대기 높이");
        }
    }

    private static java.util.List<ExecutionAnims.Track> execTracks(ExecutionAnims.Anim a) {
        java.util.List<ExecutionAnims.Track> out = new java.util.ArrayList<>();
        for (ExecutionAnims.Track t : new ExecutionAnims.Track[] {a.readyExec(), a.strikeExec(), a.fullExec()}) if (t != null) out.add(t);
        return out;
    }

    @Test
    void handsStayOnTheWeapon() {
        // 두 마디 팔: 오른손은 쥐는 곳, 두 손 무기는 왼손이 그 아래 손잡이에 (플러그인 팔 계산 = 만든 도구의 IK)
        for (ExecutionAnims.Anim a : anims.all().values()) {
            if ("none".equals(a.weapon())) continue;
            for (ExecutionAnims.Track t : execTracks(a)) {
                for (int i = 0; i < t.length(); i++) {
                    Vector3d g = ExecutionAnims.grip(t, i, 1);
                    assertNotNull(g, a.name() + " 무기 없음 " + i);
                    double dr = t.pose().hand(i, FallPose.Part.FOREARM_R, 1).distance(g);
                    assertTrue(dr < 0.07, a.name() + " " + i + "틱 오른손이 손잡이에서 " + dr);
                    if ("both".equals(a.weapon())) {
                        Vector3d d = ExecutionAnims.weaponRotation(t, i).transform(new Vector3d(0, 1, 0));
                        Vector3d left = new Vector3d(g).sub(d.mul(3.4 / 16 * ExecutionAnims.WEAPON_SCALE));
                        double dl = t.pose().hand(i, FallPose.Part.FOREARM_L, 1).distance(left);
                        assertTrue(dl < 0.07, a.name() + " " + i + "틱 왼손이 손잡이에서 " + dl);
                    }
                }
            }
        }
    }

    @Test
    void weaponNeverSpinsBetweenFrames() {
        // 무기 회전이 한 틱에 100° 넘게 바뀌면 손 안에서 휙 도는 것처럼 보임
        for (ExecutionAnims.Anim a : anims.all().values()) {
            if ("none".equals(a.weapon())) continue;
            for (ExecutionAnims.Track t : execTracks(a)) {
                for (int i = 1; i < t.length(); i++) {
                    double ang = Math.toDegrees(FallPose.angleBetween(ExecutionAnims.weaponRotation(t, i - 1), ExecutionAnims.weaponRotation(t, i)));
                    assertTrue(ang < 100, a.name() + " 무기가 " + i + "틱에 " + ang + "° 돎");
                }
            }
        }
    }

    @Test
    void executorStaysAboveTheFloor() {
        for (ExecutionAnims.Anim a : anims.all().values()) {
            for (ExecutionAnims.Track t : execTracks(a)) {
                for (int f = 0; f < t.length(); f++) {
                    for (FallPose.Part p : FallPose.Part.values()) {
                        FallPose.Placement pl = t.pose().place(f, p, 1);
                        Vector3d h = new Vector3d(p.size).mul(FallPose.PX / 2);
                        double low = Double.MAX_VALUE;
                        for (int i = 0; i < 8; i++) {
                            Vector3d c = new Vector3d((i & 1) == 0 ? -h.x : h.x, (i & 2) == 0 ? -h.y : h.y, (i & 4) == 0 ? -h.z : h.z);
                            low = Math.min(low, pl.rotation().transform(c).add(pl.center()).y);
                        }
                        assertTrue(low > -0.1, a.name() + " " + f + "틱 " + p + " 바닥 아래 " + low);
                    }
                }
            }
        }
    }

    @Test
    void kneelingLegsBendAtTheKnee() {
        // 올라탄 자세는 무릎을 꿇음: 정강이가 허벅지와 크게 꺾이고 발은 바닥 가까이
        for (String n : new String[] {"fist", "blunt", "heavy", "light", "blade"}) {
            ExecutionAnims.Anim a = anims.get(n);
            ExecutionAnims.Track t = a.hits() ? a.readyExec() : a.fullExec();
            double ang = Math.toDegrees(FallPose.angleBetween(t.pose().place(0, FallPose.Part.LEG_R, 1).rotation(),
                    t.pose().place(0, FallPose.Part.SHIN_R, 1).rotation()));
            assertTrue(ang > 50, n + " 무릎 " + ang);
            assertTrue(t.pose().foot(0, FallPose.Part.SHIN_R, 1).y < 0.25, n + " 발 높이");
        }
    }

    @Test
    void strikeFaceLeadsAtImpact() {
        // 내려치는 순간 무기의 앞면(모델 +Z: 갈고리·도끼날·식칼 날)이 아래(머리 쪽)를 봄
        for (String n : new String[] {"blunt", "heavy", "light"}) {
            ExecutionAnims.Anim a = anims.get(n);
            ExecutionAnims.Track t = a.hits() ? a.strikeExec() : a.fullExec();
            int f = a.hits() ? a.impact() : a.impacts()[0];
            var r = ExecutionAnims.weapon(t, f, 1.0, new double[] {8, 3.5, 8}).rotation();
            Vector3d front = r.transform(new Vector3d(0, 0, 1));
            assertTrue(front.y < -0.3, n + " 앞면이 아래를 보지 않음 " + front);
        }
    }
}
