package dev.violence.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class WoundsTest {
    @Test
    void hitPointsMapToTheRightPart() {
        assertEquals(FallPose.Part.HEAD, Wounds.locate(0, 28, 4).part());
        assertEquals(FallPose.Part.BODY, Wounds.locate(1, 18, 2).part());
        assertEquals(FallPose.Part.ARM_L, Wounds.locate(6, 21, 0).part(), "몸 기준 +x 가 왼쪽");
        assertEquals(FallPose.Part.FOREARM_R, Wounds.locate(-6, 14, 0).part());
        assertEquals(FallPose.Part.LEG_L, Wounds.locate(2, 9, 0).part());
        assertEquals(FallPose.Part.SHIN_R, Wounds.locate(-2, 2, 0).part());
    }

    @Test
    void spotStaysOnTheFaceAndKnowsFrontFromBack() {
        Wounds.Spot s = Wounds.locate(30, 100, -3);
        assertTrue(Math.abs(s.u()) <= 0.8 && Math.abs(s.v()) <= 0.8, "면 밖으로 나가지 않음");
        assertFalse(s.front(), "뒤에서 맞음");
        assertTrue(Wounds.locate(0, 18, 3).front());
    }

    @Test
    void heavierWeaponsLeaveBiggerWounds() {
        assertTrue(Wounds.size(Wounds.Kind.BULLET) < Wounds.size(Wounds.Kind.MELEE));
        assertTrue(Wounds.size(Wounds.Kind.MELEE) < Wounds.size(Wounds.Kind.HEAVY));
    }
}
