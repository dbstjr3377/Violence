package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.math.Vec3;
import org.bukkit.FluidCollisionMode;
import org.bukkit.entity.Display;
import org.bukkit.entity.ItemDisplay;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.bukkit.util.Vector;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 클럽 맵의 공중 빛줄기 (무빙 라이트 원뿔, 레이저 부채꼴, 미러볼).
 * 블록 표면의 빛은 리소스팩 쉐이더가 그리고, 여기서는 같은 공식(ClubLights)으로 같은 방향의 빛줄기를 보여 준다.
 * 2틱마다 보간 이동하므로 쉐이더와 거의 같은 시각에 움직인다.
 */
public final class ClubBeams {
    private static final int PERIOD = 2;
    private static final Display.Brightness FULL = new Display.Brightness(15, 15);
    private final ViolencePlugin plugin;

    public ClubBeams(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public void start(Arena a) {
        if (a.map == null || !"club".equals(a.map.id)) return;
        ItemDisplay[] spots = new ItemDisplay[ClubLights.SPOTS];
        int[] shownColor = new int[ClubLights.SPOTS];
        for (int i = 0; i < spots.length; i++) {
            spots[i] = spawn(a, ClubLights.spotPos(i), "violence:fx/beam_magenta");
            shownColor[i] = -1;
        }
        ItemDisplay[][] lasers = new ItemDisplay[ClubLights.LASERS][ClubLights.LASER_BEAMS];
        for (int j = 0; j < ClubLights.LASERS; j++) {
            for (int k = 0; k < ClubLights.LASER_BEAMS; k++) {
                lasers[j][k] = spawn(a, ClubLights.LASER, "violence:fx/laser_" + ClubLights.laserColor(j));
            }
        }
        ItemDisplay ball = spawn(a, ClubLights.BALL, "violence:fx/disco_ball");
        update(a, spots, shownColor, lasers, ball, true);
        plugin.repeat(PERIOD, task -> {
            if (plugin.arena() != a || !ball.isValid()) {
                task.cancel();
                return;
            }
            update(a, spots, shownColor, lasers, ball, false);
        });
    }

    private ItemDisplay spawn(Arena a, Vec3 at, String model) {
        return a.track(a.world.spawn(Fx.loc(a.world, at), ItemDisplay.class, d -> {
            d.setItemStack(Fx.model(model));
            d.setItemDisplayTransform(ItemDisplay.ItemDisplayTransform.NONE);
            d.setPersistent(false);
            d.setBrightness(FULL);
            d.setViewRange(2.0f);
            d.setShadowRadius(0);
            d.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(), new Quaternionf()));
        }));
    }

    private void update(Arena a, ItemDisplay[] spots, int[] shownColor, ItemDisplay[][] lasers, ItemDisplay ball, boolean first) {
        double s = ClubLights.seconds(a.world.getGameTime());
        for (int i = 0; i < spots.length; i++) {
            Vec3 from = ClubLights.spotPos(i);
            Vec3 dir = ClubLights.spotDir(i, s);
            double len = reach(a, from, dir, 26);
            float w = (float) (2 * len * Math.tan(ClubLights.SPOT_HALF_ANGLE));
            int c = ClubLights.spotColor(i, s);
            if (c != shownColor[i]) {
                spots[i].setItemStack(Fx.model("violence:fx/beam_" + ClubLights.COLORS[c]));
                shownColor[i] = c;
            }
            move(spots[i], beam(dir, len, w, w), first);
        }
        boolean on = ClubLights.lasersOn(s);
        for (int j = 0; j < lasers.length; j++) {
            for (int k = 0; k < lasers[j].length; k++) {
                Vec3 dir = ClubLights.laserBeam(j, k, s);
                double len = on ? reach(a, ClubLights.LASER, dir, 40) : 0;
                move(lasers[j][k], beam(dir, len, on ? 0.05f : 0f, on ? 0.05f : 0f), first);
            }
        }
        Quaternionf spin = new Quaternionf().rotateY((float) -ClubLights.ballAngle(s));
        move(ball, new Transformation(new Vector3f(), spin, new Vector3f(1.3f, 1.3f, 1.3f), new Quaternionf()), first);
    }

    /** 모델은 위(+y)가 광원, 아래(-y)로 뻗는 빛줄기: -y 를 dir 에 맞추고 길이만큼 늘린다 */
    private static Transformation beam(Vec3 dir, double len, float wx, float wz) {
        Quaternionf q = new Quaternionf().rotationTo(new Vector3f(0, -1, 0),
                new Vector3f((float) dir.x(), (float) dir.y(), (float) dir.z()).normalize());
        Vector3f mid = new Vector3f((float) (dir.x() * len / 2), (float) (dir.y() * len / 2), (float) (dir.z() * len / 2));
        return new Transformation(mid, q, new Vector3f(wx, (float) len, wz), new Quaternionf());
    }

    private static void move(ItemDisplay d, Transformation t, boolean first) {
        if (!d.isValid()) return;
        if (!first) {
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(PERIOD);
        }
        d.setTransformation(t);
    }

    /** 빛줄기가 벽/바닥에 닿는 거리 */
    private static double reach(Arena a, Vec3 from, Vec3 dir, double max) {
        RayTraceResult r = a.world.rayTraceBlocks(Fx.loc(a.world, from), new Vector(dir.x(), dir.y(), dir.z()), max,
                FluidCollisionMode.NEVER, true);
        if (r == null) return max;
        Vector hp = r.getHitPosition();
        return Math.max(0.2, from.distance(new Vec3(hp.getX(), hp.getY(), hp.getZ())));
    }
}
