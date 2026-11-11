package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import dev.violence.fx.ExecutionAnims;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponLabels;
import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class WeaponLabelsTest {
    private final WeaponRegistry reg = WeaponRegistry.load(new InputStreamReader(
            getClass().getClassLoader().getResourceAsStream("weapons.yml"), StandardCharsets.UTF_8));
    private final ExecutionAnims anims = ExecutionAnims.load();

    @Test
    void everyWeaponHasAKind() {
        for (WeaponType t : reg.all()) {
            String k = WeaponLabels.kind(t, anims.groupOf(t.id()));
            assertNotEquals("총기", k, t.id());
            if (t.isMelee()) assertEquals("근접 무기", k, t.id());
        }
        assertEquals("소총", WeaponLabels.kind(reg.get("m16"), null));
        assertEquals("샷건", WeaponLabels.kind(reg.get("double_barrel"), null));
        assertEquals("권총", WeaponLabels.kind(reg.get("magnum"), null));
        assertEquals("근접 무기", WeaponLabels.kind(reg.get("crowbar"), anims.groupOf("crowbar")));
        assertEquals("근접 무기", WeaponLabels.kind(reg.get("sledgehammer"), anims.groupOf("sledgehammer")));
    }

    @Test
    void ammoTextAndWidth() {
        WeaponInstance w = new WeaponInstance(reg.get("m16"));
        assertEquals("24 / 24", WeaponLabels.ammo(w));
        w.setAmmo(0);
        assertEquals("0 / 24", WeaponLabels.ammo(w));
        assertNull(WeaponLabels.ammo(new WeaponInstance(reg.get("crowbar"))));
        // 숫자 6px, 띄어쓰기 4px, '/' 6px
        assertEquals(6 * 2 + 4 + 6 + 4 + 6 * 2, WeaponLabels.defaultFontWidth("24 / 24"));
        // 카드 글꼴 폭: 숫자가 띄어쓰기보다 넓고, 글자 수에 비례
        int w24 = WeaponLabels.cardFontWidth("24 / 24");
        org.junit.jupiter.api.Assertions.assertTrue(w24 > 15 && w24 < 60, "폭 " + w24);
    }
}
