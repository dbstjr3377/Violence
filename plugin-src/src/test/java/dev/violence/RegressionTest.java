package dev.violence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.arena.GroundWeaponService;
import dev.violence.combat.Combatant;
import dev.violence.combat.ExecutionChoice;
import dev.violence.combat.GunRules;
import dev.violence.fx.BloodService;
import dev.violence.fx.ExecutionAnims;
import dev.violence.fx.FallPose;
import dev.violence.mask.Mask;
import dev.violence.math.Vec3;
import dev.violence.weapon.ExecutionStyle;
import dev.violence.weapon.WeaponInstance;
import dev.violence.weapon.WeaponRegistry;
import dev.violence.weapon.WeaponType;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.joml.Vector3d;
import org.junit.jupiter.api.Test;

/**
 * 예전에 제기된 문제가 다시 생기지 않았는지 (게임 규칙 쪽). 리소스팩·데이터 쪽은 tools/check_regressions.py.
 * 처형 무기·손·관절은 ExecutionAnimsTest, 넘어짐 자세는 FallPoseTest, 정보 카드 글자는 WeaponLabelsTest 에도 있음.
 */
class RegressionTest {
    private final WeaponRegistry reg = WeaponRegistry.load(new InputStreamReader(
            getClass().getClassLoader().getResourceAsStream("weapons.yml"), StandardCharsets.UTF_8));
    private final ExecutionAnims anims = ExecutionAnims.load();

    private static List<Mask> masksAndNone() {
        List<Mask> m = new ArrayList<>(List.of(Mask.values()));
        m.add(null);
        return m;
    }

    /** "정면에서 맞았는데 뒤로 넘어져야지": 어떤 공격이든 뒤로 넘어지고, 다 넘어지면 머리가 발 뒤쪽 */
    @Test
    void alwaysFallsBackward() {
        for (boolean strong : new boolean[] {false, true}) {
            assertTrue(Map.of(FallPose.Kind.BACK, 1, FallPose.Kind.BLAST, 1).containsKey(FallPose.kindFor(strong, false)));
            assertEquals(FallPose.Kind.WALL, FallPose.kindFor(strong, true));
        }
        Map<FallPose.Kind, FallPose> all = FallPose.loadAll();
        for (FallPose.Kind k : new FallPose.Kind[] {FallPose.Kind.BACK, FallPose.Kind.BLAST}) {
            FallPose p = all.get(k);
            int last = p.frameCount() - 1;
            Vector3d head = p.place(last, FallPose.Part.HEAD, 1).center();
            assertTrue(head.z < -1.0 && head.y < 0.5, k + " 머리가 뒤쪽 바닥에 " + head);
        }
    }

    /** "벽에 기대고 기절한 캐릭터는 어떤 상황에서든 발차기로 처형" */
    @Test
    void wallStunnedIsAlwaysKicked() {
        for (WeaponType t : reg.all()) {
            for (Mask m : masksAndNone()) {
                for (boolean ammo : new boolean[] {false, true}) {
                    ExecutionChoice c = ExecutionChoice.choose(true, t, reg.fist(), m, ammo, anims);
                    assertEquals(ExecutionStyle.WALL_KICK, c.style(), t.id() + " " + m);
                    assertFalse(c.drop(), "발차기는 무기를 버리지 않음");
                }
            }
        }
    }

