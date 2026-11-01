package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponCategory;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import org.junit.jupiter.api.Test;

class WeaponRegistryTest {

    private WeaponRegistry load() {
        return WeaponRegistry.load(new InputStreamReader(
                getClass().getClassLoader().getResourceAsStream("weapons.yml"), StandardCharsets.UTF_8));
    }

    @Test
    void fireAnimationFollowsFireRate() {
        WeaponRegistry r = load();
        // 연사 무기는 발사 간격의 약 2배 → 쏠 때마다 화염이 깜빡임
        assertEquals(2, r.get("uzi").fireAnimTicks());
        assertEquals(3, r.get("m16").fireAnimTicks());
        // 단발 무기는 반동 잡기 동작을 끝까지
        assertEquals(6, r.get("magnum").fireAnimTicks());
        assertEquals(6, r.get("shotgun").fireAnimTicks());
    }

    @Test
    void specValues() {
        WeaponRegistry r = load();
        WeaponType sg = r.get("shotgun");
        assertEquals(6, sg.ammo());
        assertEquals(12, sg.pelletsMin());
        assertEquals(130, sg.rpm());
        WeaponType db = r.get("double_barrel");
        assertEquals(2, db.ammo());
        assertEquals(20, db.pelletsMin());
        assertEquals(28, db.pelletsMax());
        assertTrue(db.spread() > sg.spread());
        assertEquals(24, r.get("m16").ammo());
        assertEquals(860, r.get("m16").rpm());
        assertEquals(30, r.get("uzi").ammo());
        assertEquals(1800, r.get("uzi").rpm());
        assertEquals(13, r.get("silenced_pistol").ammo());
        assertTrue(r.get("silenced_pistol").silenced());
        assertFalse(r.get("silenced_pistol").automatic());
        assertFalse(r.get("silenced_uzi").mapSpawn());
        assertTrue(r.get("magnum").pierce());
        assertEquals(6, r.get("magnum").ammo());
        assertEquals(32, r.get("mp5").ammo());
        assertEquals(1200, r.get("mp5").rpm());
        assertEquals(ExecutionStyle.AUTO, r.get("dagger").execution());
        assertEquals(0.5, r.get("dagger").throwKillChance());
        assertEquals("pool_cue_short", r.get("pool_cue").breaksInto());
        assertEquals(WeaponCategory.FIST, r.fist().category());
        // 긴 큐대 = 몽둥이, 짧은 큐대 = 단검과 동일한 성능
        assertEquals(r.get("bat").meleeCooldown(), r.get("pool_cue").meleeCooldown());
        assertEquals(r.get("bat").meleeRange(), r.get("pool_cue").meleeRange());
        assertEquals(r.get("dagger").meleeCooldown(), r.get("pool_cue_short").meleeCooldown());
        assertEquals(r.get("dagger").meleeRange(), r.get("pool_cue_short").meleeRange());
        assertEquals(r.get("dagger").execution(), r.get("pool_cue_short").execution());
        // 망치·서류가방은 공격속도가 낮다
        assertTrue(r.get("hammer").meleeCooldown() > r.get("bat").meleeCooldown());
        assertTrue(r.get("briefcase").meleeCooldown() > r.get("bat").meleeCooldown());
        for (String t : new String[]{"small_hammer", "bottle", "throwing_knife", "dart", "brick", "scissors"}) {
            assertEquals(WeaponCategory.THROWABLE, r.get(t).category(), t);
            assertEquals(1.0, r.get(t).throwKillChance(), t);
        }
    }

    @Test
    void randomSpawnNeverPicksHidden() {
        WeaponRegistry r = load();
        Random rnd = new Random(5);
        for (int i = 0; i < 2000; i++) {
            WeaponType t = r.randomSpawnable(rnd);
            assertTrue(t.mapSpawn(), t.id());
            assertNotEquals("silenced_uzi", t.id());
        }
    }

    @Test
    void dualMp5Magazine() {
        WeaponRegistry r = load();
        WeaponInstance w = new WeaponInstance(r.get("mp5_dual"));
        assertEquals(64, w.ammo());
        assertEquals(32, w.mag());
        long tick = 0;
        for (int i = 0; i < 32; i++) assertTrue(w.consume(tick));
        // 탄창이 비면 자동 재장전
        assertTrue(w.isReloading(tick + 1));
        assertFalse(w.consume(tick + 1));
        assertTrue(w.consume(tick + 40));
        assertEquals(31, w.ammo());
    }
}
