package dev.violence.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.violence.cutscene.Easing;
import org.junit.jupiter.api.Test;

class FlashAndEasingTest {
    @Test
    void easingsMatchTheirDefinitions() {
        assertEquals(0, Easing.outSine(0), 1e-9);
        assertEquals(1, Easing.outSine(1), 1e-9);
        assertEquals(Math.sin(Math.PI / 4), Easing.outSine(0.5), 1e-9);
        assertEquals(0, Easing.outCirc(0), 1e-9);
        assertEquals(1, Easing.outCirc(1), 1e-9);
        assertTrue(Easing.outCirc(0.3) > 0.7, "easeOutCirc 는 앞부분에 대부분 움직임");
        assertTrue(Easing.outSine(0.3) < Easing.outCirc(0.3), "카메라(sine)는 깜빡임(circ)보다 덜 급함");
    }

    @Test
    void killDuringFlashRewindsTheClock() {
        // 시계 값은 끈 뒤 틱당 0.0125 씩 내려가고, 다시 켜면 틱당 0.05 씩 올라감 → 지난 틱의 1/4 만에 처음으로 돌아감
        assertEquals(0, Hud.rewindTicks(0));
        assertEquals(1, Hud.rewindTicks(3));
        assertEquals(3, Hud.rewindTicks(12));
        assertEquals(7, Hud.rewindTicks(Hud.FLASH_TICKS));
        for (int e = 1; e <= Hud.FLASH_TICKS; e++) {
            int r = Hud.rewindTicks(e);
            assertTrue(r * Hud.DARKEN_UP >= e * Hud.DARKEN_DOWN - 1e-9, "되감기가 모자람 " + e);
        }
    }
}