    /** 처형 연출 묶음: 맨손 / 밟기 가면 / 둔기 / 무거운 무기 / 가벼운 무기 / 날붙이, 총·투척은 버리고 맨손 */
    @Test
    void executionFollowsWeaponGroup() {
        for (WeaponType t : reg.all()) {
            for (Mask m : masksAndNone()) {
                ExecutionChoice c = ExecutionChoice.choose(false, t, reg.fist(), m, true, anims);
                String fistAnim = m == Mask.JAKE || m == Mask.PIG_BUTCHER || m == Mask.MARK ? "stomp" : "fist";
                if (t.isGun() && m == Mask.DETECTIVE) {
                    assertEquals(ExecutionStyle.GUN_SHOT, c.style(), "형사 가면은 총으로 처형");
                } else if (t.isGun() || t.isThrowable()) {
                    assertTrue(c.drop() && c.weapon().isFist(), t.id() + " 버리고 맨손");
                    assertEquals(fistAnim, c.anim(), t.id() + " " + m);
                } else if (t.isFist()) {
                    assertEquals(fistAnim, c.anim(), "맨손 " + m);
                    assertEquals(ExecutionStyle.HITS.equals(c.style()) || "stomp".equals(c.anim()), true);
                } else {
                    assertEquals(anims.groupOf(t.id()), c.anim(), t.id());
                    assertFalse(c.drop());
                }
            }
        }
        // 맨손은 왼클릭 5번, 둔기·가벼운 무기는 3번, 무거운 무기·날붙이·밟기는 자동
        assertEquals(5, reg.fist().executionHits());
        assertEquals(ExecutionStyle.AUTO, ExecutionChoice.choose(false, reg.get("sledgehammer"), reg.fist(), null, true, anims).style());
        assertEquals(ExecutionStyle.AUTO, ExecutionChoice.choose(false, reg.get("dagger"), reg.fist(), null, true, anims).style());
        assertEquals(ExecutionStyle.AUTO, ExecutionChoice.choose(false, reg.fist(), reg.fist(), Mask.MARK, true, anims).style());
        assertEquals(ExecutionStyle.HITS, ExecutionChoice.choose(false, reg.get("crowbar"), reg.fist(), null, true, anims).style());
    }

    private static double configValue(String key) throws IOException {
        try (InputStream in = RegressionTest.class.getClassLoader().getResourceAsStream("config.yml")) {
            String s = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            Matcher m = Pattern.compile("(?m)^\\s*" + Pattern.quote(key) + ":\\s*([0-9.]+)").matcher(s);
            assertTrue(m.find(), key);
            return Double.parseDouble(m.group(1));
        }
    }

    /** "총에 맞은 적은 쓰러져 기절하는 것 없이 일정 hp 이하로 떨어지면 바로 즉사": 몸통 첫 발은 버팀, 두 번째 발에 즉사 */
    @Test
    void gunBodyHitsKillBelowThresholdWithoutKnockdown() throws IOException {
        double dmg = configValue("gun-body-damage");
        double death = configValue("gun-death-hp");
        GunRules.BodyHit first = GunRules.bodyHit(Combatant.MAX_HP, dmg, death);
        assertFalse(first.dies(), "첫 발");
        GunRules.BodyHit second = GunRules.bodyHit(first.hpAfter(), dmg, death);
        assertTrue(second.dies(), "두 번째 발에 즉사 (HP " + second.hpAfter() + ")");
    }

    /** "얇고 길게 퍼진 피 스프라이트를 넓게": 비스듬히 닿아도 길이 ÷ 폭이 작음 */
    @Test
    void glancingBloodStaysWide() {
        for (double g = 0; g <= 1.0001; g += 0.05) {
            float[] wh = BloodService.streakSize(1f, g);
            assertTrue(wh[0] / wh[1] <= 1.75f, "길이/폭 " + wh[0] / wh[1]);
        }
    }

    /** 바닥 무기: 빈 총은 빨간 테두리, 정보 카드는 무기 오른쪽(보는 사람 기준) */
    @Test
    void emptyGunAndCardSide() {
        WeaponInstance m16 = new WeaponInstance(reg.get("m16"));
        assertFalse(GroundWeaponService.emptyGun(m16));
        m16.setAmmo(0);
        assertTrue(GroundWeaponService.emptyGun(m16));
        assertFalse(GroundWeaponService.emptyGun(new WeaponInstance(reg.get("crowbar"))), "근접 무기는 흰 테두리");
        Vec3 item = new Vec3(0, 64, 0);
        // 북쪽(-z)을 보면 오른쪽은 동쪽(+x)
        assertTrue(GroundWeaponService.cardPos(item, new Vec3(0, -0.5, -1)).x() > 0.3);
        // 동쪽(+x)을 보면 오른쪽은 남쪽(+z)
        assertTrue(GroundWeaponService.cardPos(item, new Vec3(1, -0.5, 0)).z() > 0.3);
    }

    /** 처형 인형: 팔꿈치·무릎 두 마디 (팔다리 관절이 하나라 무기를 돌리던 문제) */
    @Test
    void puppetLimbsHaveElbowsAndKnees() {
        assertEquals(10, FallPose.Part.values().length);
        assertEquals(FallPose.Part.ARM_R, FallPose.Part.FOREARM_R.parent);
        assertEquals(FallPose.Part.LEG_L, FallPose.Part.SHIN_L.parent);
        assertNull(FallPose.Part.HEAD.parent);
    }
}
