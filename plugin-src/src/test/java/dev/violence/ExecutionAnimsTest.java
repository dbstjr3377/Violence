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
}
