package dev.violence;

import static org.junit.jupiter.api.Assertions.*;

import dev.violence.logic.ComboTracker;
import dev.violence.logic.DoorPhysics;
import dev.violence.logic.FireAccumulator;
import dev.violence.logic.KillStreak;
import dev.violence.logic.Spread;
import dev.violence.math.Vec3;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class LogicTest {

    private int shotsOver(FireAccumulator acc, int ticks) {
        int total = 0;
        for (int t = 0; t < ticks; t++) total += acc.tickHeld(1000 + t);
        return total;
    }

    @Test
    void fireRates() {
        // 1분 = 1200틱 동안 꾹 누르면 RPM 만큼(±1) 발사
        assertEquals(1800, shotsOver(new FireAccumulator(1800), 1200), 2);
        assertEquals(860, shotsOver(new FireAccumulator(860), 1200), 2);
        assertEquals(1200, shotsOver(new FireAccumulator(1200), 1200), 2);
        assertEquals(130, shotsOver(new FireAccumulator(130), 1200), 2);
        // UZI 는 틱당 1발 이상
        FireAccumulator uzi = new FireAccumulator(1800);
        assertEquals(1.5, uzi.shotsPerTick(), 1e-9);
    }

    @Test
    void firstShotIsImmediate() {
        FireAccumulator m16 = new FireAccumulator(860);
        assertEquals(1, m16.tickHeld(50));
    }

    @Test
    void singleShotInterval() {
        FireAccumulator sg = new FireAccumulator(130); // 약 9.2틱 간격
        assertTrue(sg.trySingle(100));
        assertFalse(sg.trySingle(104));
        assertTrue(sg.trySingle(109));
    }

    @Test
    void shotgunSpreadInsideCone() {
        Random r = new Random(1);
        Vec3 dir = new Vec3(0, 0, 1);
        List<Vec3> pellets = Spread.pellets(dir, 500, 5.5, r);
        for (Vec3 p : pellets) {
            assertTrue(p.angleTo(dir) <= 5.5 + 1e-6);
        }
        // 실제로 퍼지는지 확인
        assertTrue(pellets.stream().anyMatch(p -> p.angleTo(dir) > 3));
    }

    @Test
    void combo() {
        ComboTracker c = new ComboTracker();
        assertEquals(1, c.registerKill(0, 100, 200));
        assertEquals(2, c.registerKill(150, 300, 200));
        assertNull(c.tick(340));
        ComboTracker.ComboEnd end = c.tick(351);
        assertNotNull(end);
        assertEquals(2, end.count());
        assertEquals(400, end.basePoints());
        assertEquals(0, c.count());
        assertEquals(400 + 40, ComboTracker.defaultBonus(2, 400));
        assertEquals(0, ComboTracker.defaultBonus(1, 400));
    }

    @Test
    void killStreakMilestones() {
        KillStreak k = new KillStreak();
        assertEquals(KillStreak.Milestone.NONE, k.add());
        assertEquals(1, k.bloodLevel());
        assertEquals(KillStreak.Milestone.NONE, k.add());
        assertEquals(KillStreak.Milestone.THREE, k.add());
        assertEquals(2, k.bloodLevel());
        assertEquals(KillStreak.Milestone.NONE, k.add());
        assertEquals(KillStreak.Milestone.FIVE, k.add());
        assertEquals(3, k.bloodLevel());
        assertEquals(KillStreak.Milestone.NONE, k.add());
        k.reset();
        assertEquals(0, k.bloodLevel());
    }

    @Test
    void doorSwingsAndStops() {
        DoorPhysics d = new DoorPhysics();
        assertTrue(d.isClosed());
        d.push(1, 30); // 발차기
        assertTrue(d.isDangerous());
        for (int i = 0; i < 60; i++) d.tick();
        assertFalse(d.isClosed());
        assertFalse(d.isMoving());
        assertTrue(d.angle() <= DoorPhysics.MAX_ANGLE);
        d.push(-1, 8);
        for (int i = 0; i < 60; i++) d.tick();
        assertTrue(d.angle() < DoorPhysics.MAX_ANGLE);
    }
}
