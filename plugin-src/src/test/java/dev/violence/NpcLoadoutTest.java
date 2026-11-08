package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.npc.NpcLoadout;
import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;

class NpcLoadoutTest {
    private final WeaponRegistry reg = WeaponRegistry.load(new InputStreamReader(
            getClass().getClassLoader().getResourceAsStream("weapons.yml"), StandardCharsets.UTF_8));

    private static Map<NpcLoadout.Kind, Integer> count(List<NpcLoadout.Kind> l) {
        Map<NpcLoadout.Kind, Integer> m = new EnumMap<>(NpcLoadout.Kind.class);
        for (NpcLoadout.Kind k : NpcLoadout.Kind.values()) m.put(k, 0);
        for (NpcLoadout.Kind k : l) m.merge(k, 1, Integer::sum);
        return m;
    }

    @Test
    void batchMatchesThreeFifthsArmedTwoFifthsGuns() {
        // 5명 중 3명 무기, 그중 5분의 2 총·5분의 3 근접
        Map<NpcLoadout.Kind, Integer> five = count(NpcLoadout.batch(5, 0.6, 0.4, new Random(1)));
        assertEquals(2, five.get(NpcLoadout.Kind.UNARMED));
        assertEquals(1, five.get(NpcLoadout.Kind.GUN));
        assertEquals(2, five.get(NpcLoadout.Kind.MELEE));
        Map<NpcLoadout.Kind, Integer> twentyFive = count(NpcLoadout.batch(25, 0.6, 0.4, new Random(2)));
        assertEquals(10, twentyFive.get(NpcLoadout.Kind.UNARMED));
        assertEquals(6, twentyFive.get(NpcLoadout.Kind.GUN));
        assertEquals(9, twentyFive.get(NpcLoadout.Kind.MELEE));
    }

    @Test
    void respawnRollKeepsTheSameRatioOnAverage() {
        Random r = new Random(3);
        int n = 200_000;
        int[] c = new int[3];
        for (int i = 0; i < n; i++) c[NpcLoadout.roll(0.6, 0.4, r).ordinal()]++;
        assertEquals(0.40, c[0] / (double) n, 0.01);   // 맨손
        assertEquals(0.24, c[1] / (double) n, 0.01);   // 총 = 3/5 × 2/5
        assertEquals(0.36, c[2] / (double) n, 0.01);   // 근접 = 3/5 × 3/5
    }

    @Test
    void pickedWeaponsMatchTheKind() {
        Random r = new Random(4);
        for (int i = 0; i < 500; i++) {
            WeaponType g = NpcLoadout.pick(NpcLoadout.Kind.GUN, reg, r);
            assertTrue(g.isGun() && g.mapSpawn(), g.id());
            WeaponType m = NpcLoadout.pick(NpcLoadout.Kind.MELEE, reg, r);
            assertTrue(m.isMelee() && m.mapSpawn(), m.id());
        }
        assertNull(NpcLoadout.pick(NpcLoadout.Kind.UNARMED, reg, r));
    }
}
